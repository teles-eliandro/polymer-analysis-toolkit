"""O catalogo de mensagens tem de estar ligado, e nao so a existir.

Porque este teste existe
------------------------
A camada 2 do i18n traduz a prosa que o backend devolve (recusas e avisos).
O defeito original nao foi um erro de traducao: foi uma mensagem escrita
direto no codigo, que atravessou tres idiomas sem ninguem notar. Um catalogo
com uma entrada a mais ou a menos continua a compilar, continua a passar em
todos os outros testes, e continua a servir portugues a quem pediu ingles --
exactamente o defeito que se esta a corrigir.

Estes testes fecham as duas pontas:

* um codigo usado no codigo-fonte sem entrada no catalogo levanta KeyError em
  tempo de execucao, no caminho de erro, no pior momento possivel;
* uma entrada no catalogo que ninguem usa e uma traducao que alguem escreveu
  e ninguem pode ver -- ou, pior, a assinatura de uma mensagem que ficou por
  ligar enquanto o commit diz que a camada esta feita.

O segundo e o que interessa aqui. Foi por isso que a camada 2 ficou meio
feita uma vez.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core.messages_i18n import IDIOMA_ORIGEM, IDIOMAS, MSG, ROLE, msg, role_label

#: Onde se procura por ``msg(...)``. Inclui os testes, porque um teste que
#: verifica o texto de uma recusa tambem e um consumidor do catalogo.
RAIZ = Path(__file__).resolve().parents[1]
DIRETORIOS = (RAIZ / "app", RAIZ / "tests", RAIZ / "scripts")

_RE_MSG = re.compile(r"""\bmsg\(\s*["']([a-zA-Z0-9_.]+)["']""")
_RE_ROLE = re.compile(r"""\brole_label\(\s*["']([a-zA-Z0-9_.]+)["']""")


def _codigos_usados() -> tuple[set[str], set[str]]:
    """Le os codigos citados no codigo-fonte, sem importar nada."""
    usados_msg: set[str] = set()
    usados_role: set[str] = set()
    for pasta in DIRETORIOS:
        if not pasta.exists():
            continue
        for caminho in pasta.rglob("*.py"):
            # O catalogo cita os codigos como chaves, e este teste cita-os
            # como provas (``role_label("nao_existe", ...)``): nenhum dos dois
            # e um consumidor real, e conta-los daria sempre falso positivo.
            if caminho.name in ("messages_i18n.py", "test_messages_i18n.py"):
                continue
            texto = caminho.read_text(encoding="utf-8")
            usados_msg |= set(_RE_MSG.findall(texto))
            usados_role |= set(_RE_ROLE.findall(texto))
    return usados_msg, usados_role


def test_every_code_used_in_the_source_exists_in_the_catalog():
    """Um codigo sem entrada levanta KeyError no caminho de erro."""
    usados_msg, usados_role = _codigos_usados()

    faltam_msg = sorted(usados_msg - set(MSG))
    faltam_role = sorted(usados_role - set(ROLE))

    assert not faltam_msg, f"msg() sem entrada no catalogo: {faltam_msg}"
    assert not faltam_role, f"role_label() sem entrada no catalogo: {faltam_role}"


def test_every_catalog_entry_is_actually_used():
    """Uma entrada que ninguem usa e traducao que ninguem pode ver.

    Este e o teste que teria apanhado a camada 2 meio feita: o catalogo
    escrito e validado, mas ainda nao ligado as mensagens.
    """
    usados_msg, _ = _codigos_usados()

    orfas = sorted(set(MSG) - usados_msg)

    assert not orfas, f"entrada no catalogo que ninguem usa: {orfas}"


def test_every_role_the_reader_can_resolve_has_a_label():
    """Os rotulos nao se verificam por literal, e sim pelo que o leitor produz.

    ``role_label(x_role, lang)`` recebe uma variavel, nao um codigo escrito --
    por isso procurar ``role_label("mass")`` no codigo-fonte nao encontra nada
    e daria os 14 rotulos como orfaos. O que interessa nao e onde a funcao e
    chamada, e sim se o conjunto de papeis que o leitor consegue devolver tem
    exactamente os rotulos que existem.

    Os papeis em ``IGNORED_ROLES`` ficam de fora de proposito: sao colunas que
    o leitor descarta e nunca nomeia a quem le. Excepto por uma via: ``x_role``
    e ``y_role`` chegam como texto livre no formulario do endpoint, e uma
    recusa nomeia o papel *pedido* -- ``time`` continua alcancavel por ai, e
    por isso o rotulo fica. A verificacao inversa (rotulo sem papel) nao e
    possivel: nao ha lista fechada de papeis, ja que o pedido e do cliente.
    """
    from app.core.trace_io import _AXIS_ROLE_BY_UNIT, COLUMN_ROLES, IGNORED_ROLES

    resolviveis = set(COLUMN_ROLES) | set(_AXIS_ROLE_BY_UNIT.values()) | {"absorbance"}
    nomeaveis = resolviveis - set(IGNORED_ROLES)

    sem_rotulo = sorted(nomeaveis - set(ROLE))

    assert not sem_rotulo, f"papel que o leitor pode devolver e nao tem rotulo: {sem_rotulo}"


@pytest.mark.parametrize("codigo", sorted(MSG))
def test_placeholders_are_the_same_in_every_language(codigo: str):
    """Um ``{nome}`` a menos num idioma e um valor que desaparece da frase.

    A frase continua a ser formada, o ``.format()`` nao falha, e o numero
    que o leitor precisava de ver simplesmente nao esta la. Nada o apanha.
    """
    variantes = MSG[codigo]
    esperado: set[str] = set()
    for idioma in IDIOMAS:
        assert idioma in variantes, f"{codigo}: falta o idioma {idioma!r}"
        encontrados = set(re.findall(r"\{(\w+)", variantes[idioma]))
        if not esperado:
            esperado = encontrados
        else:
            assert encontrados == esperado, (
                f"{codigo}/{idioma}: placeholders {sorted(encontrados)} != "
                f"{sorted(esperado)}"
            )


@pytest.mark.parametrize("codigo", sorted(MSG))
def test_every_language_actually_renders(codigo: str):
    """Formata cada variante com valores de prova, para apanhar chaves mal escritas."""
    for idioma in IDIOMAS:
        texto = msg(codigo, idioma, **_valores_de_prova(MSG[codigo][idioma]))
        assert texto and not re.search(r"\{[a-zA-Z_]\w*\}", texto), (
            f"{codigo}/{idioma}: sobrou um placeholder por preencher -> {texto!r}"
        )


def test_source_language_is_portuguese():
    """O idioma de origem e o que o backend escreve por omissao.

    Fixa-lo num teste evita a mudanca silenciosa: se o padrao passasse a
    ingles, todos os clientes antigos (que nao enviam ``lang``) mudariam de
    lingua sem que nenhum teste se queixasse.
    """
    assert IDIOMA_ORIGEM == "pt"


def test_unknown_language_falls_back_to_the_source():
    """Pedir um idioma que nao existe devolve o texto de origem, nao um erro.

    Uma frase em portugues e util; uma excepcao no caminho de erro esconde o
    erro verdadeiro.
    """
    codigo = "trace.axis.x"
    assert msg(codigo, "xx", reason="teste") == MSG[codigo]["pt"].format(reason="teste")
    assert msg(codigo, None, reason="teste") == MSG[codigo]["pt"].format(reason="teste")


def test_role_label_falls_back_to_the_code_itself():
    """Um papel desconhecido tem de aparecer na frase, nao virar None.

    ``None`` dentro de uma f-string escreve "None" no meio da recusa.
    """
    assert role_label("nao_existe", "pt") == "nao_existe"


def _valores_de_prova(texto: str) -> dict[str, object]:
    """Valores plausiveis para os placeholders, derivados do nome deles.

    O tipo tem de casar com o formato: ``{ppd:.1f}`` com uma string levanta
    ValueError, e ``msg`` engole isso e devolve o molde por preencher -- que
    e exactamente o que este teste procura, mas por engano. O formato declarado
    e a unica fonte fiavel do tipo, por isso le-se o formato, nao o nome.
    """
    valores: dict[str, object] = {}
    for nome, formato in re.findall(r"\{(\w+)(?::([^}]*))?\}", texto):
        if formato and any(c in formato for c in "d"):
            valores[nome] = 5
        elif formato and any(c in formato for c in "fegE"):
            valores[nome] = 42.5
        elif nome in ("n", "bad", "dropped", "total", "nx", "ny", "i", "j"):
            valores[nome] = 5
        elif nome in ("xc", "dhm", "value", "ref", "ppd", "span", "minimum"):
            valores[nome] = 42.5
        else:
            valores[nome] = "prova"
    return valores
