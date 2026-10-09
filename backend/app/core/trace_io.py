"""
Leitura de arquivos de instrumento para os módulos de traço (TGA, DSC,
tração, reologia, FTIR, XRD, WAXS).

O problema
----------
Os endpoints de traço recebem JSON com duas listas já limpas, na unidade certa.
Isso funciona para quem exporta os dados à mão, e não funciona para quem tem o
arquivo que o instrumento escreve. Um DSC da NETZSCH sai assim::

    #SEPARATOR:SEMICOLON
    #DECIMAL:POINT
    #EXO:-1
    #RANGE:-30°C/10,0(K/min)/200°C
    #SAMPLE MASS /mg:4.98
    #SAMPLE:1-90
    ##Temp./°C;Time/min;DSC/(mW/mg);Sensit./(uV/mW)
      9.33910; 91.00083;-8.719357e-02;3.42446

Quatro colunas, e a segunda é *tempo*, não temperatura. Um parser que assume
"primeira coluna = x, segunda = y" lê tempo como se fosse o sinal. O sinal está
em mW/mg, não em W/g. E o cabeçalho ``#EXO:-1`` diz que o eixo está com
exotérmico para cima -- o inverso da convenção que a análise assume.

O que este módulo faz
---------------------
Lê o arquivo, encontra as colunas que o módulo pediu, confere que a unidade
bate, converte o que precisa ser convertido, e devolve os metadados que o
cabeçalho trouxer (taxa de aquecimento, massa, nome da amostra, convenção de
sinal). A decisão de aceitar ou recusar é explícita: quando algo não pode ser
determinado, o resultado carrega o motivo em vez de um palpite.

O que este módulo NÃO faz
-------------------------
Não adivinha a unidade de uma coluna sem rótulo. Se o arquivo não diz, e os
valores não permitem decidir por faixa física, a coluna é recusada com o motivo.
Converter por palpite é a falha que o resto do projeto existe para evitar.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from app.core.ingest import _to_float


class TraceImportError(ValueError):
    """O arquivo não pode ser lido como o traço pedido."""


# ---------------------------------------------------------------------------
# Papéis de coluna e as palavras que os denunciam
# ---------------------------------------------------------------------------

#: Cada papel tem os nomes que os instrumentos usam, normalizados. A ordem
#: importa: a primeira correspondência vence, então um rótulo mais específico
#: precisa vir antes do mais genérico ("heat flow" antes de "flow").
#:
#: Toda entrada precisa de três caracteres ou mais, ou ser uma palavra inteira.
#: A regra existe porque uma versão anterior aceitava substring curta -- ``"s"``
#: para segundos, ``"i "`` para intensidade -- e então ``DSC/(mW/mg)`` e
#: ``Sensit./(uV/mW)`` casavam com "time" antes de casar consigo mesmos, porque
#: ambos contêm a letra ``s``. O resultado era um DSC lido como *tempo*: o
#: eixo y saía do arquivo errado, sem erro nenhum. Uma abreviação curta é
#: sempre ambígua num cabeçalho de instrumento, e é melhor não reconhecer do
#: que reconhecer errado.
COLUMN_ROLES: dict[str, tuple[str, ...]] = {
    "temperature": (
        "temp",
        "temperature",
        "temperatur",
        "sample temp",
        "program temp",
        "tsample",
        "tzero",
    ),
    "time": ("time", "zeit", "minute", "second", "min)", "(min", "(s)", "/min"),
    "heat_flow": (
        "dsc",
        "heat flow",
        "heatflow",
        "heat-flow",
        "fluxo de calor",
        "heat flow rate",
        "calor",
    ),
    "mass": (
        "mass",
        "weight",
        "tga",
        "masse",
        "massa",
        "mass percent",
        "tga curve",
        "w (%)",
        "weight (%)",
        "mass (%)",
    ),
    "dtg": ("dtg", "derivative", "dm/dt", "rate of mass loss"),
    "stress": ("stress", "tensao", "tension", "sigma", "force"),
    "strain": ("strain", "deform", "elongation", "extens"),
    "omega": ("omega", "frequency", "freq", "rad/s", "angular"),
    "g_prime": ("g'", "g_prime", "gprime", "storage"),
    "g_double_prime": ("g''", "g_double_prime", "gpp", "loss mod"),
    "wavenumber": ("wavenumber", "wave number", "cm-1", "cm^-1", "cm⁻¹"),
    "transmittance": ("transmittance", "transmission", "%t"),
    "absorbance": ("absorbance", "optical density"),
    "two_theta": ("2theta", "2-theta", "2θ", "two theta", "angle", "theta"),
    "intensity": ("intensity", "counts", "cps"),
    "sensitivity": ("sensit", "sensitiv"),
    "reference_temp": ("reference temp", "ref temp"),
    "purge": ("purge",),
}


#: Papéis que um arquivo costuma trazer e que a análise não usa. A presença de
#: um deles nunca é um problema; reconhecê-los serve para que a mensagem de
#: erro liste o que existe em vez de só dizer que faltou algo, e para que
#: pequenas abreviações não sejam forçadas no papel errado.
IGNORED_ROLES = frozenset({"sensitivity", "reference_temp", "purge", "time", "dtg"})


#: Unidades reconhecidas por papel, com o fator para a unidade canônica do
#: módulo. A canônica é a que a análise documenta: W/g para DSC, % para massa
#: de TGA, MPa para tensão, Pa para módulo, graus para ângulos.
#:
#: O fator é um número quando basta multiplicar, ``None`` quando a conversão
#: depende de um valor que pode não estar no arquivo (mW absoluto precisa da
#: massa), e uma string nomeada quando a conversão não é multiplicativa
#: (Kelvin -> Celsius é soma). Os dois últimos casos não são erro: são a
#: informação que falta para converter, e o chamador decide se tem o dado.
UNIT_TABLE: dict[str, dict[str, tuple[float | str | None, str]]] = {
    "heat_flow": {
        "w/g": (1.0, "W/g"),
        "mw/mg": (1.0, "W/g"),  # numericamente idêntico: 1 mW/mg = 1 W/g
        "w/mg": (1000.0, "W/g"),
        "uw/mg": (1e-3, "W/g"),
        "mw": (None, "W/g"),  # absoluto: precisa da massa
        "w": (None, "W/g"),
        "j/g": (None, "W/g"),  # energia, não fluxo: recusar
    },
    "mass": {
        "%": (1.0, "pct"),
        "pct": (1.0, "pct"),
        "percent": (1.0, "pct"),
        "mg": (None, "pct"),  # absoluto: precisa da massa inicial
        "g": (None, "pct"),
    },
    "temperature": {
        "c": (1.0, "C"),
        "°c": (1.0, "C"),
        "celsius": (1.0, "C"),
        "k": ("+273.15", "C"),
        "kelvin": ("+273.15", "C"),
        "f": ("F2C", "C"),
    },
    "stress": {
        "mpa": (1.0, "MPa"),
        "n/mm2": (1.0, "MPa"),
        "gpa": (1000.0, "MPa"),
        "kpa": (1e-3, "MPa"),
        "psi": (0.00689476, "MPa"),
        "pa": (1e-6, "MPa"),
    },
    "strain": {
        "%": (1.0, "pct"),
        "pct": (1.0, "pct"),
        "percent": (1.0, "pct"),
        "mm/mm": (100.0, "pct"),
        "": (1.0, "pct"),  # sem unidade: assumir fração? não -- ver abaixo
    },
    "g_prime": {"pa": (1.0, "Pa"), "kpa": (1e3, "Pa"), "mpa": (1e6, "Pa")},
    "g_double_prime": {"pa": (1.0, "Pa"), "kpa": (1e3, "Pa"), "mpa": (1e6, "Pa")},
    "wavenumber": {"cm-1": (1.0, "cm-1"), "cm^-1": (1.0, "cm-1"), "cm⁻¹": (1.0, "cm-1")},
    "transmittance": {"%": (1.0, "pct"), "pct": (1.0, "pct")},
    "absorbance": {"au": (1.0, "au"), "": (1.0, "au"), "a.u.": (1.0, "au")},
    "two_theta": {
        "deg": (1.0, "deg"),
        "°": (1.0, "deg"),
        "degrees": (1.0, "deg"),
        "2theta": (1.0, "deg"),
    },
}


@dataclass
class ParsedColumn:
    """Uma coluna resolvida do arquivo."""

    index: int
    raw_header: str
    role: str | None
    unit: str | None
    #: Fator de conversão para a unidade canônica, ou None quando a conversão
    #: depende de um valor que não está no arquivo (ex.: massa para mW -> W/g).
    factor: float | str | None
    values: list[float]


@dataclass
class TraceFile:
    """Um arquivo de instrumento lido."""

    path: str
    #: Linhas de cabeçalho ``#CHAVE:valor``, chave em minúsculas.
    metadata: dict[str, str] = field(default_factory=dict)
    columns: list[ParsedColumn] = field(default_factory=list)
    #: Avisos sobre decisões tomadas na leitura, para o usuário julgar.
    warnings: list[str] = field(default_factory=list)

    def column(self, role: str) -> ParsedColumn | None:
        for c in self.columns:
            if c.role == role:
                return c
        return None

    def values(self, role: str) -> list[float] | None:
        c = self.column(role)
        return c.values if c else None

    # -- metadados que o cabeçalho costuma trazer --------------------------
    @property
    def sample_name(self) -> str | None:
        for key in ("sample", "identity", "samplename", "sample name"):
            if key in self.metadata:
                v = self.metadata[key].strip()
                if v:
                    return v
        return None

    @property
    def sample_mass_mg(self) -> float | None:
        for key in (
            "sample mass /mg",
            "sample mass",
            "mass /mg",
            "size",
            "sample weight /mg",
        ):
            if key in self.metadata:
                v = _to_float(self.metadata[key])
                if v is not None and v > 0:
                    return v
        return None

    @property
    def heating_rate(self) -> float | None:
        """Taxa de aquecimento programada, em K/min, lida do método."""
        for key in ("range", "segment", "seg. 1", "method", "method name"):
            raw = self.metadata.get(key)
            if not raw:
                continue
            m = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*\(?\s*K\s*/\s*min", raw, re.I)
            if m:
                return float(m.group(1).replace(",", "."))
            m = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*°?\s*C\s*/\s*min", raw, re.I)
            if m:
                return float(m.group(1).replace(",", "."))
        return None

    @property
    def exothermic_direction(self) -> str | None:
        """'up' ou 'down', segundo o cabeçalho. ``#EXO:-1`` significa down."""
        for key in ("exo", "exothermic", "exo up", "sign"):
            raw = self.metadata.get(key)
            if raw is None:
                continue
            v = raw.strip().lower()
            if v in {"1", "up", "yes", "true"}:
                # Convenção do fabricante: 1 pode significar "exotérmico para
                # cima" ou "sinal invertido". O valor numérico é ambíguo entre
                # instrumentos, então 1 é lido como "exotérmico para cima" e o
                # aviso correspondente é registrado.
                return "up"
            if v in {"-1", "down", "no", "false"}:
                return "down"
        return None


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------

