#!/usr/bin/env python3
"""Camada 3: separa citacao de prosa nas referencias das formulas.

O que estava errado
-------------------
Os 25 blocos ``reference=`` dos paineis eram strings literais em ingles, e cada
uma misturava duas coisas com regras de traducao OPOSTAS:

  "ASTM D638-22, Standard Test Method for Tensile Properties of Plastics;
   ISO 527-1:2019. Both require the modulus from the initial linear region."

A primeira parte e uma citacao -- um nome que um leitor vai procurar literalmente,
e que traduzido nao recupera nada. A segunda e prosa, escrita para quem le a
pagina. Numa string unica so da para traduzir as duas juntas, entao na pratica
nao se traduziu nenhuma: a pagina em portugues mostrava paragrafos em ingles.

O que este script faz
---------------------
1. Acrescenta ``<prefixo>.referenceNote`` e ``<prefixo>.expressionNote`` aos tres
   blocos do dicionario.
2. Nos paineis, corta a prosa da citacao: a citacao continua literal no prop
   ``reference``, a prosa passa a ``referenceNote={t(...)}``.
3. Tira o ingles que estava dentro da notacao matematica (``sum(Ni Mi)`` ->
   ``Σ(Ni Mi)``, ``(elution volume)`` -> ``Ve``), porque ``sum`` e ``elution``
   sao palavras inglesas dentro de uma formula.

Idempotente: rodar de novo nao altera nada.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DICIONARIO = RAIZ / "src" / "i18n" / "I18nContext.jsx"
COMPONENTES = RAIZ / "src" / "components"

# ---------------------------------------------------------------------------
# Prosa das referencias: (prefixo) -> {idioma: texto}
# Só os blocos com prosa; referências que são citação pura ficam fora.
# ---------------------------------------------------------------------------
REF_NOTES: dict[str, dict[str, str]] = {
    "mech.f.young": {
        "en": "Both require the modulus from the initial linear region, and neither permits a modulus quoted without the strain range it was fitted over.",
        "pt": "Ambos exigem o módulo da região linear inicial, e nenhum dos dois permite citar um módulo sem o intervalo de deformação em que foi ajustado.",
        "es": "Ambos exigen el módulo de la región lineal inicial, y ninguno de los dos permite citar un módulo sin el rango de deformación en el que se ajustó.",
    },
    "mech.f.fit": {
        "en": "The standard fits the slope over a defined strain window (typically 0.05 % to 0.25 %) rather than the whole curve, because the toe region at the start of the test is seating compliance, not material stiffness.",
        "pt": "A norma ajusta a inclinação sobre uma janela de deformação definida (tipicamente 0,05 % a 0,25 %) e não sobre a curva inteira, porque a região de acomodação no início do ensaio é folga de fixação, não rigidez do material.",
        "es": "La norma ajusta la pendiente sobre una ventana de deformación definida (típicamente 0,05 % a 0,25 %) y no sobre la curva completa, porque la región de acomodo al inicio del ensayo es holgura de fijación, no rigidez del material.",
    },
    "mech.f.sigma": {
        "en": "The original cross-section is used throughout; engineering stress, not true stress.",
        "pt": "A seção original é usada do início ao fim; tensão de engenharia, não tensão real.",
        "es": "Se usa la sección original de principio a fin; tensión de ingeniería, no tensión real.",
    },
    "mech.f.toughness": {
        "en": "The area is integrated over the strain range supplied, so a truncated curve underestimates toughness.",
        "pt": "A área é integrada sobre o intervalo de deformação fornecido, então uma curva truncada subestima a tenacidade.",
        "es": "El área se integra sobre el rango de deformación suministrado, así que una curva truncada subestima la tenacidad.",
    },
    "mol.f.pdi": {
        "en": "IUPAC recommends the term dispersity and the symbol D. A value below 1 is not a narrow distribution but an error in the data or the calculation.",
        "pt": "A IUPAC recomenda o termo dispersidade e o símbolo D. Um valor abaixo de 1 não é uma distribuição estreita, mas um erro nos dados ou no cálculo.",
        "es": "La IUPAC recomienda el término dispersidad y el símbolo D. Un valor por debajo de 1 no es una distribución estrecha, sino un error en los datos o en el cálculo.",
    },
    "mol.f.mz": {
        "en": "The z-average is weighted towards the heaviest chains, so it responds to a high-mass tail that Mw barely registers.",
        "pt": "A média z é ponderada pelas cadeias mais pesadas, então responde a uma cauda de massa alta que o Mw quase não registra.",
        "es": "El promedio z está ponderado hacia las cadenas más pesadas, así que responde a una cola de masa alta que el Mw apenas registra.",
    },
    "mol.f.mh": {
        "en": "Mark-Houwink-Sakurada relation; K and a are tabulated per polymer-solvent-temperature combination in the Polymer Handbook. They are not universal constants.",
        "pt": "Relação de Mark-Houwink-Sakurada; K e a são tabelados por combinação polímero-solvente-temperatura no Polymer Handbook. Não são constantes universais.",
        "es": "Relación de Mark-Houwink-Sakurada; K y a están tabulados por combinación polímero-disolvente-temperatura en el Polymer Handbook. No son constantes universales.",
    },
    "mol.f.gpc": {
        "en": "Conventional GPC calibration assumes the sample and the standards have the same hydrodynamic volume at a given elution volume. Reporting the result as absolute molar mass without a light-scattering or viscometry detector overstates what the measurement supports.",
        "pt": "A calibração convencional de GPC presume que a amostra e os padrões têm o mesmo volume hidrodinâmico num dado volume de eluição. Reportar o resultado como massa molar absoluta sem detector de espalhamento de luz ou viscosimetria superestima o que a medição sustenta.",
        "es": "La calibración convencional de GPC supone que la muestra y los estándares tienen el mismo volumen hidrodinámico en un volumen de elución dado. Informar el resultado como masa molar absoluta sin detector de dispersión de luz o viscosimetría exagera lo que la medición sostiene.",
    },
    "mol.f.log": {
        "en": "Schulz-Zimm and log-normal distributions are the usual models for a SEC trace; the log-normal is used here because its Mw/Mn follows directly from sigma.",
        "pt": "As distribuições de Schulz-Zimm e log-normal são os modelos usuais para um traço de SEC; a log-normal é usada aqui porque o seu Mw/Mn sai diretamente de sigma.",
        "es": "Las distribuciones de Schulz-Zimm y log-normal son los modelos habituales para una traza de SEC; aquí se usa la log-normal porque su Mw/Mn se deduce directamente de sigma.",
    },
    "rheo.f.gel": {
        "en": "The rigorous criterion is a power law in both moduli; crossing of the two is a practical approximation.",
        "pt": "O critério rigoroso é uma lei de potência nos dois módulos; o cruzamento dos dois é uma aproximação prática.",
        "es": "El criterio riguroso es una ley de potencia en ambos módulos; el cruce de los dos es una aproximación práctica.",
    },
    "rheo.f.cross": {
        "en": "The cross-over of the moduli is a practical marker of the terminal-to-plateau transition for a linear polymer; it shifts with frequency, so the value is only comparable between measurements made at the same angular frequency.",
        "pt": "O cruzamento dos módulos é um marcador prático da transição terminal-platô num polímero linear; ele desloca com a frequência, então o valor só é comparável entre medições feitas na mesma frequência angular.",
        "es": "El cruce de los módulos es un marcador práctico de la transición terminal-meseta en un polímero lineal; se desplaza con la frecuencia, así que el valor solo es comparable entre mediciones hechas a la misma frecuencia angular.",
    },
    "structure.f.scherrer": {
        "en": "Instrumental broadening is subtracted in quadrature before β is used.",
        "pt": "O alargamento instrumental é subtraído em quadratura antes de usar β.",
        "es": "El ensanchamiento instrumental se resta en cuadratura antes de usar β.",
    },
    "structure.f.fwhm": {
        "en": "The FWHM is the β that the Scherrer equation expects, and it must be corrected for instrumental broadening (β² = β_obs² − β_inst² for a Gaussian profile) before use. Without that correction the crystallite size is underestimated, and on a well-crystallised sample the instrumental contribution can be most of the observed width.",
        "pt": "A FWHM é o β que a equação de Scherrer espera, e precisa ser corrigida do alargamento instrumental (β² = β_obs² − β_inst² para um perfil gaussiano) antes do uso. Sem essa correção o tamanho do cristalito é subestimado, e numa amostra bem cristalizada a contribuição instrumental pode ser a maior parte da largura observada.",
        "es": "La FWHM es el β que espera la ecuación de Scherrer, y debe corregirse del ensanchamiento instrumental (β² = β_obs² − β_inst² para un perfil gaussiano) antes de usarla. Sin esa corrección el tamaño del cristalito se subestima, y en una muestra bien cristalizada la contribución instrumental puede ser la mayor parte del ancho observado.",
    },
    "structure.f.xc": {
        "en": "Relative index only; it is not a mass fraction and is comparable only between patterns measured identically.",
        "pt": "Apenas um índice relativo; não é fração mássica e só é comparável entre padrões medidos de forma idêntica.",
        "es": "Solo un índice relativo; no es una fracción másica y solo es comparable entre patrones medidos de forma idéntica.",
    },
    "thermal.f.dtg": {
        "en": "The DTG is the first derivative of the mass loss curve; its maximum is the temperature of greatest decomposition rate.",
        "pt": "A DTG é a primeira derivada da curva de perda de massa; o seu máximo é a temperatura de maior velocidade de decomposição.",
        "es": "La DTG es la primera derivada de la curva de pérdida de masa; su máximo es la temperatura de mayor velocidad de descomposición.",
    },
    "thermal.f.td": {
        "en": "Defines the onset temperature by the mass-loss criterion and the extrapolated tangent.",
        "pt": "Define a temperatura de onset pelo critério de perda de massa e pela tangente extrapolada.",
        "es": "Define la temperatura de onset por el criterio de pérdida de masa y la tangente extrapolada.",
    },
    "thermal.f.res": {
        "en": "The residue includes any inorganic filler, ash or char, so it is an upper bound on the filler content, not a measurement of it.",
        "pt": "O resíduo inclui qualquer carga inorgânica, cinza ou resíduo carbonoso, então é um limite superior do teor de carga, não uma medição dele.",
        "es": "El residuo incluye cualquier carga inorgánica, ceniza o residuo carbonoso, así que es un límite superior del contenido de carga, no una medición de este.",
    },
    "thermal.f.smooth": {
        "en": "A moving-average filter is the usual pre-treatment for a DTG curve (ISO 11358-1:2022, which permits smoothing provided its parameters are reported). It is a low-pass filter, so it suppresses sharp features along with the noise: widening w flattens a narrow decomposition step, and the smoothed curve must never be the one the residue is read from.",
        "pt": "Um filtro de média móvel é o pré-tratamento usual para uma curva de DTG (ISO 11358-1:2022, que permite suavizar desde que os parâmetros sejam reportados). É um filtro passa-baixa, então suprime traços agudos junto com o ruído: aumentar w achata um degrau estreito de decomposição, e a curva suavizada nunca deve ser aquela de onde se lê o resíduo.",
        "es": "Un filtro de media móvil es el pretratamiento habitual para una curva de DTG (ISO 11358-1:2022, que permite suavizar siempre que se informen sus parámetros). Es un filtro paso bajo, así que suprime los rasgos agudos junto con el ruido: aumentar w aplana un escalón estrecho de descomposición, y la curva suavizada nunca debe ser aquella de la que se lee el residuo.",
    },
    "thermal.f.uniform": {
        "en": "ISO 11358-1:2022 requires the rate of mass loss to be reported against temperature on a defined basis. A finite difference taken on the raw, unevenly spaced axis is dominated by the shortest intervals — one noisy pair a hundredth of a degree apart yields a gradient of tens of percent per degree — so the trace is resampled onto a uniform grid first. The choice of grid step is then reported, because it sets the resolution of every DTG peak that follows.",
        "pt": "A ISO 11358-1:2022 exige que a velocidade de perda de massa seja reportada em função da temperatura numa base definida. Uma diferença finita tomada no eixo bruto, de espaçamento irregular, é dominada pelos intervalos mais curtos — um par ruidoso separado por um centésimo de grau produz um gradiente de dezenas de por cento por grau — então o traço é reamostrado numa grade uniforme antes. A escolha do passo da grade é então reportada, porque define a resolução de todos os picos de DTG que vêm depois.",
        "es": "La ISO 11358-1:2022 exige que la velocidad de pérdida de masa se informe frente a la temperatura sobre una base definida. Una diferencia finita tomada sobre el eje bruto, de espaciado irregular, está dominada por los intervalos más cortos — un par ruidoso separado por una centésima de grado produce un gradiente de decenas de por ciento por grado — así que la traza se remuestrea primero en una malla uniforme. La elección del paso de malla se informa después, porque fija la resolución de todos los picos de DTG que siguen.",
    },
    "thermal.f.dscpeak": {
        "en": "The peak area is bounded by a baseline drawn between the flanks of the transition.",
        "pt": "A área do pico é limitada por uma linha de base traçada entre os flancos da transição.",
        "es": "El área del pico está delimitada por una línea base trazada entre los flancos de la transición.",
    },
    "thermal.f.xc": {
        "en": "Xc from DSC is a mass fraction, and is only as good as ΔHm°.",
        "pt": "A Xc por DSC é uma fração mássica, e só é tão boa quanto o ΔHm°.",
        "es": "La Xc por DSC es una fracción másica, y solo es tan buena como el ΔHm°.",
    },
}

# ---------------------------------------------------------------------------
# Prosa que estava dentro da notacao matematica: (prefixo) -> {idioma: texto}
# ---------------------------------------------------------------------------
EXPR_NOTES: dict[str, dict[str, str]] = {
    "mech.f.young": {
        "en": "(slope of the initial linear region)",
        "pt": "(inclinação da região linear inicial)",
        "es": "(pendiente de la región lineal inicial)",
    },
    "mech.f.fit": {
        "en": "(least squares)",
        "pt": "(mínimos quadrados)",
        "es": "(mínimos cuadrados)",
    },
    "mech.f.toughness": {
        "en": "(area under the stress-strain curve)",
        "pt": "(área sob a curva tensão-deformação)",
        "es": "(área bajo la curva tensión-deformación)",
    },
    "mol.f.pdi": {
        "en": "(dispersity, formerly polydispersity index)",
        "pt": "(dispersidade, antigamente índice de polidispersão)",
        "es": "(dispersidad, antiguamente índice de polidispersidad)",
    },
    "mol.f.gpc": {
        "en": "(calibrated against narrow standards)",
        "pt": "(calibrada contra padrões estreitos)",
        "es": "(calibrada contra estándares estrechos)",
    },
    "rheo.f.gel": {
        "en": "(gel point: the ω where the two moduli agree within tolerance, with G' > G'')",
        "pt": "(ponto de gel: o ω em que os dois módulos concordam dentro da tolerância, com G' > G'')",
        "es": "(punto de gel: el ω donde los dos módulos concuerdan dentro de la tolerancia, con G' > G'')",
    },
    "rheo.f.cross": {
        "en": "(cross-over)",
        "pt": "(cruzamento)",
        "es": "(cruce)",
    },
    "structure.f.fwhm": {
        "en": "(half-width at half maximum, in radians)",
        "pt": "(largura a meia altura, em radianos)",
        "es": "(anchura a media altura, en radianes)",
    },
    "structure.f.xc": {
        "en": "(A_c: crystalline area; A_t: total area)",
        "pt": "(A_c: área cristalina; A_t: área total)",
        "es": "(A_c: área cristalina; A_t: área total)",
    },
    "thermal.f.td": {
        "en": "(linear interpolation)",
        "pt": "(interpolação linear)",
        "es": "(interpolación lineal)",
    },
    "thermal.f.smooth": {
        "en": "(over a window of w points, edge-padded)",
        "pt": "(sobre uma janela de w pontos, com preenchimento nas bordas)",
        "es": "(sobre una ventana de w puntos, con relleno en los bordes)",
    },
    "thermal.f.uniform": {
        "en": "(DTG computed on a uniform 1 °C grid after interpolation)",
        "pt": "(DTG calculada numa grade uniforme de 1 °C após interpolação)",
        "es": "(DTG calculada en una malla uniforme de 1 °C tras la interpolación)",
    },
}

# ---------------------------------------------------------------------------
# Edicoes nos paineis: (arquivo, trecho antigo, trecho novo)
# Citação pura: o prop nao muda. Citação + prosa: corta a prosa.
# ---------------------------------------------------------------------------
EDICOES_REF: list[tuple[str, str, str]] = [
    # --- MechanicalPanel -------------------------------------------------
    (
        "MechanicalPanel.jsx",
        'reference="ASTM D638-22, Standard Test Method for Tensile Properties of Plastics; ISO 527-1:2019. Both require the modulus from the initial linear region, and neither permits a modulus quoted without the strain range it was fitted over."',
        'reference="ASTM D638-22, Standard Test Method for Tensile Properties of Plastics; ISO 527-1:2019."\n          referenceNote={t(\'mech.f.young.referenceNote\')}',
    ),
    (
        "MechanicalPanel.jsx",
        'reference="ISO 527-1:2019, determination of tensile modulus. The standard fits the slope over a defined strain window (typically 0.05 % to 0.25 %) rather than the whole curve, because the toe region at the start of the test is seating compliance, not material stiffness."',
        'reference="ISO 527-1:2019, determination of tensile modulus."\n          referenceNote={t(\'mech.f.fit.referenceNote\')}',
    ),
    (
        "MechanicalPanel.jsx",
        'reference="ISO 527-1:2019 (definitions of stress and strain). The original cross-section is used throughout; engineering stress, not true stress."',
        'reference="ISO 527-1:2019 (definitions of stress and strain)."\n          referenceNote={t(\'mech.f.sigma.referenceNote\')}',
    ),
    (
        "MechanicalPanel.jsx",
        'reference="ASTM D638-22, Annex on energy at break. The area is integrated over the strain range supplied, so a truncated curve underestimates toughness."',
        'reference="ASTM D638-22, Annex on energy at break."\n          referenceNote={t(\'mech.f.toughness.referenceNote\')}',
    ),
    # --- MolecularPanel --------------------------------------------------
    # IUPAC/ASTM D5296: citação pura, nao muda.
    (
        "MolecularPanel.jsx",
        'reference="IUPAC recommends the term dispersity and the symbol D. A value below 1 is not a narrow distribution but an error in the data or the calculation."',
        "referenceNote={t('mol.f.pdi.referenceNote')}",
    ),
    (
        "MolecularPanel.jsx",
        'reference="The z-average is weighted towards the heaviest chains, so it responds to a high-mass tail that Mw barely registers."',
        "referenceNote={t('mol.f.mz.referenceNote')}",
    ),
    (
        "MolecularPanel.jsx",
        'reference="Mark-Houwink-Sakurada relation; K and a are tabulated per polymer-solvent-temperature combination in the Polymer Handbook. They are not universal constants."',
        "referenceNote={t('mol.f.mh.referenceNote')}",
    ),
    (
        "MolecularPanel.jsx",
        'reference="Conventional GPC calibration assumes the sample and the standards have the same hydrodynamic volume at a given elution volume. Reporting the result as absolute molar mass without a light-scattering or viscometry detector overstates what the measurement supports."',
        "referenceNote={t('mol.f.gpc.referenceNote')}",
    ),
    (
        "MolecularPanel.jsx",
        'reference="Schulz-Zimm and log-normal distributions are the usual models for a SEC trace; the log-normal is used here because its Mw/Mn follows directly from sigma."',
        "referenceNote={t('mol.f.log.referenceNote')}",
    ),
    # --- RheologyPanel ---------------------------------------------------
    # ISO 6721-10 e ASTM D4440: citações puras, nao mudam.
    (
        "RheologyPanel.jsx",
        'reference="Winter & Chambon, Analysis of linear viscoelasticity of a crosslinking polymer at the gel point, Journal of Rheology 30 (1986) 367-382. The rigorous criterion is a power law in both moduli; crossing of the two is a practical approximation."',
        'reference="Winter & Chambon, Analysis of linear viscoelasticity of a crosslinking polymer at the gel point, Journal of Rheology 30 (1986) 367-382."\n          referenceNote={t(\'rheo.f.gel.referenceNote\')}',
    ),
    (
        "RheologyPanel.jsx",
        'reference="ASTM D4440-15. The cross-over of the moduli is a practical marker of the terminal-to-plateau transition for a linear polymer; it shifts with frequency, so the value is only comparable between measurements made at the same angular frequency."',
        'reference="ASTM D4440-15."\n          referenceNote={t(\'rheo.f.cross.referenceNote\')}',
    ),
    # --- StructurePanel --------------------------------------------------
    # Bragg & Bragg: citação pura, nao muda.
    (
        "StructurePanel.jsx",
        "reference=\"Scherrer, 'Bestimmung der Größe und der inneren Struktur von Kolloidteilchen mittels Röntgenstrahlen', Göttinger Nachrichten 2 (1918) 98–100. Instrumental broadening is subtracted in quadrature before β is used.\"",
        "reference=\"Scherrer, 'Bestimmung der Größe und der inneren Struktur von Kolloidteilchen mittels Röntgenstrahlen', Göttinger Nachrichten 2 (1918) 98–100.\"\n          referenceNote={t('structure.f.scherrer.referenceNote')}",
    ),
    (
        "StructurePanel.jsx",
        'reference="The FWHM is the β that the Scherrer equation expects, and it must be corrected for instrumental broadening (β² = β_obs² − β_inst² for a Gaussian profile) before use. Without that correction the crystallite size is underestimated, and on a well-crystallised sample the instrumental contribution can be most of the observed width."',
        "referenceNote={t('structure.f.fwhm.referenceNote')}",
    ),
    (
        "StructurePanel.jsx",
        "reference=\"Segal et al., 'An empirical method for estimating the degree of crystallinity of native cellulose using the X-ray diffractometer', Textile Research Journal 29 (1959) 786–794. Relative index only; it is not a mass fraction and is comparable only between patterns measured identically.\"",
        "reference=\"Segal et al., 'An empirical method for estimating the degree of crystallinity of native cellulose using the X-ray diffractometer', Textile Research Journal 29 (1959) 786–794.\"\n          referenceNote={t('structure.f.xc.referenceNote')}",
    ),
    # --- ThermalPanel ----------------------------------------------------
    (
        "ThermalPanel.jsx",
        'reference="ASTM E1131-20, Standard Test Method for Compositional Analysis by Thermogravimetry. The DTG is the first derivative of the mass loss curve; its maximum is the temperature of greatest decomposition rate."',
        'reference="ASTM E1131-20, Standard Test Method for Compositional Analysis by Thermogravimetry."\n          referenceNote={t(\'thermal.f.dtg.referenceNote\')}',
    ),
    (
        "ThermalPanel.jsx",
        'reference="ISO 11358-1:2022, Plastics — Thermogravimetry (TG) of polymers — Part 1: General principles. Defines the onset temperature by the mass-loss criterion and the extrapolated tangent."',
        'reference="ISO 11358-1:2022, Plastics — Thermogravimetry (TG) of polymers — Part 1: General principles."\n          referenceNote={t(\'thermal.f.td.referenceNote\')}',
    ),
    (
        "ThermalPanel.jsx",
        'reference="ISO 11358-1:2022 (residue determination). The residue includes any inorganic filler, ash or char, so it is an upper bound on the filler content, not a measurement of it."',
        'reference="ISO 11358-1:2022 (residue determination)."\n          referenceNote={t(\'thermal.f.res.referenceNote\')}',
    ),
    (
        "ThermalPanel.jsx",
        'reference="A moving-average filter is the usual pre-treatment for a DTG curve (ISO 11358-1:2022, which permits smoothing provided its parameters are reported). It is a low-pass filter, so it suppresses sharp features along with the noise: widening w flattens a narrow decomposition step, and the smoothed curve must never be the one the residue is read from."',
        "referenceNote={t('thermal.f.smooth.referenceNote')}",
    ),
    (
        "ThermalPanel.jsx",
        'reference="ISO 11358-1:2022 requires the rate of mass loss to be reported against temperature on a defined basis. A finite difference taken on the raw, unevenly spaced axis is dominated by the shortest intervals — one noisy pair a hundredth of a degree apart yields a gradient of tens of percent per degree — so the trace is resampled onto a uniform grid first. The choice of grid step is then reported, because it sets the resolution of every DTG peak that follows."',
        "referenceNote={t('thermal.f.uniform.referenceNote')}",
    ),
    (
        "ThermalPanel.jsx",
        'reference="ASTM E793-06(2018), Standard Test Method for Enthalpies of Fusion and Crystallization by DSC. The peak area is bounded by a baseline drawn between the flanks of the transition."',
        'reference="ASTM E793-06(2018), Standard Test Method for Enthalpies of Fusion and Crystallization by DSC."\n          referenceNote={t(\'thermal.f.dscpeak.referenceNote\')}',
    ),
    (
        "ThermalPanel.jsx",
        "reference=\"Kong & Hay, 'The measurement of the crystallinity of polymers by DSC', Polymer 43 (2002) 3873–3878. Xc from DSC is a mass fraction, and is only as good as ΔHm°.\"",
        "reference=\"Kong & Hay, 'The measurement of the crystallinity of polymers by DSC', Polymer 43 (2002) 3873–3878.\"\n          referenceNote={t('thermal.f.xc.referenceNote')}",
    ),
]

# ---------------------------------------------------------------------------
# Edicoes nas notacoes: tira o ingles de dentro da matematica.
# ---------------------------------------------------------------------------
EDICOES_EXPR: list[tuple[str, str, str]] = [
    (
        "MechanicalPanel.jsx",
        'expression="E = Δσ / Δε   (slope of the initial linear region)"',
        'expression="E = Δσ / Δε"\n          expressionNote={t(\'mech.f.young.expressionNote\')}',
    ),
    (
        "MechanicalPanel.jsx",
        'expression="E = Σ(εi − ε̄)(σi − σ̄) / Σ(εi − ε̄)²   (least squares)"',
        'expression="E = Σ(εi − ε̄)(σi − σ̄) / Σ(εi − ε̄)²"\n          expressionNote={t(\'mech.f.fit.expressionNote\')}',
    ),
    (
        "MechanicalPanel.jsx",
        'expression="U = ∫ σ dε   (area under the stress-strain curve)"',
        'expression="U = ∫ σ dε"\n          expressionNote={t(\'mech.f.toughness.expressionNote\')}',
    ),
    (
        "MolecularPanel.jsx",
        'expression="Mn = sum(Ni Mi) / sum(Ni)      Mw = sum(Ni Mi^2) / sum(Ni Mi)"',
        'expression="Mn = Σ(Ni Mi) / Σ(Ni)      Mw = Σ(Ni Mi²) / Σ(Ni Mi)"',
    ),
    (
        "MolecularPanel.jsx",
        'expression="D = Mw / Mn   (dispersity, formerly polydispersity index)"',
        'expression="D = Mw / Mn"\n          expressionNote={t(\'mol.f.pdi.expressionNote\')}',
    ),
    (
        "MolecularPanel.jsx",
        'expression="Mz = sum(Ni Mi^3) / sum(Ni Mi^2)"',
        'expression="Mz = Σ(Ni Mi³) / Σ(Ni Mi²)"',
    ),
    (
        "MolecularPanel.jsx",
        'expression="log M = f(elution volume)   calibrated against narrow standards"',
        'expression="log M = f(Ve)"\n          expressionNote={t(\'mol.f.gpc.expressionNote\')}',
    ),
    (
        "RheologyPanel.jsx",
        "expression=\"gel point: the w where |G' - G''| / G' <= tolerance,  with G' > G''\"",
        "expression=\"|G' − G''| / G' ≤ tol,  G' > G''\"\n          expressionNote={t('rheo.f.gel.expressionNote')}",
    ),
    (
        "RheologyPanel.jsx",
        "expression=\"cross-over: G' = G''  ->  tan d = 1\"",
        "expression=\"G' = G'',  tan δ = 1\"\n          expressionNote={t('rheo.f.cross.expressionNote')}",
    ),
    (
        "StructurePanel.jsx",
        'expression="β = 2·|2θ(half) − 2θ(peak)|   (half-width at half maximum, in radians)"',
        'expression="β = 2·|2θ(meia) − 2θ(pico)|"\n          expressionNote={t(\'structure.f.fwhm.expressionNote\')}',
    ),
    (
        "StructurePanel.jsx",
        'expression="CI (%) = 100 · (A_crystalline) / (A_total)"',
        'expression="CI (%) = 100 · A_c / A_t"\n          expressionNote={t(\'structure.f.xc.expressionNote\')}',
    ),
    (
        "ThermalPanel.jsx",
        'expression="Td(x%) : the T where m(T) = 100 − x   (linear interpolation)"',
        'expression="Td(x%): m(T) = 100 − x"\n          expressionNote={t(\'thermal.f.td.expressionNote\')}',
    ),
    (
        "ThermalPanel.jsx",
        'expression="m_smooth(T) = (1/w) Σ m(T_i)   over a window of w points, edge-padded"',
        'expression="m_smooth(T) = (1/w) Σ m(T_i)"\n          expressionNote={t(\'thermal.f.smooth.expressionNote\')}',
    ),
    (
        "ThermalPanel.jsx",
        'expression="DTG computed on a uniform 1 °C grid after interpolation"',
        'expression="ΔT = 1 °C"\n          expressionNote={t(\'thermal.f.uniform.expressionNote\')}',
    ),
]

IDIOMAS = ("en", "pt", "es")

#: Valor de `common.ref`, igual nos tres idiomas (e uma abreviacao bibliografica).
COMMON_REF = {"en": "Ref.", "pt": "Ref.", "es": "Ref."}


def _escapar(valor: str) -> str:
    return valor.replace("\\", "\\\\").replace("'", "\\'")


def inserir_chave(
    texto: str, ancora: str, prefixo: str, notas: dict[str, str], sufixo: str
) -> tuple[str, bool]:
    """Insere ``'<prefixo>.<sufixo>'`` nos tres blocos de idioma de uma vez.

    A mesma chave existe nos tres blocos, entao ha tres ancoras. Processa de
    tras para frente para que os indices anteriores continuem validos, e so
    escreve num bloco que ainda nao tenha a chave -- assim rodar duas vezes nao
    duplica.
    """
    linhas = texto.split("\n")
    alvo = re.compile(r"^\s*'" + re.escape(ancora) + r"\.note'\s*:")
    ancoras = [i for i, ln in enumerate(linhas) if alvo.match(ln)]
    if not ancoras:
        return texto, False

    # Cada ancora pertence a um bloco; a nota correta depende de qual bloco e.
    # Os blocos aparecem na ordem en, pt, es -- a mesma de IDIOMAS.
    if len(ancoras) != len(IDIOMAS):
        return texto, False

    for ordem_inversa, i in enumerate(reversed(ancoras)):
        idioma = IDIOMAS[len(ancoras) - 1 - ordem_inversa]
        indent = linhas[i][: len(linhas[i]) - len(linhas[i].lstrip())]
        ja_existe = (
            i + 1 < len(linhas) and f"'{prefixo}.{sufixo}'" in linhas[i + 1]
        )
        if ja_existe:
            continue
        linhas.insert(i + 1, f"{indent}'{prefixo}.{sufixo}': '{_escapar(notas[idioma])}',")
    return "\n".join(linhas), True


def main() -> int:
    problemas: list[str] = []

    # --- 1. dicionario ---------------------------------------------------
    texto = DICIONARIO.read_text(encoding="utf-8")
    if texto.count("'common.ref'") != len(IDIOMAS):
        # Fica junto das outras chaves de `common`, em TODOS os blocos: a
        # primeira versao parava no primeiro bloco e deixava en com uma chave a
        # mais que pt e es, o que o teste de paridade acusa como falha.
        #
        # E insere de tras para frente depois de COLETAR os indices: inserir
        # linhas enquanto se itera a mesma lista invalida os indices seguintes e
        # espalha copias pela chave errada. Foi exactamente o que aconteceu --
        # tres copias foram parar no bloco en, duas no pt, duas no es.
        linhas = [ln for ln in texto.split("\n") if not re.match(r"^\s*'common\.ref'\s*:", ln)]
        ancoras = [i for i, ln in enumerate(linhas) if re.match(r"^\s*'common\.results'\s*:", ln)]
        if len(ancoras) != len(IDIOMAS):
            problemas.append(f"esperava {len(IDIOMAS)} ancoras 'common.results', achei {len(ancoras)}")
        for n, i in enumerate(reversed(ancoras)):
            idioma = IDIOMAS[len(ancoras) - 1 - n]
            indent = linhas[i][: len(linhas[i]) - len(linhas[i].lstrip())]
            linhas.insert(i + 1, f"{indent}'common.ref': '{COMMON_REF[idioma]}',")
        texto = "\n".join(linhas)

    for prefixo, notas in REF_NOTES.items():
        if f"'{prefixo}.referenceNote'" in texto:
            continue
        texto, ok = inserir_chave(texto, prefixo, prefixo, notas, "referenceNote")
        if not ok:
            problemas.append(f"nao consegui inserir {prefixo}.referenceNote")

    for prefixo, notas in EXPR_NOTES.items():
        if f"'{prefixo}.expressionNote'" in texto:
            continue
        texto, ok = inserir_chave(texto, prefixo, prefixo, notas, "expressionNote")
        if not ok:
            problemas.append(f"nao consegui inserir {prefixo}.expressionNote")

    DICIONARIO.write_text(texto, encoding="utf-8")
    print("dicionario: chaves inseridas")

    # --- 2. paineis ------------------------------------------------------
    for arquivo, antigo, novo in EDICOES_EXPR + EDICOES_REF:
        caminho = COMPONENTES / arquivo
        src = caminho.read_text(encoding="utf-8")
        if novo.split("\n")[0] in src and antigo not in src:
            continue  # ja aplicado
        n = src.count(antigo)
        if n != 1:
            problemas.append(f"{arquivo}: {n} ocorrencia(s) de {antigo[:60]!r}")
            continue
        caminho.write_text(src.replace(antigo, novo), encoding="utf-8")

    if problemas:
        print("PROBLEMAS:")
        for p in problemas:
            print("  ", p)
        return 1
    print(f"paineis: {len(EDICOES_EXPR) + len(EDICOES_REF)} edicoes verificadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
