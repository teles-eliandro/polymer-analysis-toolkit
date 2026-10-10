"""A tabela de referência tem de estar traduzida por inteiro.

``options()`` cai no português quando falta uma tradução. É o comportamento
certo para não perder o dado, e o errado para o leitor: ele vê uma lista em
inglês com entradas em português e conclui que a ferramenta está quebrada --
que é exatamente o defeito que originou este teste.

Nada falha quando uma tradução some. Não há exceção, não há aviso, não há
teste vermelho: o campo simplesmente reaparece no idioma de origem. Por isso a
paridade é verificada aqui, e não confiada à revisão.

O que **não** é verificado, e é deliberado: ``source``. A citação fica no
idioma do documento nas três versões. Traduzir "The reflection of X-rays by
crystals" produziria uma referência que o artigo não usa.
"""

from __future__ import annotations

from app.core.crystallinity_ref import ENTHALPY_DB
from app.core.crystallinity_ref_i18n import CRYSTAL_FORM, DISPLAY_NAME, NOTE

LANGUAGES = ("en", "es")


def _entry_keys() -> set[str]:
    return set(ENTHALPY_DB)


def _note_keys() -> set[str]:
    """As chaves de nota que o banco realmente usa, no formato do módulo i18n."""
    keys: set[str] = set()
    for key, entry in ENTHALPY_DB.items():
        if entry.note:
            keys.add(f"{key}.poly")
        for i, ref in enumerate(entry.references):
            if ref.note:
                keys.add(f"{key}.ref{i}")
    return keys


def _crystal_forms() -> set[str]:
    forms: set[str] = set()
    for entry in ENTHALPY_DB.values():
        for ref in entry.references:
            if ref.crystal_form:
                forms.add(ref.crystal_form)
    return forms


def test_every_polymer_has_a_translated_name() -> None:
    faltando = []
    for key in _entry_keys():
        entry = DISPLAY_NAME.get(key) or {}
        for lang in LANGUAGES:
            if not (entry.get(lang) or "").strip():
                faltando.append(f"{key}.{lang}")
    assert not faltando, (
        f"{len(faltando)} nome(s) sem tradução -- apareceriam em português no "
        f"meio de uma lista em inglês: {sorted(faltando)}"
    )


def test_every_crystal_form_has_a_translation() -> None:
    faltando = []
    for form in _crystal_forms():
        entry = CRYSTAL_FORM.get(form) or {}
        for lang in LANGUAGES:
            if not (entry.get(lang) or "").strip():
                faltando.append(f"{form!r}.{lang}")
    assert not faltando, (
        f"{len(faltando)} forma(s) cristalina(s) sem tradução: {sorted(faltando)}"
    )


def test_every_note_has_a_translation() -> None:
    faltando = []
    for key in _note_keys():
        entry = NOTE.get(key) or {}
        for lang in LANGUAGES:
            if not (entry.get(lang) or "").strip():
                faltando.append(f"{key}.{lang}")
    assert not faltando, (
        f"{len(faltando)} nota(s) sem tradução -- a mais visível das falhas, "
        f"porque a nota aparece embaixo do campo: {sorted(faltando)}"
    )


def test_no_orphan_translations() -> None:
    """Tradução de uma chave que não existe mais é uma chave renomeada pela metade."""
    orfas = {
        "DISPLAY_NAME": sorted(set(DISPLAY_NAME) - _entry_keys()),
        "NOTE": sorted(set(NOTE) - _note_keys()),
        "CRYSTAL_FORM": sorted(set(CRYSTAL_FORM) - _crystal_forms()),
    }
    orfas = {k: v for k, v in orfas.items() if v}
    assert not orfas, f"traduções órfãs (chave renomeada?): {orfas}"


def test_the_citation_is_never_translated() -> None:
    """
    ``source`` tem de sair idêntica nas três línguas.

    Se um dia alguém traduzir a citação, o DOI e o título do artigo deixam de
    casar com o que a base bibliográfica tem, e quem for buscar o documento não
    o encontra. É a asserção que trava essa "melhoria" bem-intencionada.
    """
    from app.core.crystallinity_ref import options

    por_idioma = {lang: {e["key"]: e["source"] for e in options(lang)} for lang in ("pt", "en", "es")}
    for key in por_idioma["pt"]:
        fontes = {lang: por_idioma[lang][key] for lang in por_idioma}
        assert len(set(fontes.values())) == 1, f"{key}: citação traduzida em {fontes}"


def test_the_three_languages_actually_differ() -> None:
    """
    Uma tradução copiada é pior que uma ausente: parece pronta e não é.

    Compara o nome de cada polímero entre as três línguas e exige que nem todos
    sejam iguais -- há nomes legitimamente idênticos ("Nylon 6" é Nylon 6 nos
    três), então a asserção é sobre o conjunto, não sobre cada entrada.
    """
    from app.core.crystallinity_ref import options

    nomes = {lang: {e["key"]: e["label"] for e in options(lang)} for lang in ("pt", "en", "es")}
    iguais = [k for k in nomes["pt"] if nomes["pt"][k] == nomes["en"][k] == nomes["es"][k]]
    assert len(iguais) < len(nomes["pt"]), (
        "todos os nomes são idênticos nos três idiomas -- a tradução não foi aplicada"
    )
    # E o inglês tem de diferir do português em algum ponto, ou nada foi traduzido.
    assert any(nomes["pt"][k] != nomes["en"][k] for k in nomes["pt"])


def test_unknown_language_falls_back_to_the_source_language() -> None:
    """Um código de idioma fora da lista não pode devolver campo vazio."""
    from app.core.crystallinity_ref import options

    pt = {e["key"]: e["label"] for e in options("pt")}
    xx = {e["key"]: e["label"] for e in options("xx")}
    assert xx == pt