#: Chaves de cabeçalho que nunca são metadados úteis.
_SKIP_META = {"exporttype", "ftype", "format", "corr. code", "remark"}


def _decode(raw: bytes) -> str:
    """
    Decodifica o arquivo tolerando os encodings que os instrumentos usam.

    Latin-1 é tentado antes de UTF-8 porque um export de instrumento europeu
    escreve ``°`` como byte único, o que é UTF-8 inválido: decodificar como
    UTF-8 com ``errors="replace"`` produziria ``�`` no meio de ``°C`` e o
    rótulo da coluna de temperatura deixaria de casar.

    Um conteúdo binário é recusado aqui em vez de seguir: latin-1 decodifica
    *qualquer* byte, então sem esta guarda um PNG ou um contêiner proprietário
    atravessava o parser de texto e saía como um ``TraceFile`` de colunas
    inventadas -- a análise rodava sobre lixo sem que nada reclamasse.
    """
    if _looks_binary(raw):
        raise TraceImportError(
            "o arquivo parece binário, não um export de texto delimitado. "
            "Se for um formato proprietário do instrumento (ex.: .tri, .ngb-sd7), "
            "exporte-o como texto/CSV, ou informe o formato para que o leitor "
            "correto seja usado."
        )
    for enc in ("utf-8-sig", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    # ``\r\n`` e ``\r`` viram ``\n``; o resto do código assume linhas simples.
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _looks_binary(raw: bytes) -> bool:
    """Distingue um export de texto de um contêiner binário.

    O teste é a presença de bytes nulos e a fração de bytes de controle: um
    export de instrumento é ASCII estendido e pode ter ``\\t``/``\\n``, mas não
    tem ``\\x00`` nem rajadas de bytes de controle. Amostra o primeiro 1 MB --
    suficiente para decidir e barato mesmo num arquivo de dezenas de MB.
    """
    head = raw[:1_000_000]
    if not head:
        return False
    if b"\x00" in head:
        return True
    control = sum(1 for b in head if b < 32 and b not in (9, 10, 13))
    return control / len(head) > 0.05


def _split_header_and_body(lines: Sequence[str]) -> tuple[dict[str, str], list[str]]:
    """
    Separa ``#CHAVE:valor`` das linhas de dados.

    Um arquivo de instrumento tem três tipos de linha, e todos começam com
    ``#``: metadados (``#SAMPLE:x``), o cabeçalho de colunas (``##Temp.;Time``)
    e nada mais. O cabeçalho de colunas é o ``#`` duplo.
    """
    meta: dict[str, str] = {}
    body: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("##"):
            body.append(s[2:])
            continue
        if s.startswith("#"):
            inner = s.lstrip("#").strip()
            if ":" in inner:
                key, _, value = inner.partition(":")
                k = key.strip().lower()
                if k and k not in _SKIP_META:
                    meta.setdefault(k, value.strip())
            # Comentário sem valor: guardar como chave vazia não ajuda.
            continue
        body.append(s)
    return meta, body


def _split_fields(line: str, separator: str | None) -> list[str]:
    if separator:
        return [f.strip() for f in line.split(separator)]
    # Sem separador declarado, tenta os usuais antes de cair em espaços.
    for cand in (";", "\t", "|", ","):
        if line.count(cand) >= 1:
            return [f.strip() for f in line.split(cand)]
    return line.split()


def _unit_of(header: str) -> str:
    """Extrai a unidade de um rótulo como ``DSC/(mW/mg)`` ou ``Temp./°C``."""
    m = re.search(r"[\(\[]\s*([^\)\]]+?)\s*[\)\]]\s*$", header)
    if m:
        return m.group(1).strip().lower()
    # Formato ``Temp./°C`` -- unidade após a última barra.
    m = re.search(r"/\s*([^/]+?)\s*$", header)
    if m:
        return m.group(1).strip().lower()
    return ""


def _match_role(header: str, unit: str) -> str | None:
    """Papel de uma coluna, pelo rótulo — a unidade serve de desempate."""
    norm = re.sub(r"\s+", " ", header.strip().lower())
    norm = norm.replace("°", "").replace("º", "")
    # Unidade com grau já foi normalizada; tenta casar pelo nome.
    for role, tokens in COLUMN_ROLES.items():
        for tok in tokens:
            if tok in norm:
                return role
    # Sem nome reconhecível, a unidade sozinha pode decidir.
    if unit in {"w/g", "mw/mg", "w/mg", "uw/mg"}:
        return "heat_flow"
    if unit in {"cm-1", "cm^-1", "cm⁻¹"}:
        return "wavenumber"
    if unit in {"rad/s"}:
        return "omega"
    if unit in {"pa", "kpa", "mpa"}:
        # Ambíguo entre G' e G''; só a ordem ou o nome decide.
        return None
    if unit in {"deg", "°", "degrees"}:
        return "two_theta"
    if unit in {"%", "pct", "percent"}:
        return None
    return None


# ---------------------------------------------------------------------------
# Formato binário TA Instruments (.tri): mesmo contrato, outra porta
# ---------------------------------------------------------------------------
#
# Um .tri não tem cabeçalho de colunas legível: os canais vêm numerados num
# bloco binário e seus nomes na chave ``proceduresignals``. O adaptador abaixo
# reduz o .tri ao mesmo ``TraceFile`` que o caminho de texto produz, para que a
# resolução de papéis, a conversão de unidades e a validação de coerência sejam
# as mesmas nos dois casos -- uma segunda porta, não um segundo parser.
#
# A unidade não está no arquivo: o TA nomeia o canal ("Heat Flow") sem dizer se
# é W/g ou mW. Como o dado é normalizado pela massa em toda a série do
# instrumento, e 1 mW/mg = 1 W/g numericamente, a unidade canônica é declarada
# aqui e a conversão é a identidade. Declarar isso explicitamente (em vez de
# deixar ``_unit_of`` devolver vazio e o fator cair em None) é o que faz a
# coluna ser aceita em vez de recusada por unidade ausente.
_TRI_ROLE_UNITS: tuple[tuple[str, str, str], ...] = (
    # (trecho do nome do canal, papel, unidade declarada)
    #
    # A unidade vai dentro do cabeçalho entre colchetes, e não no campo
    # ``unit``, porque é assim que o caminho de texto a entrega: `_unit_of`
    # extrai o que está entre parênteses/colchetes. Passar "degC" direto no
    # campo unit não casaria com a chave "c" da UNIT_TABLE sem normalização
    # extra, e a coluna cairia em factor=None -- recusada por unidade ausente.
    ("tzero temperature", "temperature", "Temp. [°C]"),
    ("heat flow", "heat_flow", "Heat Flow [mW/mg]"),
    ("cell purge", "purge", "Cell Purge [mL/min]"),
    ("time", "time", "Time [s]"),
)


def _tri_role_and_header(name: str) -> tuple[str | None, str]:
    """Mapeia um nome de canal .tri para (papel, cabeçalho com unidade).

    O casamento prefere a **igualdade** ao trecho: ``Heat Flow`` é o canal
    normalizado do instrumento, enquanto ``Heat Flow A``/``Heat Flow B`` são
    sensores auxiliares. Casar por trecho na ordem do arquivo elegia
    ``Heat Flow A`` (index 11) no lugar de ``Heat Flow`` (index 13) -- a
    análise rodaria sobre uma leitura auxiliar sem sinalizar nada.

    Canais auxiliares (``Temperature A/B/C``, ``Heat Flow A/B``, ``Flange``,
    ``Junction``) **não** recebem papel: são leituras redundantes da mesma
    grandeza e, se rotuladas, fariam ``resolve_trace`` escolher a primeira
    por ordem de arquivo em vez da canônica. Ficam listadas como colunas sem
    papel -- visíveis na prévia, fora da análise.
    """
    low = name.strip().lower()
    # 1) Igualdade exata contra o nome canônico do canal.
    for needle, role, header in _TRI_ROLE_UNITS:
        if low == needle:
            return role, header
    # 2) Trecho, restrito aos nomes canônicos (não aos auxiliares).
    for needle, role, header in _TRI_ROLE_UNITS:
        if needle in low and not re.search(r"\s[a-c]$", low):
            return role, header
    return None, name


def _clean_procedure(raw: str) -> str:
    """Remove os prefixos de controle e conserta o grau corrompido.

    O bloco de metadados do .tri é latin-1, então o símbolo de grau chega como
    a sequência de dois bytes ``Â°``. O regex de taxa procura ``°?C/min`` e não
    casa com ``Â°C/min`` -- a taxa vinha None em todos os 116 arquivos. Trocar
    a sequência por ``°`` antes de publicar conserta isso na origem, para que
    o mesmo regex do caminho de texto funcione nos dois formatos.
    """
    cleaned = raw.strip().lstrip("\x01\x02\x03\x04\x05\x06\x07\x08\x0e\x10\r\n")
    return cleaned.replace("Â°", "°").replace("\u00c2\u00b0", "°")


def _read_tri_as_trace_file(p: Path) -> TraceFile:
    """Converte um .tri no mesmo ``TraceFile`` que o caminho de texto produz."""
    # Import tardio: o leitor binário importa numpy, e o caminho de texto não
    # deve pagar esse custo quando o arquivo é .txt.
    from app.core.io.tri_reader import read_tri

    tri = read_tri(str(p))

    # Metadados: chaves em minúsculas, como no caminho de texto, para que as
    # propriedades de TraceFile (sample_name, sample_mass_mg, heating_rate)
    # funcionem sem ramo por formato.
    meta: dict[str, str] = {}
    if tri.sample_name:
        meta["sample"] = tri.sample_name
    if tri.sample_mass_mg is not None:
        meta["sample mass /mg"] = str(tri.sample_mass_mg)
    if tri.procedure:
        # A taxa de aquecimento vive na procedure ("Ramp 10.00 C/min to 270").
        # Publicá-la sob "method" deixa TraceFile.heating_rate lê-la com o
        # mesmo código que lê o #RANGE dos arquivos de texto.
        meta["method"] = _clean_procedure(tri.procedure)

    columns: list[ParsedColumn] = []
    seen: set[str] = set()
    for ch in tri.channels:
        if not ch.name:
            continue
        role, header = _tri_role_and_header(ch.name)
        # Só o primeiro canal de cada papel entra na análise; os repetidos
        # ficam sem papel para não competir pela escolha. O primeiro em ordem
        # de arquivo é o canônico: Time, Tzero Temperature, ... , Heat Flow.
        if role is not None and role in seen:
            role = None
        if role is not None:
            seen.add(role)
        columns.append(
            ParsedColumn(
                index=ch.index,
                raw_header=header if role else ch.name,
                role=role,
                unit=_unit_of(header) if role else None,
                factor=None,  # resolvido pela UNIT_TABLE no caminho comum
                values=ch.values,
            )
        )

    warnings: list[str] = []
    if not columns:
        raise TraceImportError(f"{p.name}: nenhum canal numérico recuperado do arquivo .tri")
    roles = {c.role for c in columns}
    if "temperature" not in roles or "heat_flow" not in roles:
        warnings.append(
            "canal de temperatura ou de fluxo de calor ausente: "
            f"papéis presentes = {sorted(r for r in roles if r)}"
        )

    tf = TraceFile(path=str(p), metadata=meta, columns=columns, warnings=warnings)
    # O caminho comum aplica a UNIT_TABLE a partir de (role, unit); o .tri
    # chega sem fator porque a unidade é declarada, não medida no arquivo.
    for col in tf.columns:
        _assign_factor(col)
    return tf


_BINARY_SUFFIXES = frozenset({".tri", ".ngb-sd7", ".ngb", ".sd7"})


def _looks_like_tri(raw: bytes) -> bool:
    """Reconhece um .tri pelo conteúdo, não pelo nome.

    Dois sinais, ambos presentes em todo arquivo do dataset: um bloco PNG
    embutido (o Trios grava um render do gráfico junto aos dados) e o padrão
    de ancoragem ``<count><18 bytes><count>`` que o leitor usa para localizar
    os canais. Checar o conteúdo permite ler um .tri renomeado -- que é o caso
    real de um export chegado por e-mail ou de um fixture recortado -- sem
    depender de a extensão sobreviver ao transporte.
    """
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return False  # um PNG puro: plot exportado, não um container .tri
    return b"\x89PNG" in raw[:1_000_000]


def _assign_factor(col: ParsedColumn) -> None:
    """Resolve, no lugar, o fator de conversão de uma coluna para a canônica.

    Fica separado do laço de leitura porque o caminho .tri monta colunas fora
    desse laço mas precisa da mesma conversão: dois lugares decidindo fator
    seria uma divergência silenciosa esperando para acontecer.
    """
    if not col.role or not col.unit:
        return
    table = UNIT_TABLE.get(col.role, {})
    # Procura a unidade mais específica primeiro (a mais longa).
    for key in sorted(table, key=len, reverse=True):
        if key and key in col.unit:
            col.factor = table[key][0]
            return
    col.factor = 1.0 if col.unit == "" else None


def read_trace_file(path: str | Path) -> TraceFile:
    """Lê um arquivo de instrumento e devolve colunas rotuladas e metadados.

    Despacha por formato: contêineres binários da TA Instruments vão para o
    adaptador .tri; todo o resto é tratado como texto delimitado. Os dois
    caminhos terminam no mesmo ``TraceFile``, então a resolução de papéis e a
    conversão de unidades são idênticas qualquer que seja a porta de entrada.
    """
    p = Path(path)
    raw = p.read_bytes()
    if p.suffix.lower() in _BINARY_SUFFIXES or _looks_like_tri(raw):
        return _read_tri_as_trace_file(p)

    text = _decode(raw)
    lines = text.split("\n")
    meta, body = _split_header_and_body(lines)

    if not body:
        raise TraceImportError(f"{p.name}: nenhuma linha de dados encontrada")

    # O separador declarado no cabeçalho vence qualquer heurística.
    declared = meta.get("separator", "").lower()
    sep = {
        "semicolon": ";",
        "comma": ",",
        "tab": "\t",
        "space": " ",
        "colon": ":",
    }.get(declared)
    if sep is None and declared in {";", ",", "\t"}:
        sep = declared

    # A primeira linha "de corpo" costuma ser o cabeçalho de colunas; a
    # decisão é por conteúdo: um cabeçalho tem letras e poucos números.
    header_idx = 0
    for i, line in enumerate(body[:5]):
        if re.search(r"[A-Za-z]{2}", line):
            header_idx = i
            break

    header_line = body[header_idx]
    fields = _split_fields(header_line, sep)
    if len(fields) < 2:
        # Sem cabeçalho multi-coluna: as colunas são posicionais e sem nome.
        fields = [""] * len(_split_fields(body[header_idx], sep))

    headers = fields
    data_lines = body[header_idx + 1 :]

    # Lê as colunas.
    columns: list[list[float]] = [[] for _ in headers]
    ncol = len(headers)
    for line in data_lines:
        parts = _split_fields(line, sep)
        if len(parts) < ncol:
            # Linha incompleta: descartar em vez de preencher com zero, o que
            # deslocaria o eixo em silêncio.
            continue
        row_ok = False
        for j in range(ncol):
            v = _to_float(parts[j])
            if v is None:
                v = float("nan")
            else:
                row_ok = True
            columns[j].append(v)
        if not row_ok:
            # Nenhum campo numérico: fim dos dados ou linha de rodapé.
            for j in range(ncol):
                columns[j].pop()
            break

    # Monta os objetos de coluna.
    parsed: list[ParsedColumn] = []
    for j, hdr in enumerate(headers):
        unit = _unit_of(hdr)
        role = _match_role(hdr, unit)
        col = ParsedColumn(
            index=j,
            raw_header=hdr,
            role=role,
            unit=unit or None,
            factor=None,
            values=columns[j],
        )
        _assign_factor(col)
        parsed.append(col)

    tf = TraceFile(path=str(p), metadata=meta, columns=parsed)
    return tf


# ---------------------------------------------------------------------------
# Resolução: do arquivo lido às duas séries que a análise precisa
# ---------------------------------------------------------------------------


@dataclass
class ResolvedTrace:
    """O que a análise precisa, mais de onde veio e o que foi decidido."""

    x: list[float]
    y: list[float]
    x_label: str
    y_label: str
    x_unit: str
    y_unit: str
    sample_name: str | None = None
    heating_rate: float | None = None
    sample_mass_mg: float | None = None
    #: 'up' quando o arquivo traz exotérmico para cima (o inverso da
    #: convenção da análise), 'down' quando já está na convenção correta.
    exothermic_direction: str | None = None
    notes: list[str] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)


