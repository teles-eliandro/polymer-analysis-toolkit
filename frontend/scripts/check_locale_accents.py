#!/usr/bin/env python3
"""Portao de build: valores pt/es nao podem perder acento.

Por que isto e um portao e nao um teste de unidade como os outros: o defeito
que este arquivo previne nao quebra nada. A aplicacao compila, os testes passam,
a pagina renderiza -- e o texto sai "Medias numerica e ponderal" no lugar de
"Medias numerica e ponderal" com acento. Nenhum teste funcional pega isso,
porque o valor continua sendo uma string nao vazia e as chaves continuam em
paridade. So um humano lendo a tela pega.

O que ele NAO faz: nao tem lista completa de palavras. Uma lista de palavras
encontra so o que ja se sabia procurar. Ele e um alarme para o vocabulario que
importa neste dominio (modulo, tensao, deformacao, distribuicao, numero...),
que e onde o defeito realmente apareceu.

Acerto que nao e defeito: manter em NAO_LEVAM_ACENTO. Acentuar "energia" em
portugues, ou "media"/"tolerancia" em espanhol, introduz um erro novo -- o
oposto do que este portao quer.

Uso:  python3 scripts/check_locale_accents.py     (saida 1 se achar pendencia)
"""
from __future__ import annotations

import re
import sys

PATH = "src/i18n/I18nContext.jsx"

#: Palavras que, neste vocabulario, sempre levam acento em portugues.
FALTANDO_PT = [
    "media", "medias", "numero", "numeros", "numerica", "numerico", "especifica",
    "especifico", "polimero", "polimeros", "distribuicao", "calibracao", "eluicao",
    "padrao", "padroes", "nao", "entao", "traco", "minimo", "minimos", "maximo",
    "maximos", "modulo", "modulos", "tensao", "deformacao", "forca", "area",
    "tres", "sao", "sera", "apos", "atraves", "funcao", "aplicacao", "condicao",
    "dimensao", "extensao", "conversao", "precisao", "medicao", "duracao",
    "fracao", "equacao", "secao", "inclinacao", "viscoelastica", "tolerancia",
    "frequencia", "residuo", "informacao", "necessario", "necessaria", "variavel",
    "variaveis", "disponivel", "responsavel", "voce", "ductil", "regiao",
    "caracterizacao", "composicao", "alem", "tambem", "proximo", "ultimo",
    "versao", "conteudo", "pratica", "metodo", "calculo", "periodo", "referencia",
    "diferenca", "possivel", "impossivel", "nivel", "util", "dificil", "facil",
    "hidrolise", "isotatico", "atatico", "sindiotatico", "polimerizacao",
    "viscosimetrica", "razoavel",
]

#: Palavras que, neste vocabulario, sempre levam acento em espanhol.
FALTANDO_ES = [
    "numero", "numeros", "numerica", "numerico", "especifica", "especifico",
    "polimero", "polimeros", "distribucion", "calibracion", "elucion", "estandar",
    "estandares", "tambien", "despues", "asi", "aqui", "razon", "condicion",
    "precision", "medicion", "informacion", "aplicacion", "direccion", "util",
    "dificil", "facil", "region", "elastico", "elastica", "elasticamente",
    "termico", "metodo", "calculo", "grafico", "caracteristica", "practica",
    "estatico", "dinamico", "maximo", "minimo", "teorico", "valido", "invalido",
    "unico", "unica", "ultimo", "proximo", "polimerizacion", "anonica",
    "sistematicamente", "automatica", "deteccion", "dispersion", "posicion",
    "erronea", "traccion", "tension", "deformacion", "energia", "perdida",
    "fraccion", "porcion", "leida",
]

#: Acertos que NAO sao defeitos. Sem esta lista o portao acusa para sempre e
#: alguem acaba "corrigindo" -- acentuando o que nao leva acento.
NAO_LEVAM_ACENTO = {
    "pt": {"energia", "tangente", "sistematicamente", "viscosimetria", "reticulada",
           "elasticamente", "crepusculo"},
    # "media", "tolerancia", "longitud" e "velocidad" NAO levam acento em
    # espanhol -- e "media"/"tolerancia" levam em portugues. Por isso as duas
    # listas sao separadas por idioma: uma lista unica acentuaria o espanhol.
    "es": {"media", "tolerancia", "longitud", "velocidad", "dispersidad", "traza",
           "muestra", "ensayo", "informa"},
}


