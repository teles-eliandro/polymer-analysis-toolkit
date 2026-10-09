"""O modulo FTIR nao pode aceitar transmitancia em silencio.

Contexto (achado ao validar contra os 59 espectros reais do figshare 24593022,
CC-BY-4.0): o instrumento exporta **transmitancia** (%T), e a ferramenta pede
**absorbancia**. Passar o arquivo como ele vem nao da erro -- devolve cerca de
100 picos por espectro, quase todos ruido, porque uma banda de transmitancia e
uma rampa monotona enorme e o localizador de picos le cada ondulacao dela.

Medido nos 59 espectros reais:

    unidade                 picos (mediana)   plausivel (<=25 picos)
    transmitancia (arquivo)        100                1 / 58
    absorbancia (convertida)        16               48 / 52

Medicao direta no PE-1, cujas bandas sao conhecidas:
    transmitancia -> 103 picos, comecando em 3998 cm-1 (nada fisico)
    absorbancia   ->   4 picos: 2915, 2848, 1473, 730 cm-1
                      = exatamente as bandas CH2 do polietileno

A ferramenta rejeitava absorbancia negativa com uma mensagem clara, mas aceitava
transmitancia sem dizer nada. Os dois erros vem do mesmo engano de unidade e
merecem o mesmo tratamento: recusar, dizendo o que fazer.

Estes testes fixam isso.
"""
import numpy as np
import pytest

from app.core.structure import analyse_ftir


def _pe_spectrum():
    """Espectro tipo PE: bandas CH2 em 2915, 2848, 1473, 730 cm-1, em %T."""
    wn = np.linspace(4000.0, 400.0, 1801)
    T = np.full_like(wn, 95.0)  # baseline de transmitancia
    for centre, depth, width in [
        (2915.0, 45.0, 25.0),
        (2848.0, 30.0, 20.0),
        (1473.0, 35.0, 15.0),
        (730.0, 40.0, 12.0),
    ]:
        T -= depth * np.exp(-0.5 * ((wn - centre) / width) ** 2)
    return wn, T


def test_transmittance_is_rejected_with_a_usable_message():
    """
    Passar %T tem de falhar, nao devolver uma centena de picos falsos.

    Este e o erro que um pesquisador comete naturalmente: exportar do
    instrumento e colar. A mensagem precisa dizer o que fazer.
    """
    wn, T = _pe_spectrum()

    with pytest.raises(ValueError) as exc:
        analyse_ftir(wn, T)

    msg = str(exc.value).lower()
    # A mensagem tem de nomear a unidade errada e a conversao correta.
    assert "transmittance" in msg or "transmitancia" in msg
    assert "log10" in msg or "absorbance" in msg


def test_absorbance_still_works_and_finds_the_real_bands():
    """
    A conversao correta continua funcionando e acha as bandas do PE.

    Trava o comportamento bom: se a deteccao de unidade ficar agressiva demais e
    passar a recusar absorbancia legitima, isto quebra.
    """
    wn, T = _pe_spectrum()
    A = -np.log10(T / 100.0)

    result = analyse_ftir(wn, A)

    assert len(result.detected_peaks) < 25, (
        f"{len(result.detected_peaks)} picos num espectro de 4 bandas -- "
        "a deteccao de picos esta lendo ruido"
    )
    found = np.asarray(result.detected_peaks)
    for expected in (2915.0, 2848.0, 1473.0, 730.0):
        assert np.min(np.abs(found - expected)) < 12.0, (
            f"banda do PE em {expected} cm-1 nao foi detectada; "
            f"achados: {sorted(found)[:10]}"
        )


def test_a_genuine_absorbance_spectrum_is_not_mistaken_for_transmittance():
    """
    Absorbancia real nao e rejeitada por engano.

    Absorbancia de espectro limpo fica tipicamente entre 0 e ~2 (unidades de
    absorbancia). Uma transmitancia fica entre 0 e 100. A discriminacao nao pode
    ser so "os valores sao maiores que 100", porque uma transmitancia com
    baseline em 80 % ja seria ambigua -- e um espectro de absorbancia com pico
    em 3 tambem.

    O que distingue de verdade: a cauda da transmitancia tem o comportamento de
    uma rampa que cai (a linha de base decresce monotonicamente com a
    inclinacao do baseline), enquanto a absorbancia de bandas fica perto de zero
    fora das bandas. Aqui um espectro de absorbancia com valores baixos passa.
    """
    wn = np.linspace(4000.0, 400.0, 1801)
    A = 0.05 + 0.9 * np.exp(-0.5 * ((wn - 2915.0) / 25.0) ** 2)
    A += 0.6 * np.exp(-0.5 * ((wn - 1473.0) / 15.0) ** 2)

    result = analyse_ftir(wn, A)

    found = np.asarray(result.detected_peaks)
    assert found.size >= 2
    assert np.min(np.abs(found - 2915.0)) < 12.0