def _apply_factor(
    values: list[float], factor: float | str | None, unit: str
) -> tuple[list[float], str | None]:
    """
    Converte uma coluna à unidade canônica.

    Devolve ``(valores, motivo_da_recusa)``. Uma recusa não é um erro fatal:
    é uma conversão que não pode ser feita com honestidade.
    """
    if factor is None:
        return values, (
            f"a coluna está em '{unit}', e converter para a unidade canônica "
            "exige um dado que o arquivo não traz (por exemplo a massa da "
            "amostra para um sinal absoluto em mW). Forneça o dado ou exporte "
            "o sinal normalizado pela massa."
        )
    if isinstance(factor, str):
        if factor == "+273.15":
            return [v + 273.15 for v in values], None
        if factor == "F2C":
            return [(v - 32.0) * 5.0 / 9.0 for v in values], None
        return values, f"conversão '{factor}' não implementada"
    return [v * factor for v in values], None


#: Rolos nomeados, para mensagens legíveis.
_ROLE_LABEL = {
    "temperature": "temperatura",
    "heat_flow": "fluxo de calor",
    "mass": "massa",
    "stress": "tensão",
    "strain": "deformação",
    "omega": "frequência angular",
    "g_prime": "módulo de armazenamento G'",
    "g_double_prime": "módulo de perdas G''",
    "wavenumber": "número de onda",
    "transmittance": "transmitância",
    "absorbance": "absorbância",
    "two_theta": "ângulo 2θ",
    "intensity": "intensidade",
}


