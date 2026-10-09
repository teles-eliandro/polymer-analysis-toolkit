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
        "temp", "temperature", "temperatur", "sample temp", "program temp",
        "tsample", "tzero",
    ),
    "time": ("time", "zeit", "minute", "second", "min)", "(min", "(s)", "/min"),
    "heat_flow": (
        "dsc", "heat flow", "heatflow", "heat-flow", "fluxo de calor",
        "heat flow rate", "calor",
    ),
    "mass": (
        "mass", "weight", "tga", "masse", "massa", "mass percent",
        "tga curve", "w (%)", "weight (%)", "mass (%)",
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
        "mw/mg": (1.0, "W/g"),          # numericamente idêntico: 1 mW/mg = 1 W/g
        "w/mg": (1000.0, "W/g"),
        "uw/mg": (1e-3, "W/g"),
        "mw": (None, "W/g"),            # absoluto: precisa da massa
        "w": (None, "W/g"),
        "j/g": (None, "W/g"),           # energia, não fluxo: recusar
    },
    "mass": {
        "%": (1.0, "pct"),
        "pct": (1.0, "pct"),
        "percent": (1.0, "pct"),
        "mg": (None, "pct"),            # absoluto: precisa da massa inicial
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
        "": (1.0, "pct"),               # sem unidade: assumir fração? não -- ver abaixo
    },
    "g_prime": {"pa": (1.0, "Pa"), "kpa": (1e3, "Pa"), "mpa": (1e6, "Pa")},
    "g_double_prime": {"pa": (1.0, "Pa"), "kpa": (1e3, "Pa"), "mpa": (1e6, "Pa")},
    "wavenumber": {"cm-1": (1.0, "cm-1"), "cm^-1": (1.0, "cm-1"), "cm⁻¹": (1.0, "cm-1")},
    "transmittance": {"%": (1.0, "pct"), "pct": (1.0, "pct")},
    "absorbance": {"au": (1.0, "au"), "": (1.0, "au"), "a.u.": (1.0, "au")},
    "two_theta": {"deg": (1.0, "deg"), "°": (1.0, "deg"), "degrees": (1.0, "deg"), "2theta": (1.0, "deg")},
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
            "sample mass /mg", "sample mass", "mass /mg", "size",
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
    """
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


def read_trace_file(path: str | Path) -> TraceFile:
    """Lê um arquivo de instrumento e devolve colunas rotuladas e metadados."""
    p = Path(path)
    raw = p.read_bytes()
    text = _decode(raw)
    lines = text.split("\n")
    meta, body = _split_header_and_body(lines)

    if not body:
        raise TraceImportError(f"{p.name}: nenhuma linha de dados encontrada")

    # O separador declarado no cabeçalho vence qualquer heurística.
    declared = meta.get("separator", "").lower()
    sep = {
        "semicolon": ";", "comma": ",", "tab": "\t", "space": " ",
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
    data_lines = body[header_idx + 1:]

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
        factor: float | str | None = None
        if role and unit:
            table = UNIT_TABLE.get(role, {})
            # Procura a unidade mais específica primeiro (a mais longa).
            for key in sorted(table, key=len, reverse=True):
                if key and key in unit:
                    factor = table[key][0]
                    break
            else:
                factor = 1.0 if unit == "" else None
        parsed.append(
            ParsedColumn(
                index=j,
                raw_header=hdr,
                role=role,
                unit=unit or None,
                factor=factor,
                values=columns[j],
            )
        )

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


def _apply_factor(values: list[float], factor: float | str | None, unit: str) -> tuple[list[float], str | None]:
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
        found = ", ".join(
            f"'{c.raw_header or f'coluna {c.index + 1}'}'" for c in tf.columns
        )
        raise TraceImportError(
            f"Não encontrei a coluna de {_ROLE_LABEL.get(x_role, x_role)}. "
            f"O arquivo tem: {found}. Se o papel da coluna for outro, "
            "renomeie o cabeçalho ou converta o arquivo para CSV de duas colunas."
        )
    if yc is None:
        found = ", ".join(
            f"'{c.raw_header or f'coluna {c.index + 1}'}'" for c in tf.columns
        )
        raise TraceImportError(
            f"Não encontrei a coluna de {_ROLE_LABEL.get(y_role, y_role)}. "
            f"O arquivo tem: {found}."
        )

    # Comprimento comum. Um arquivo real pode ter colunas de tamanhos
    # diferentes quando o instrumento escreve blocos separados.
    n = min(len(xc.values), len(yc.values))
    if n < 3:
        raise TraceImportError(
            f"Só {n} ponto(s) utilizáveis: a análise precisa de pelo menos 3."
        )
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
    mask = [
        i
        for i in range(n)
        if np.isfinite(x_vals[i]) and np.isfinite(y_vals[i])
    ]
    dropped = n - len(mask)
    if dropped:
        notes.append(f"{dropped} ponto(s) não numéricos foram descartados.")
    x_vals = [x_vals[i] for i in mask]
    y_vals = [y_vals[i] for i in mask]
    if len(x_vals) < 3:
        raise TraceImportError(
            "Depois de descartar valores não numéricos sobraram menos de 3 "
            "pontos."
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