def _fim_do_objeto(linhas: list[str], inicio: int) -> int:
    """Primeira linha em que a chave aberta em ``inicio`` fecha.

    Sem isto o ultimo bloco de idioma nao tem delimitador: nao existe um quarto
    idioma depois do espanhol para marcar onde ele acaba, entao o bloco "es"
    engolia o resto do arquivo -- o componente inteiro -- e o portao acusava
    JavaScript como se fosse espanhol sem acento.
    """
    profundidade = 0
    for i in range(inicio, len(linhas)):
        profundidade += linhas[i].count("{") - linhas[i].count("}")
        if profundidade == 0 and i > inicio:
            return i
    return len(linhas) - 1


def extrair_blocos(src: str) -> dict[str, str]:
    """Devolve o texto de cada bloco de idioma, delimitado pelo objeto MESSAGES."""
    linhas = src.split("\n")
    try:
        i_objeto = next(i for i, ln in enumerate(linhas) if re.match(r"^\s*const MESSAGES\s*=\s*\{", ln))
    except StopIteration:
        raise SystemExit("nao encontrei 'const MESSAGES = {' -- o portao precisa dele para se orientar")
    fim_objeto = _fim_do_objeto(linhas, i_objeto)

    inicios = [
        i for i in range(i_objeto, fim_objeto)
        if re.match(r"^\s{0,2}(en|pt|es)\s*:\s*\{", linhas[i])
    ]
    if len(inicios) != 3:
        raise SystemExit(f"esperava 3 blocos de idioma (en/pt/es) em MESSAGES, achei {len(inicios)}")
    blocos: dict[str, str] = {}
    for n, i in enumerate(inicios):
        idioma = re.match(r"^\s{0,2}(en|pt|es)\s*:", linhas[i]).group(1)  # type: ignore[union-attr]
        fim = inicios[n + 1] if n + 1 < len(inicios) else fim_objeto + 1
        blocos[idioma] = "\n".join(linhas[i:fim])
    return blocos


def pendentes(bloco: str, palavras: list[str], idioma: str) -> list[tuple[str, list[str]]]:
    ignorar = NAO_LEVAM_ACENTO.get(idioma, set())
    achados: list[tuple[str, list[str]]] = []
    for m in re.finditer(r"['\"]([^'\"]{3,})['\"]", bloco):
        valor = m.group(1)
        if not re.search(r"[A-Za-z]", valor):
            continue
        acertos = [
            w for w in palavras
            if w not in ignorar
            and re.search(r"(?<![A-Za-zÀ-ÿ])" + w + r"(?![A-Za-zÀ-ÿ])", valor, re.I)
        ]
        if acertos:
            achados.append((valor, sorted(set(acertos))))
    return achados


def main() -> int:
    src = open(PATH, encoding="utf-8").read()
    blocos = extrair_blocos(src)

    falhas = 0
    for idioma, palavras in (("pt", FALTANDO_PT), ("es", FALTANDO_ES)):
        achados = pendentes(blocos[idioma], palavras, idioma)
        if not achados:
            print(f"  {idioma}: ok")
            continue
        falhas += len(achados)
        print(f"  {idioma}: {len(achados)} valor(es) com acento faltando")
        for valor, acertos in achados[:20]:
            print(f"      [{', '.join(acertos[:4])}] {valor[:90]}")

    if falhas:
        print(
            f"\nFALHOU: {falhas} valor(es). Corrija os acentos no dicionario.\n"
            "Se um acerto for falso positivo, adicione a palavra a NAO_LEVAM_ACENTO\n"
            "com um comentario explicando -- nao acentue a palavra."
        )
        return 1
    print("\nok: nenhum valor pt/es com acento faltando neste vocabulario")
    return 0


if __name__ == "__main__":
    sys.exit(main())
