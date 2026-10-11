"""A prosa do backend tem de sair na lingua que o cliente pediu.

Porque este teste existe
------------------------
A camada 2 do i18n ligou o catalogo as mensagens do caminho termico. Um
catalogo correto, ligado no sitio errado, devolve portugues a quem pediu
ingles -- e a unica forma de saber se o ``lang`` chegou mesmo ao codigo e
pedir a mesma coisa em duas linguas e comparar as respostas.

Os testes unitarios do catalogo verificam a *forma* (placeholders iguais,
todas as linguas presentes). Este verifica o *percurso*: pedido HTTP ->
endpoint -> leitor -> catalogo -> resposta. A ligacao entre os dois nao e
coberta por nenhum teste de forma, e foi essa ligacao que ficou a faltar
quando a camada 2 esteve meio feita.

Duas armadilhas que se evitam aqui:

* verificar so que o texto muda nao chega -- dois idiomas podem devolver a
  mesma string de erro generica e o teste passaria;
* verificar uma palavra-chave isolada e fragil, mas e o que liga a resposta a
  uma lingua concreta. Usa-se em conjunto com a diferenca entre as tres.
"""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app

IDIOMAS = ("pt", "en", "es")

#: Um ficheiro binario. O leitor recusa-o com a mensagem ``trace.binary_file``,
#: que e prosa e portanto tem traducao.
BINARIO = b"\x00\x01\x02\xff\xfe\x00\x00binary\x00\x01"


@pytest.fixture(scope="module")
def cliente() -> TestClient:
    return TestClient(app)


def _importar(cliente: TestClient, dados: bytes, lang: str):
    return cliente.post(
        "/api/v1/thermal/import",
        files={"file": ("x.txt", dados, "text/plain")},
        data={"target": "tga", "lang": lang},
    )


def test_the_reader_refusal_comes_back_in_each_language(cliente: TestClient):
    """As tres linguas tem de dar tres textos diferentes."""
    textos = {}
    for lang in IDIOMAS:
        r = _importar(cliente, BINARIO, lang)
        assert r.status_code == 400, f"{lang}: esperava 400, veio {r.status_code}"
        textos[lang] = r.json()["detail"]

    assert len(set(textos.values())) == 3, (
        "as tres linguas devolveram o mesmo texto: o lang nao chegou ao leitor\n"
        f"pt={textos['pt']!r}\nen={textos['en']!r}\nes={textos['es']!r}"
    )


def test_each_language_contains_its_own_marker(cliente: TestClient):
    """Prova positiva: nao basta serem diferentes, tem de ser a lingua certa.

    Comparar so a diferenca deixaria passar o caso em que o texto muda por
    outro motivo qualquer (um numero, um nome de ficheiro).
    """
    pt = _importar(cliente, BINARIO, "pt").json()["detail"]
    en = _importar(cliente, BINARIO, "en").json()["detail"]
    es = _importar(cliente, BINARIO, "es").json()["detail"]

    assert "parece binário" in pt
    assert "looks binary" in en
    assert "parece binario" in es  # espanhol nao acentua "binario"

    # E o texto ingles nao pode conter a prosa portuguesa, nem o contrario:
    # e a mistura de linguas que este trabalho existe para eliminar.
    assert "binário" not in en and "binário" not in es
    assert "binario, no una" not in pt


def test_an_unknown_language_is_rejected_not_silently_translated(cliente: TestClient):
    """Um codigo fora do conjunto nao pode virar portugues em silencio.

    O servidor devolver uma lingua diferente da pedida sem avisar e pior do
    que recusar: o cliente nao tem como saber que o pedido foi ignorado. O
    conjunto e fechado e igual nos tres pontos de entrada.
    """
    assert _importar(cliente, BINARIO, "xx").status_code == 422

    r = cliente.post(
        "/api/v1/thermal/tga",
        json={"temperature": [1, 2, 3, 4, 5], "mass_pct": [100, 90, 80, 70, 60], "lang": "de"},
    )
    assert r.status_code == 422

    r = cliente.get("/api/v1/thermal/crystallinity-references", params={"lang": "fr"})
    assert r.status_code == 422


def test_analysis_notes_also_follow_the_language(cliente: TestClient):
    """A via do payload JSON, nao so a do ficheiro.

    Um trace com duas perdas de massa distintas e classificado como tendo
    varios passos, e isso e dito numa nota. A nota e prosa, logo tem idioma.

    Escolheu-se esta nota por ser deterministica: as outras dependem de
    limiares fisicos (residuo negativo, inicio abaixo de 100 %) que uma
    fixture inventada facilmente nao cruza -- a primeira versao deste teste
    usava uma e recebia uma lista vazia, passando por engano se so se
    verificasse "nao rebentou".
    """
    T = np.linspace(25.0, 600.0, 260)
    m = (
        100.0
        - 30.0 / (1.0 + np.exp(-(T - 150.0) / 8.0))
        - 50.0 / (1.0 + np.exp(-(T - 450.0) / 10.0))
        + np.random.default_rng(3).normal(0.0, 0.02, T.size)
    )
    corpo = {"temperature": T.tolist(), "mass_pct": m.tolist()}

    textos = {}
    for lang in IDIOMAS:
        r = cliente.post("/api/v1/thermal/tga", json={**corpo, "lang": lang})
        assert r.status_code == 200, r.text
        notas = r.json().get("notes") or []
        assert notas, f"{lang}: a analise nao produziu nota nenhuma"
        textos[lang] = " | ".join(notas)

    assert len(set(textos.values())) == 3, f"as notas nao seguiram o idioma:\n{textos}"
    assert "Foram detectados vários passos" in textos["pt"]
    assert "Several steps were detected" in textos["en"]
    assert "Se detectaron varios pasos" in textos["es"]


def test_the_default_language_is_portuguese(cliente: TestClient):
    """Sem ``lang``, a resposta e a de origem.

    Um cliente antigo (o que nao envia o campo) nao pode mudar de lingua por
    causa desta alteracao. E o contrato que mantem a mudanca compativel.
    """
    r = cliente.post(
        "/api/v1/thermal/import",
        files={"file": ("x.txt", BINARIO, "text/plain")},
        data={"target": "tga"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == _importar(cliente, BINARIO, "pt").json()["detail"]
