/**
 * Minimal i18n for the toolkit.
 *
 * Deliberately not i18next: the app has one page per module and a fixed
 * vocabulary, so a hand-rolled lookup keeps the bundle small and makes every
 * string greppable. Scientific terms that have one accepted form in the
 * literature (Mn, Mw, dispersity, Scherrer, Mark-Houwink) are NOT translated -
 * translating them would make the output harder to compare with a paper, not
 * easier.
 *
 * Adding a language: add one entry to MESSAGES with the same keys. A missing
 * key falls back to English and logs a warning in development, so a partial
 * translation degrades rather than crashing.
 */

import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

export const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'pt', label: 'Português' },
  { code: 'es', label: 'Español' },
];

const MESSAGES = {
  en: {
    'app.title': 'Polymer Analysis Toolkit',
    'app.subtitle': 'Open characterisation tools for polymer scientists',
    'app.tagline':
      'Every result states its method, its units and its assumptions. Nothing here is a black box.',
    'app.footer.developed': 'Developed by',
    'app.footer.repo': 'Source code',
    'app.footer.docs': 'API documentation',

    'nav.molecular': 'Molar mass',
    'nav.thermal': 'Thermal',
    'nav.mechanical': 'Mechanical',
    'nav.rheology': 'Rheology',
    'nav.structure': 'Structure',

    'common.calculate': 'Calculate',
    'common.calculating': 'Calculating…',
    'common.reset': 'Clear',
    'common.loading': 'Loading…',
    'common.results': 'Results',
    'common.error': 'Error',
    'common.optional': 'optional',
    'common.required': 'required',
    'common.upload': 'Upload a file',
    'common.chooseFile': 'Choose file',
    'common.noFile': 'No file selected',
    'common.exportJson': 'Export JSON',
    'common.importDecisions': 'How the file was read',
    'common.showDetails': 'Show details',
    'common.hideDetails': 'Hide details',
    'common.slices': 'slices',
    'common.apiUrl': 'API',
    'common.apiUnreachable': 'API unreachable',
    'common.apiOk': 'API online',
    'common.language': 'Language',

    'molecular.title': 'Molar mass distribution',
    'molecular.intro':
      'Calculate the molar-mass averages from a distribution, either by uploading an instrument export or by entering the values directly.',
    'molecular.uploadLabel': 'Instrument export (CSV or delimited text)',
    'molecular.uploadHint':
      'Any of these are accepted: mass/fraction in g/mol, percentages, raw detector intensity, a logM axis, comma or semicolon delimiters, decimal comma, header in English or Portuguese.',
    'molecular.preview': 'Inspect file',
    'molecular.previewHint':
      'Shows how the importer interpreted the file before anything is calculated.',
    'molecular.normalise': 'Normalise the fractions by their sum',
    'molecular.normaliseHint':
      'Use when the values are percentages or raw intensities rather than fractions that sum to one.',
    'molecular.markHouwink': 'Mark-Houwink exponent a',
    'molecular.markHouwinkHint':
      'Optional. Supplying a value also computes Mv, the viscosity-average molar mass. The exponent is specific to the polymer, solvent and temperature, and must come from a handbook or paper.',
    'molecular.manualEntry': 'Enter the distribution directly',
    'molecular.masses': 'Molar masses (g/mol)',
    'molecular.fractions': 'Weight fractions',
    'molecular.pairHint': 'One value per line, in matching order.',
    'molecular.Mn': 'Number average',
    'molecular.Mw': 'Weight average',
    'molecular.Mz': 'Z average',
    'molecular.Mz1': 'Z+1 average',
    'molecular.Mv': 'Viscosity average',
    'molecular.dispersity': 'Dispersity (Đ)',
    'molecular.dispersityNote':
      'Đ = Mw/Mn. Near 1.0 for a controlled polymerisation, above 1.5 for uncontrolled radical polymerisation.',
    'molecular.MnNote': 'Weighted by the number of chains.',
    'molecular.MwNote': 'Weighted by mass. The value a light-scattering measurement gives.',
    'molecular.MzNote': 'Sensitive to the high-mass tail.',
    'molecular.Mz1Note': 'Very sensitive to the high-mass tail.',
    'molecular.distribution': 'Weight distribution',
    'molecular.crossCheck': 'Cross-check against the file',
    'molecular.crossCheckNote':
      'The instrument reported its own averages. A large difference means the file was misread.',
    'molecular.fileMn': 'Mn in file',
    'molecular.fileMw': 'Mw in file',
    'molecular.calcMn': 'Mn calculated',
    'molecular.calcMw': 'Mw calculated',
    'molecular.reference': 'Reference case',
    'molecular.referenceNote':
      'A log-normal distribution is the shape a well-controlled radical polymerisation approaches. Its properties are known analytically, so it is a useful sanity check.',
    'molecular.referenceDispersity': 'Target dispersity',
    'molecular.generate': 'Generate',

    'thermal.title': 'Thermal analysis',
    'thermal.intro':
      'TGA gives degradation temperatures and residue; DSC gives the glass transition, melting and crystallinity.',
    'thermal.tga': 'TGA',
    'thermal.dsc': 'DSC',
    'thermal.temperature': 'Temperature (°C)',
    'thermal.massPct': 'Mass remaining (%)',
    'thermal.heatFlow': 'Heat flow (W/g)',
    'thermal.heatingRate': 'Heating rate (K/min)',
    'thermal.heatingRateHint':
      'Required for enthalpies: the signal is integrated over temperature, so the scan rate is needed to get J/g.',
    'thermal.refEnthalpy': 'Reference melting enthalpy (J/g)',
    'thermal.refEnthalpyHint':
      'The melting enthalpy of the same polymer in a fully crystalline state. Required for a crystallinity value, and it must be the right polymorph.',
    'thermal.Td5': 'Td at 5 % loss',
    'thermal.Td10': 'Td at 10 % loss',
    'thermal.TmaxRate': 'Peak decomposition rate',
    'thermal.TmaxRateNote':
      'The step that loses mass fastest. With several steps this is not necessarily the first one.',
    'thermal.residue': 'Residue',
    'thermal.steps': 'Decomposition steps',
    'thermal.Tg': 'Glass transition',
    'thermal.TgNote':
      'ASTM D3418 midpoint. A single heating scan carries the sample history; a heat-cool-heat cycle read on the second heating is more reliable.',
    'thermal.Tm': 'Melting point',
    'thermal.deltaHm': 'Melting enthalpy',
    'thermal.deltaCp': 'Heat capacity step',
    'thermal.crystallinity': 'Crystallinity',
    'thermal.crystallinityNote':
      'Uses the reference enthalpy supplied above. A value above 100 % means the reference does not match the sample.',
    'thermal.trace': 'Trace',
    'thermal.dtg': 'Derivative',

    'mechanical.title': 'Tensile properties',
    'mechanical.intro':
      'Standard descriptors from an engineering stress-strain curve, per ISO 527-1.',
    'mechanical.strain': 'Strain (%)',
    'mechanical.stress': 'Stress (MPa)',
    'mechanical.modulus': "Young's modulus",
    'mechanical.modulusNote':
      'Slope of the initial linear region. The strain window used is reported so the value can be checked.',
    'mechanical.window': 'Strain window used',
    'mechanical.stressMax': 'Tensile strength',
    'mechanical.strainMax': 'Strain at maximum',
    'mechanical.stressBreak': 'Stress at break',
    'mechanical.strainBreak': 'Strain at break',
    'mechanical.stressYield': 'Yield stress',
    'mechanical.strainYield': 'Yield strain',
    'mechanical.toughness': 'Toughness',
    'mechanical.toughnessNote': 'Area under the curve. The least precise number here.',
    'mechanical.yielded': 'Shows a yield point',
    'mechanical.brittle': 'Breaks at maximum stress',
    'mechanical.curve': 'Stress-strain curve',

    'rheology.title': 'Oscillatory shear',
    'rheology.intro': 'Descriptors of a small-amplitude frequency sweep.',
    'rheology.omega': 'Angular frequency (rad/s)',
    'rheology.gPrime': "Storage modulus G' (Pa)",
    'rheology.gDoublePrime': "Loss modulus G'' (Pa)",
    'rheology.crossover': 'Crossover',
    'rheology.crossoverNote': "Frequency where G' = G''. Its inverse is the terminal relaxation time.",
    'rheology.plateau': 'Plateau modulus',
    'rheology.plateauNote':
      'Estimated from the minimum of tan(δ). Slightly biased low, because the full relaxation spectrum is not measured.',
    'rheology.relaxation': 'Relaxation time',
    'rheology.slopes': 'Terminal slopes',
    'rheology.slopesNote':
      "For a narrow-distribution linear melt the theory gives 2 for G' and 1 for G''. Values much lower mean the sweep did not reach the terminal regime, so the plateau modulus and zero-shear viscosity are not meaningful.",
    'rheology.zeroShear': 'Zero-shear viscosity',
    'rheology.gel': 'Gel point (Winter-Chambon)',
    'rheology.gelYes': 'tan(δ) is frequency independent — consistent with a critical gel',
    'rheology.gelNo': 'tan(δ) varies with frequency — no gel point in this window',
    'rheology.solidLike': "G' exceeds G'' at the lowest frequency",
    'rheology.liquidLike': "G'' exceeds G' at the lowest frequency",
    'rheology.masterCurve': "G' and G'' vs frequency",

    'structure.title': 'Structure',
    'structure.intro':
      'X-ray diffraction for crystallinity and crystallite size; infrared for functional groups.',
    'structure.xrd': 'XRD',
    'structure.ftir': 'FTIR',
    'structure.twoTheta': '2θ (degrees)',
    'structure.intensity': 'Intensity',
    'structure.wavelength': 'Wavelength (Å)',
    'structure.instrumentFwhm': 'Instrumental broadening (FWHM, °)',
    'structure.instrumentFwhmHint':
      'Measure it on a standard such as LaB6 or silicon. Leaving it at zero makes every crystallite size an underestimate.',
    'structure.peaks': 'Peaks',
    'structure.peak': '2θ',
    'structure.dSpacing': 'd (Å)',
    'structure.size': 'Size (nm)',
    'structure.fwhm': 'FWHM (°)',
    'structure.crystallinity': 'Crystallinity index',
    'structure.crystallinityNote':
      'NOT the absolute degree of crystallinity. Comparable only between samples measured with the same range, baseline and slits.',
    'structure.wavenumber': 'Wavenumber (cm⁻¹)',
    'structure.absorbance': 'Absorbance',
    'structure.bands': 'Detected bands',
    'structure.band': 'Band',
    'structure.assignments': 'Candidate assignments',
    'structure.pattern': 'Pattern',
    'structure.spectrum': 'Spectrum',
    'structure.ftirWarning':
      'This is a functional-group lookup, not an identification. Many polymers share the same groups, and additives and moisture contribute their own bands. Confirm against a reference spectrum measured on the same instrument.',

    'error.needData': 'Provide a file or enter the values directly.',
    'error.needFile': 'Choose a file first.',
    'error.tooFewPoints': 'At least {n} points are needed.',
    'error.mismatched': 'The two columns must have the same number of values.',
    'error.badNumbers': 'Some values could not be read as numbers.',
  },

  pt: {
    'app.title': 'Polymer Analysis Toolkit',
    'app.subtitle': 'Ferramentas abertas de caracterização para cientistas de polímeros',
    'app.tagline':
      'Todo resultado informa o método, as unidades e as hipóteses. Nada aqui é caixa-preta.',
    'app.footer.developed': 'Desenvolvido por',
    'app.footer.repo': 'Código-fonte',
    'app.footer.docs': 'Documentação da API',

    'nav.molecular': 'Massa molar',
    'nav.thermal': 'Térmica',
    'nav.mechanical': 'Mecânica',
    'nav.rheology': 'Reologia',
    'nav.structure': 'Estrutura',

    'common.calculate': 'Calcular',
    'common.calculating': 'Calculando…',
    'common.reset': 'Limpar',
    'common.loading': 'Carregando…',
    'common.results': 'Resultados',
    'common.error': 'Erro',
    'common.optional': 'opcional',
    'common.required': 'obrigatório',
    'common.upload': 'Enviar arquivo',
    'common.chooseFile': 'Escolher arquivo',
    'common.noFile': 'Nenhum arquivo selecionado',
    'common.exportJson': 'Exportar JSON',
    'common.importDecisions': 'Como o arquivo foi lido',
    'common.showDetails': 'Ver detalhes',
    'common.hideDetails': 'Ocultar detalhes',
    'common.slices': 'fatias',
    'common.apiUrl': 'API',
    'common.apiUnreachable': 'API inacessível',
    'common.apiOk': 'API no ar',
    'common.language': 'Idioma',

    'molecular.title': 'Distribuição de massa molar',
    'molecular.intro':
      'Calcule as médias de massa molar a partir de uma distribuição, enviando a exportação do equipamento ou digitando os valores.',
    'molecular.uploadLabel': 'Exportação do equipamento (CSV ou texto delimitado)',
    'molecular.uploadHint':
      'São aceitos: massa/fração em g/mol, porcentagens, intensidade bruta do detector, eixo logM, separador por vírgula ou ponto e vírgula, vírgula decimal, cabeçalho em português ou inglês.',
    'molecular.preview': 'Inspecionar arquivo',
    'molecular.previewHint':
      'Mostra como o importador interpretou o arquivo antes de qualquer cálculo.',
    'molecular.normalise': 'Normalizar as frações pela soma',
    'molecular.normaliseHint':
      'Use quando os valores são porcentagens ou intensidades brutas, e não frações que somam um.',
    'molecular.markHouwink': 'Expoente de Mark-Houwink a',
    'molecular.markHouwinkHint':
      'Opcional. Informar um valor também calcula Mv, a massa molar média viscosimétrica. O expoente é específico do polímero, solvente e temperatura, e deve vir de um handbook ou artigo.',
    'molecular.manualEntry': 'Digitar a distribuição diretamente',
    'molecular.masses': 'Massas molares (g/mol)',
    'molecular.fractions': 'Frações em massa',
    'molecular.pairHint': 'Um valor por linha, na mesma ordem.',
    'molecular.Mn': 'Média numérica',
    'molecular.Mw': 'Média ponderal',
    'molecular.Mz': 'Média Z',
    'molecular.Mz1': 'Média Z+1',
    'molecular.Mv': 'Média viscosimétrica',
    'molecular.dispersity': 'Dispersividade (Đ)',
    'molecular.dispersityNote':
      'Đ = Mw/Mn. Próximo de 1,0 em polimerização controlada, acima de 1,5 em radicalar não controlada.',
    'molecular.MnNote': 'Ponderada pelo número de cadeias.',
    'molecular.MwNote': 'Ponderada pela massa. É o valor que o espalhamento de luz fornece.',
    'molecular.MzNote': 'Sensível à cauda de alta massa.',
    'molecular.Mz1Note': 'Muito sensível à cauda de alta massa.',
    'molecular.distribution': 'Distribuição em massa',
    'molecular.crossCheck': 'Conferência com o arquivo',
    'molecular.crossCheckNote':
      'O equipamento informou as próprias médias. Diferença grande significa que o arquivo foi mal lido.',
    'molecular.fileMn': 'Mn no arquivo',
    'molecular.fileMw': 'Mw no arquivo',
    'molecular.calcMn': 'Mn calculado',
    'molecular.calcMw': 'Mw calculado',
    'molecular.reference': 'Caso de referência',
    'molecular.referenceNote':
      'A distribuição log-normal é a forma que uma polimerização radicalar bem controlada se aproxima. Suas propriedades são conhecidas analiticamente, o que a torna uma boa conferência.',
    'molecular.referenceDispersity': 'Dispersividade alvo',
    'molecular.generate': 'Gerar',

    'thermal.title': 'Análise térmica',
    'thermal.intro':
      'TGA fornece temperaturas de degradação e resíduo; DSC fornece transição vítrea, fusão e cristalinidade.',
    'thermal.tga': 'TGA',
    'thermal.dsc': 'DSC',
    'thermal.temperature': 'Temperatura (°C)',
    'thermal.massPct': 'Massa restante (%)',
    'thermal.heatFlow': 'Fluxo de calor (W/g)',
    'thermal.heatingRate': 'Taxa de aquecimento (K/min)',
    'thermal.heatingRateHint':
      'Necessária para entalpias: o sinal é integrado em temperatura, então a taxa é necessária para obter J/g.',
    'thermal.refEnthalpy': 'Entalpia de fusão de referência (J/g)',
    'thermal.refEnthalpyHint':
      'A entalpia de fusão do mesmo polímero totalmente cristalino. Necessária para cristalinidade, e precisa ser a forma polimórfica correta.',
    'thermal.Td5': 'Td com 5 % de perda',
    'thermal.Td10': 'Td com 10 % de perda',
    'thermal.TmaxRate': 'Pico de taxa de decomposição',
    'thermal.TmaxRateNote':
      'A etapa que perde massa mais rápido. Havendo várias etapas, não é necessariamente a primeira.',
    'thermal.residue': 'Resíduo',
    'thermal.steps': 'Etapas de decomposição',
    'thermal.Tg': 'Transição vítrea',
    'thermal.TgNote':
      'Ponto médio ASTM D3418. Uma única varredura carrega a história térmica; o ciclo aquece-resfria-aquece lido no segundo aquecimento é mais confiável.',
    'thermal.Tm': 'Ponto de fusão',
    'thermal.deltaHm': 'Entalpia de fusão',
    'thermal.deltaCp': 'Degrau de capacidade térmica',
    'thermal.crystallinity': 'Cristalinidade',
    'thermal.crystallinityNote':
      'Usa a entalpia de referência informada acima. Valor acima de 100 % significa que a referência não corresponde à amostra.',
    'thermal.trace': 'Curva',
    'thermal.dtg': 'Derivada',

    'mechanical.title': 'Propriedades de tração',
    'mechanical.intro':
      'Descritores padrão a partir de uma curva tensão-deformação de engenharia, conforme ISO 527-1.',
    'mechanical.strain': 'Deformação (%)',
    'mechanical.stress': 'Tensão (MPa)',
    'mechanical.modulus': 'Módulo de Young',
    'mechanical.modulusNote':
      'Inclinação da região linear inicial. A faixa de deformação usada é informada para permitir conferência.',
    'mechanical.window': 'Faixa de deformação usada',
    'mechanical.stressMax': 'Resistência à tração',
    'mechanical.strainMax': 'Deformação no máximo',
    'mechanical.stressBreak': 'Tensão na ruptura',
    'mechanical.strainBreak': 'Deformação na ruptura',
    'mechanical.stressYield': 'Tensão de escoamento',
    'mechanical.strainYield': 'Deformação de escoamento',
    'mechanical.toughness': 'Tenacidade',
    'mechanical.toughnessNote': 'Área sob a curva. O número menos preciso daqui.',
    'mechanical.yielded': 'Apresenta escoamento',
    'mechanical.brittle': 'Rompe na tensão máxima',
    'mechanical.curve': 'Curva tensão-deformação',

    'rheology.title': 'Cisalhamento oscilatório',
    'rheology.intro': 'Descritores de uma varredura de frequência de pequena amplitude.',
    'rheology.omega': 'Frequência angular (rad/s)',
    'rheology.gPrime': "Módulo de armazenamento G' (Pa)",
    'rheology.gDoublePrime': "Módulo de perda G'' (Pa)",
    'rheology.crossover': 'Cruzamento',
    'rheology.crossoverNote': "Frequência onde G' = G''. Seu inverso é o tempo de relaxação terminal.",
    'rheology.plateau': 'Módulo de platô',
    'rheology.plateauNote':
      'Estimado pelo mínimo de tan(δ). Tende a subestimar, porque o espectro completo de relaxação não é medido.',
    'rheology.relaxation': 'Tempo de relaxação',
    'rheology.slopes': 'Inclinações terminais',
    'rheology.slopesNote':
      "Para um fundido linear de distribuição estreita a teoria dá 2 para G' e 1 para G''. Valores bem menores indicam que a varredura não atingiu o regime terminal, então o módulo de platô e a viscosidade de cisalhamento zero não têm significado.",
    'rheology.zeroShear': 'Viscosidade de cisalhamento zero',
    'rheology.gel': 'Ponto de gel (Winter-Chambon)',
    'rheology.gelYes': 'tan(δ) independe da frequência — consistente com gel crítico',
    'rheology.gelNo': 'tan(δ) varia com a frequência — sem ponto de gel nesta janela',
    'rheology.solidLike': "G' supera G'' na menor frequência",
    'rheology.liquidLike': "G'' supera G' na menor frequência",
    'rheology.masterCurve': "G' e G'' em função da frequência",

    'structure.title': 'Estrutura',
    'structure.intro':
      'Difração de raios X para cristalinidade e tamanho de cristalito; infravermelho para grupos funcionais.',
    'structure.xrd': 'DRX',
    'structure.ftir': 'FTIR',
    'structure.twoTheta': '2θ (graus)',
    'structure.intensity': 'Intensidade',
    'structure.wavelength': 'Comprimento de onda (Å)',
    'structure.instrumentFwhm': 'Alargamento instrumental (FWHM, °)',
    'structure.instrumentFwhmHint':
      'Meça em um padrão como LaB6 ou silício. Deixar em zero faz todo tamanho de cristalito sair subestimado.',
    'structure.peaks': 'Picos',
    'structure.peak': '2θ',
    'structure.dSpacing': 'd (Å)',
    'structure.size': 'Tamanho (nm)',
    'structure.fwhm': 'FWHM (°)',
    'structure.crystallinity': 'Índice de cristalinidade',
    'structure.crystallinityNote':
      'NÃO é o grau absoluto de cristalinidade. Comparável apenas entre amostras medidas com a mesma faixa, linha de base e fendas.',
    'structure.wavenumber': 'Número de onda (cm⁻¹)',
    'structure.absorbance': 'Absorbância',
    'structure.bands': 'Bandas detectadas',
    'structure.band': 'Banda',
    'structure.assignments': 'Atribuições candidatas',
    'structure.pattern': 'Difratograma',
    'structure.spectrum': 'Espectro',
    'structure.ftirWarning':
      'Isto é uma consulta de grupos funcionais, não uma identificação. Muitos polímeros compartilham os mesmos grupos, e aditivos e umidade contribuem com bandas próprias. Confirme contra um espectro de referência medido no mesmo instrumento.',

    'error.needData': 'Informe um arquivo ou digite os valores.',
    'error.needFile': 'Escolha um arquivo primeiro.',
    'error.tooFewPoints': 'São necessários ao menos {n} pontos.',
    'error.mismatched': 'As duas colunas precisam ter o mesmo número de valores.',
    'error.badNumbers': 'Alguns valores não puderam ser lidos como números.',
  },

  es: {
    'app.title': 'Polymer Analysis Toolkit',
    'app.subtitle': 'Herramientas abiertas de caracterización para científicos de polímeros',
    'app.tagline':
      'Cada resultado indica su método, sus unidades y sus hipótesis. Nada aquí es una caja negra.',
    'app.footer.developed': 'Desarrollado por',
    'app.footer.repo': 'Código fuente',
    'app.footer.docs': 'Documentación de la API',

    'nav.molecular': 'Masa molar',
    'nav.thermal': 'Térmica',
    'nav.mechanical': 'Mecánica',
    'nav.rheology': 'Reología',
    'nav.structure': 'Estructura',

    'common.calculate': 'Calcular',
    'common.calculating': 'Calculando…',
    'common.reset': 'Limpiar',
    'common.loading': 'Cargando…',
    'common.results': 'Resultados',
    'common.error': 'Error',
    'common.optional': 'opcional',
    'common.required': 'obligatorio',
    'common.upload': 'Subir un archivo',
    'common.chooseFile': 'Elegir archivo',
    'common.noFile': 'Ningún archivo seleccionado',
    'common.exportJson': 'Exportar JSON',
    'common.importDecisions': 'Cómo se leyó el archivo',
    'common.showDetails': 'Ver detalles',
    'common.hideDetails': 'Ocultar detalles',
    'common.slices': 'fracciones',
    'common.apiUrl': 'API',
    'common.apiUnreachable': 'API inaccesible',
    'common.apiOk': 'API en línea',
    'common.language': 'Idioma',

    'molecular.title': 'Distribución de masa molar',
    'molecular.intro':
      'Calcule los promedios de masa molar a partir de una distribución, subiendo la exportación del equipo o introduciendo los valores.',
    'molecular.uploadLabel': 'Exportación del equipo (CSV o texto delimitado)',
    'molecular.uploadHint':
      'Se aceptan: masa/fracción en g/mol, porcentajes, intensidad bruta del detector, eje logM, delimitador por coma o punto y coma, coma decimal, cabecera en español, inglés o portugués.',
    'molecular.preview': 'Inspeccionar archivo',
    'molecular.previewHint':
      'Muestra cómo interpretó el importador el archivo antes de calcular nada.',
    'molecular.normalise': 'Normalizar las fracciones por su suma',
    'molecular.normaliseHint':
      'Úselo cuando los valores son porcentajes o intensidades brutas en lugar de fracciones que suman uno.',
    'molecular.markHouwink': 'Exponente de Mark-Houwink a',
    'molecular.markHouwinkHint':
      'Opcional. Al indicar un valor también se calcula Mv, la masa molar promedio viscosimétrica. El exponente es específico del polímero, disolvente y temperatura, y debe provenir de un handbook o artículo.',
    'molecular.manualEntry': 'Introducir la distribución directamente',
    'molecular.masses': 'Masas molares (g/mol)',
    'molecular.fractions': 'Fracciones en peso',
    'molecular.pairHint': 'Un valor por línea, en el mismo orden.',
    'molecular.Mn': 'Promedio numérico',
    'molecular.Mw': 'Promedio ponderal',
    'molecular.Mz': 'Promedio Z',
    'molecular.Mz1': 'Promedio Z+1',
    'molecular.Mv': 'Promedio viscosimétrico',
    'molecular.dispersity': 'Dispersidad (Đ)',
    'molecular.dispersityNote':
      'Đ = Mw/Mn. Cerca de 1,0 en polimerización controlada, por encima de 1,5 en radicalaria no controlada.',
    'molecular.MnNote': 'Ponderado por el número de cadenas.',
    'molecular.MwNote': 'Ponderado por masa. Es el valor que da la dispersión de luz.',
    'molecular.MzNote': 'Sensible a la cola de alta masa.',
    'molecular.Mz1Note': 'Muy sensible a la cola de alta masa.',
    'molecular.distribution': 'Distribución en peso',
    'molecular.crossCheck': 'Contraste con el archivo',
    'molecular.crossCheckNote':
      'El equipo informó sus propios promedios. Una diferencia grande significa que el archivo se leyó mal.',
    'molecular.fileMn': 'Mn en el archivo',
    'molecular.fileMw': 'Mw en el archivo',
    'molecular.calcMn': 'Mn calculado',
    'molecular.calcMw': 'Mw calculado',
    'molecular.reference': 'Caso de referencia',
    'molecular.referenceNote':
      'La distribución log-normal es la forma a la que se aproxima una polimerización radicalaria bien controlada. Sus propiedades se conocen analíticamente, lo que la hace útil como comprobación.',
    'molecular.referenceDispersity': 'Dispersidad objetivo',
    'molecular.generate': 'Generar',

    'thermal.title': 'Análisis térmico',
    'thermal.intro':
      'TGA da temperaturas de degradación y residuo; DSC da la transición vítrea, la fusión y la cristalinidad.',
    'thermal.tga': 'TGA',
    'thermal.dsc': 'DSC',
    'thermal.temperature': 'Temperatura (°C)',
    'thermal.massPct': 'Masa restante (%)',
    'thermal.heatFlow': 'Flujo de calor (W/g)',
    'thermal.heatingRate': 'Velocidad de calentamiento (K/min)',
    'thermal.heatingRateHint':
      'Necesaria para entalpías: la señal se integra en temperatura, así que la velocidad es necesaria para obtener J/g.',
    'thermal.refEnthalpy': 'Entalpía de fusión de referencia (J/g)',
    'thermal.refEnthalpyHint':
      'La entalpía de fusión del mismo polímero totalmente cristalino. Necesaria para la cristalinidad, y debe ser el polimorfo correcto.',
    'thermal.Td5': 'Td con 5 % de pérdida',
    'thermal.Td10': 'Td con 10 % de pérdida',
    'thermal.TmaxRate': 'Pico de velocidad de descomposición',
    'thermal.TmaxRateNote':
      'La etapa que pierde masa más rápido. Con varias etapas no es necesariamente la primera.',
    'thermal.residue': 'Residuo',
    'thermal.steps': 'Etapas de descomposición',
    'thermal.Tg': 'Transición vítrea',
    'thermal.TgNote':
      'Punto medio ASTM D3418. Un único calentamiento arrastra la historia térmica; el ciclo calienta-enfría-calienta leído en el segundo calentamiento es más fiable.',
    'thermal.Tm': 'Punto de fusión',
    'thermal.deltaHm': 'Entalpía de fusión',
    'thermal.deltaCp': 'Salto de capacidad calorífica',
    'thermal.crystallinity': 'Cristalinidad',
    'thermal.crystallinityNote':
      'Usa la entalpía de referencia indicada arriba. Un valor por encima de 100 % significa que la referencia no corresponde a la muestra.',
    'thermal.trace': 'Curva',
    'thermal.dtg': 'Derivada',

    'mechanical.title': 'Propiedades de tracción',
    'mechanical.intro':
      'Descriptores estándar de una curva tensión-deformación de ingeniería, según ISO 527-1.',
    'mechanical.strain': 'Deformación (%)',
    'mechanical.stress': 'Tensión (MPa)',
    'mechanical.modulus': 'Módulo de Young',
    'mechanical.modulusNote':
      'Pendiente de la región lineal inicial. Se informa el intervalo de deformación usado para poder verificarlo.',
    'mechanical.window': 'Intervalo de deformación usado',
    'mechanical.stressMax': 'Resistencia a la tracción',
    'mechanical.strainMax': 'Deformación en el máximo',
    'mechanical.stressBreak': 'Tensión de rotura',
    'mechanical.strainBreak': 'Deformación de rotura',
    'mechanical.stressYield': 'Tensión de fluencia',
    'mechanical.strainYield': 'Deformación de fluencia',
    'mechanical.toughness': 'Tenacidad',
    'mechanical.toughnessNote': 'Área bajo la curva. El número menos preciso de aquí.',
    'mechanical.yielded': 'Presenta fluencia',
    'mechanical.brittle': 'Rompe en la tensión máxima',
    'mechanical.curve': 'Curva tensión-deformación',

    'rheology.title': 'Cizalla oscilatoria',
    'rheology.intro': 'Descriptores de un barrido de frecuencia de pequeña amplitud.',
    'rheology.omega': 'Frecuencia angular (rad/s)',
    'rheology.gPrime': "Módulo de almacenamiento G' (Pa)",
    'rheology.gDoublePrime': "Módulo de pérdida G'' (Pa)",
    'rheology.crossover': 'Cruce',
    'rheology.crossoverNote': "Frecuencia donde G' = G''. Su inversa es el tiempo de relajación terminal.",
    'rheology.plateau': 'Módulo de plateau',
    'rheology.plateauNote':
      'Estimado del mínimo de tan(δ). Tiende a subestimar, porque no se mide el espectro completo de relajación.',
    'rheology.relaxation': 'Tiempo de relajación',
    'rheology.slopes': 'Pendientes terminales',
    'rheology.slopesNote':
      "Para un fundido lineal de distribución estrecha la teoría da 2 para G' y 1 para G''. Valores mucho menores indican que el barrido no alcanzó el régimen terminal, así que el módulo de plateau y la viscosidad de cizalla cero no son significativos.",
    'rheology.zeroShear': 'Viscosidad de cizalla cero',
    'rheology.gel': 'Punto de gel (Winter-Chambon)',
    'rheology.gelYes': 'tan(δ) no depende de la frecuencia — consistente con gel crítico',
    'rheology.gelNo': 'tan(δ) varía con la frecuencia — sin punto de gel en esta ventana',
    'rheology.solidLike': "G' supera a G'' en la frecuencia más baja",
    'rheology.liquidLike': "G'' supera a G' en la frecuencia más baja",
    'rheology.masterCurve': "G' y G'' frente a la frecuencia",

    'structure.title': 'Estructura',
    'structure.intro':
      'Difracción de rayos X para cristalinidad y tamaño de cristalito; infrarrojo para grupos funcionales.',
    'structure.xrd': 'DRX',
    'structure.ftir': 'FTIR',
    'structure.twoTheta': '2θ (grados)',
    'structure.intensity': 'Intensidad',
    'structure.wavelength': 'Longitud de onda (Å)',
    'structure.instrumentFwhm': 'Ensanchamiento instrumental (FWHM, °)',
    'structure.instrumentFwhmHint':
      'Mídalo en un estándar como LaB6 o silicio. Dejarlo en cero hace que todo tamaño de cristalito salga subestimado.',
    'structure.peaks': 'Picos',
    'structure.peak': '2θ',
    'structure.dSpacing': 'd (Å)',
    'structure.size': 'Tamaño (nm)',
    'structure.fwhm': 'FWHM (°)',
    'structure.crystallinity': 'Índice de cristalinidad',
    'structure.crystallinityNote':
      'NO es el grado absoluto de cristalinidad. Comparable solo entre muestras medidas con el mismo rango, línea base y rendijas.',
    'structure.wavenumber': 'Número de onda (cm⁻¹)',
    'structure.absorbance': 'Absorbancia',
    'structure.bands': 'Bandas detectadas',
    'structure.band': 'Banda',
    'structure.assignments': 'Asignaciones candidatas',
    'structure.pattern': 'Difractograma',
    'structure.spectrum': 'Espectro',
    'structure.ftirWarning':
      'Esto es una consulta de grupos funcionales, no una identificación. Muchos polímeros comparten los mismos grupos, y los aditivos y la humedad aportan sus propias bandas. Confirme contra un espectro de referencia medido en el mismo instrumento.',

    'error.needData': 'Indique un archivo o introduzca los valores.',
    'error.needFile': 'Elija un archivo primero.',
    'error.tooFewPoints': 'Se necesitan al menos {n} puntos.',
    'error.mismatched': 'Las dos columnas deben tener el mismo número de valores.',
    'error.badNumbers': 'Algunos valores no pudieron leerse como números.',
  },
};