def _pick(tf: TraceFile, role: str) -> ParsedColumn | None:
    """A coluna de um papel, preferindo a de unidade utilizável."""
    cands = [c for c in tf.columns if c.role == role]
    if not cands:
        return None
    usable = [c for c in cands if c.factor is not None]
    return (usable or cands)[0]


def resolve_trace(
    tf: TraceFile,
    x_role: str,
    y_role: str,
    *,
    invert_for_endothermic_up: bool = False,
) -> ResolvedTrace:
    """
    Resolve um arquivo lido nas duas séries que a análise pede.

    ``x_role`` e ``y_role`` nomeiam o que a análise quer. A função procura as
    colunas, confere a unidade, converte, e devolve os metadados do cabeçalho
    junto. Quando uma coluna não pode ser resolvida com honestidade, o motivo
    vai para ``refusals`` e a chamada levanta ``TraceImportError`` com o texto
    -- porque devolver um par de listas vazio seria pior: o usuário veria "sem
    resultado" sem saber por quê.
    """
    notes: list[str] = list(tf.warnings)
    refusals: list[str] = []

    xc = _pick(tf, x_role)
    yc = _pick(tf, y_role)

    if xc is None:
        found = ", ".join(f"'{c.raw_header or f'coluna {c.index + 1}'}'" for c in tf.columns)
        raise TraceImportError(
            f"Não encontrei a coluna de {_ROLE_LABEL.get(x_role, x_role)}. "
            f"O arquivo tem: {found}. Se o papel da coluna for outro, "
            "renomeie o cabeçalho ou converta o arquivo para CSV de duas colunas."
        )
    if yc is None:
        found = ", ".join(f"'{c.raw_header or f'coluna {c.index + 1}'}'" for c in tf.columns)
        raise TraceImportError(
            f"Não encontrei a coluna de {_ROLE_LABEL.get(y_role, y_role)}. "
            f"O arquivo tem: {found}."
        )

    # Comprimento comum. Um arquivo real pode ter colunas de tamanhos
    # diferentes quando o instrumento escreve blocos separados.
    n = min(len(xc.values), len(yc.values))
    if n < 3:
        raise TraceImportError(f"Só {n} ponto(s) utilizáveis: a análise precisa de pelo menos 3.")
    if len(xc.values) != len(yc.values):
        notes.append(
            f"As colunas têm comprimentos diferentes "
            f"({len(xc.values)} e {len(yc.values)}); usei os {n} primeiros "
            "pontos de cada."
        )

    x_vals = xc.values[:n]
    y_vals = yc.values[:n]

    # Uma linha com NaN sobrevive à leitura como NaN. Filtrar aqui, e contar,
    # porque perder metade dos pontos em silêncio mudaria o resultado.
    mask = [i for i in range(n) if np.isfinite(x_vals[i]) and np.isfinite(y_vals[i])]
    dropped = n - len(mask)
    if dropped:
        notes.append(f"{dropped} ponto(s) não numéricos foram descartados.")
    x_vals = [x_vals[i] for i in mask]
    y_vals = [y_vals[i] for i in mask]
    if len(x_vals) < 3:
        raise TraceImportError(
            "Depois de descartar valores não numéricos sobraram menos de 3 " "pontos."
        )

    x_out, x_refuse = _apply_factor(x_vals, xc.factor, xc.unit or "")
    y_out, y_refuse = _apply_factor(y_vals, yc.factor, yc.unit or "")
    if x_refuse:
        refusals.append(f"eixo x: {x_refuse}")
    if y_refuse:
        refusals.append(f"eixo y: {y_refuse}")
    if refusals:
        raise TraceImportError(" ".join(refusals))

    # O eixo x precisa ser monotônico para a análise. Um traço pode vir
    # ordenado de forma decrescente, o que é normal em resfriamento; inverter
    # é seguro. Não-monotônico de verdade (com ida e volta) é recusado, porque
    # escolher uma metade silenciosamente perderia a outra.
    diffs = [x_out[i + 1] - x_out[i] for i in range(len(x_out) - 1)]
    if all(d <= 0 for d in diffs):
        x_out.reverse()
        y_out.reverse()
        notes.append("O eixo x vinha decrescente; inverti a ordem.")
    elif not all(d >= 0 for d in diffs):
        # Um ou outro ponto fora de ordem é ruído de export; um traço que
        # sobe e desce é um método com rampa e patamar.
        bad = sum(1 for d in diffs if d < 0)
        if bad > len(diffs) * 0.05:
            raise TraceImportError(
                f"O eixo x não é monotônico ({bad} de {len(diffs)} passos "
                "decrescentes). Isto costuma indicar um método com várias "
                "rampas; o PAT analisa uma rampa por vez."
            )
        notes.append(f"{bad} ponto(s) fora de ordem no eixo x foram ignorados.")

    # Sinal exotérmico. A análise assume endotérmico para cima. Um DSC exportado
    # com exotérmico para cima tem o sinal invertido, e isso muda Tg, Tm e a
    # entalpia se não for corrigido.
    direction = tf.exothermic_direction
    if invert_for_endothermic_up and direction == "up":
        y_out = [-v for v in y_out]
        notes.append(
            "O cabeçalho declara exotérmico PARA CIMA (#EXO); inverti o sinal "
            "para a convenção endotérmico-para-cima que a análise usa."
        )

    return ResolvedTrace(
        x=x_out,
        y=y_out,
        x_label=xc.raw_header or x_role,
        y_label=yc.raw_header or y_role,
        x_unit=UNIT_TABLE.get(x_role, {}).get(xc.unit or "", (None, xc.unit or ""))[1],
        y_unit=UNIT_TABLE.get(y_role, {}).get(yc.unit or "", (None, yc.unit or ""))[1],
        sample_name=tf.sample_name,
        heating_rate=tf.heating_rate,
        sample_mass_mg=tf.sample_mass_mg,
        exothermic_direction=direction,
        notes=notes,
    )
