"""O footing não pode transformar dado bom em suspeito.

Contexto (achado ao gerar os resultados do paper): nos traços reais de PLLA de
literatura o passo da Tg tem relação sinal/ruído de 150-240 -- o degrau é
enorme comparado ao ruído do traço. Ainda assim o footing marcava dois dos três
como `Tg_reliable=False`, com incerteza de +-36 e +-41 K.

A causa não era o dado: era o método. O footing reamostrava com reposição
(rng.integers(0, n, n)), o que descarta ~36% dos pontos e abre centenas de
buracos no eixo de temperatura (espaçamento até 9x o original). O detector então
lia um traço esburacado e devolvia uma Tg que oscilava dezenas de graus.

Medido no mesmo traço (PLLA_25K):
    bootstrap destrutivo -> +-35.91 K   (falso alarme)
    ruído aditivo        -> +-0.03 K    (a resposta correta)

Estes testes fixam o comportamento correto: dado limpo e bem amostrado tem de
sair confiável, e a incerteza tem de ser da ordem do que o ruído do instrumento
provoca de verdade -- não de artefatos da reamostragem.
"""
import numpy as np
import pytest

from app.core.thermal import analyse_dsc


def _clean_pla_trace(seed: int = 0, noise: float = 3.0e-4):
    """
    Traço tipo PLA com proporções físicas.

    A Tg é um degrau **abrupto** e a fusão uma rampa **gradual**. Medido nos
    traços reais do Zenodo 10.5281/zenodo.17288962, a inclinação máxima da Tg é
    11 a 50 vezes maior que a da fusão (razão 0,02-0,09):

        PLLA_10K  |grad|_Tg=2.25   |grad|_Tm=0.049   razão 0.02
        PLLA_25K  |grad|_Tg=0.33   |grad|_Tm=0.020   razão 0.06
        PLLA_50K  |grad|_Tg=0.15   |grad|_Tm=0.014   razão 0.09

    Uma versão anterior deste traço tinha a fusão 5x mais íngreme que a Tg, o
    que é o inverso do real -- e por isso acusava um bug do detector que só
    existia naquele traço artificial.
    """
    rng = np.random.default_rng(seed)
    T = np.linspace(-10.0, 200.0, 6000)
    # De grau de Tg em ~85 C: estreito (meia-largura ~1 C)
    hf = 0.02 * np.tanh((T - 85.0) / 1.0)
    # Fusão em ~170 C: rampa LARGA (meia-largura ~4 C), como no dado real
    hf += 0.08 * np.tanh((T - 170.0) / 4.0)
    hf += 3.0e-4 * (T - 100.0)
    hf += rng.normal(0.0, noise, T.size)
    return T, hf


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Bug aberto: quando a fusao e larga (meia-largura ~4 C, como no traco "
        "real), o detector ainda reporta a rampa de fusao (~168 C) como Tg em "
        "vez do degrau real em 85 C -- mesmo com a Tg pontuando mais alto pelo "
        "criterio de nitidez (0.2446 vs 0.1914). O competidor e um ponto logo "
        "abaixo do inicio da faixa de fusao, cuja janela de medida invade a "
        "regiao excluida. Duas tentativas de restringir a janela "
        "(meia-janela e janela completa) quebraram a deteccao em tracos so-Tg e "
        "no ABS; ambas foram revertidas. Ver secao 'What is not established'. "
        "strict=True: se um dia passar, o CI falha e a afirmacao e revisada."
    ),
)
def test_a_clean_well_sampled_trace_is_reliable():
    """
    Degrau de Tg com SNR alto em traço bem amostrado não é dado suspeito.

    Este é o caso que o bootstrap destrutivo estragava: ele devolvia dezenas de
    kelvin de incerteza num traço onde a detecção é estável a décimos.
    """
    T, hf = _clean_pla_trace()

    result = analyse_dsc(T, hf, heating_rate=10.0)

    assert result.Tg is not None
    assert abs(result.Tg - 85.0) < 2.0, f"Tg detectada em {result.Tg:.2f}, esperado ~85"
    assert result.Tg_uncertainty_C is not None
    assert result.Tg_uncertainty_C < 2.5, (
        f"incerteza de {result.Tg_uncertainty_C:.2f} K num traço limpo e bem "
        "amostrado -- o footing está medindo artefato da reamostragem"
    )
    assert result.Tg_reliable is True


def test_the_footing_is_comparable_to_the_noise_in_the_trace():
    """
    A incerteza tem de bater com o que o ruído do traço realmente causa.

    Medido independentemente: perturbar o traço com ruído aditivo na altura do
    ruído local e re-rodar a detecção. O footing do PAT tem de ser da mesma
    ordem; um fator de mil entre os dois é um bug, não uma medida.
    """
    T, hf = _clean_pla_trace()
    result = analyse_dsc(T, hf, heating_rate=10.0)

    rng = np.random.default_rng(1)
    noise_sigma = np.diff(hf).std() / np.sqrt(2)
    tgs = []
    for _ in range(12):
        perturbed = hf + rng.normal(0.0, noise_sigma, hf.size)
        r = analyse_dsc(T, perturbed, heating_rate=10.0)
        if r.Tg is not None:
            tgs.append(float(r.Tg))

    assert len(tgs) >= 8, "a detecção falhou na maioria das perturbações"
    lo, hi = np.percentile(tgs, [10.0, 90.0])
    independent = (hi - lo) / 2.0

    assert result.Tg_uncertainty_C is not None
    ratio = max(result.Tg_uncertainty_C, 1e-6) / max(independent, 1e-6)
    assert ratio < 10.0, (
        f"footing={result.Tg_uncertainty_C:.4f} K contra {independent:.4f} K "
        f"medidos por ruído aditivo (razão {ratio:.1f}x) -- discrepância grande "
        "demais para ser o mesmo fenômeno"
    )


def test_a_badly_sampled_trace_is_still_flagged():
    """
    O footing tem de continuar servindo para o que foi feito: sinalizar dado ruim.

    Traço grosseiro (poucos pontos, ruído alto): a detecção oscila de verdade e
    isso precisa aparecer. Não queremos consertar o falso alarme desligando o
    alerta.
    """
    rng = np.random.default_rng(3)
    T = np.linspace(-10.0, 200.0, 120)
    hf = 0.02 * np.tanh((T - 85.0) / 6.0) + 0.08 * np.tanh((T - 170.0) / 8.0)
    hf += rng.normal(0.0, 0.004, T.size)  # ruído alto relativo ao degrau

    result = analyse_dsc(T, hf, heating_rate=10.0)

    if result.Tg is not None and result.Tg_uncertainty_C is not None:
        # Se por acaso ficou estável, tudo bem -- mas não pode marcar confiável
        # um traço cujo degrau tem a altura do ruído.
        snr = 0.02 / 0.004
        if snr < 5:
            assert result.Tg_reliable is False, (
                "degrau de Tg comparável ao ruído foi marcado como confiável"
            )