const STORAGE_KEY = 'pat.language';

function detectInitialLanguage() {
  if (typeof window === 'undefined') return 'en';
  const stored = window.localStorage?.getItem(STORAGE_KEY);
  if (stored && MESSAGES[stored]) return stored;
  const nav = window.navigator?.language?.slice(0, 2)?.toLowerCase();
  if (nav && MESSAGES[nav]) return nav;
  return 'en';
}

const I18nContext = createContext({
  language: 'en',
  setLanguage: () => {},
  t: (key) => key,
});

export function I18nProvider({ children }) {
  const [language, setLanguage] = useState(detectInitialLanguage);

  useEffect(() => {
    try {
      window.localStorage?.setItem(STORAGE_KEY, language);
    } catch {
      // Storage can be unavailable (private mode); the language still applies
      // for this session.
    }
    document.documentElement.lang = language;
  }, [language]);

  const value = useMemo(() => {
    const translate = (key, vars) => {
      const table = MESSAGES[language] || MESSAGES.en;
      let text = table[key];
      if (text === undefined) {
        text = MESSAGES.en[key];
        if (text === undefined) {
          if (process.env.NODE_ENV !== 'production') {
            // eslint-disable-next-line no-console
            console.warn(`[i18n] missing key: ${key}`);
          }
          return key;
        }
      }
      if (vars) {
        Object.entries(vars).forEach(([k, v]) => {
          text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
        });
      }
      return text;
    };
    return { language, setLanguage, t: translate };
  }, [language]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}

/** Format a number for display with a sensible precision for the magnitude. */
export function formatNumber(value, digits) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  if (typeof value !== 'number') return String(value);
  const abs = Math.abs(value);
  let d = digits;
  if (d === undefined) {
    if (abs === 0) d = 3;
    else if (abs >= 1e6) d = 0;
    else if (abs >= 1e3) d = 1;
    else if (abs >= 1) d = 3;
    else if (abs >= 1e-3) d = 4;
    else d = 6;
  }
  return value.toLocaleString(undefined, {
    minimumFractionDigits: d,
    maximumFractionDigits: d,
  });
}

export default I18nProvider;
