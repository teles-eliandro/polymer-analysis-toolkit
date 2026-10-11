"""Mensagens dirigidas ao utilizador, nos tres idiomas.

Porque este modulo existe
-------------------------
As mensagens de recusa e de aviso do backend estavam escritas em dois idiomas ao
mesmo tempo: ``trace_io`` e a camada da API em portugues, ``core/thermal`` em
ingles. O resultado no ecra era o defeito que o utilizador descreveu -- "texto
em ingles com pedacos de texto em portugues" -- e nenhuma auditoria da frontend
podia ve-lo, porque o texto nao vem da frontend.

Porque nao a abordagem do codigo estavel
----------------------------------------
Para prosa de conjunto ABERTO (uma nova forma de falha acrescenta uma mensagem)
o padrao certo e o codigo estavel e o cliente traduz -- e e o que este
repositorio ja faz para ``reason``/``reason_code`` na comparacao. Aqui o
conjunto e FECHADO: sao as mensagens que este codigo escreve, e um teste
percorre-o. Para um conjunto fechado, o modulo de traducao fica no lado que
produz o texto, e a carga da API nao muda de forma -- nenhum cliente antigo
parte.

E a mesma decisao ja tomada para a tabela de entalpias de referencia
(``crystallinity_ref_i18n.py``), pelo mesmo motivo.

A lingua de origem e o portugues; ``lang="pt"`` e o padrao, para que um cliente
que nao envie ``lang`` receba exactamente o que recebia antes.
"""
from __future__ import annotations

from typing import Any

#: Idioma de origem e fallback. Nao traduzir as CHAVES.
IDIOMA_ORIGEM = "pt"
IDIOMAS = ("pt", "en", "es")


def _norm(lang: str | None) -> str:
    """Normaliza o codigo de idioma; desconhecido cai no idioma de origem."""
    if not lang:
        return IDIOMA_ORIGEM
    codigo = str(lang).strip().lower().replace("_", "-").split("-")[0]
    return codigo if codigo in IDIOMAS else IDIOMA_ORIGEM


# ---------------------------------------------------------------------------
# Rotulos de papel de coluna. Sao substantivos curtos, mas aparecem no meio de
# uma frase ("Nao encontrei a coluna de <rotulo>"), entao traduzem-se.
# ---------------------------------------------------------------------------
ROLE = {
    "temperature": {"pt": "temperatura", "en": "temperature", "es": "temperatura"},
    "heat_flow": {"pt": "fluxo de calor", "en": "heat flow", "es": "flujo de calor"},
    "mass": {"pt": "massa", "en": "mass", "es": "masa"},
    "stress": {"pt": "tensão", "en": "stress", "es": "tensión"},
    "strain": {"pt": "deformação", "en": "strain", "es": "deformación"},
    "time": {"pt": "tempo", "en": "time", "es": "tiempo"},
    "omega": {"pt": "frequência angular", "en": "angular frequency", "es": "frecuencia angular"},
    "g_prime": {"pt": "módulo de armazenamento G'", "en": "storage modulus G'", "es": "módulo de almacenamiento G'"},
    "g_double_prime": {"pt": "módulo de perdas G''", "en": "loss modulus G''", "es": "módulo de pérdidas G''"},
    "wavenumber": {"pt": "número de onda", "en": "wavenumber", "es": "número de onda"},
    "transmittance": {"pt": "transmitância", "en": "transmittance", "es": "transmitancia"},
    "absorbance": {"pt": "absorbância", "en": "absorbance", "es": "absorbancia"},
    "two_theta": {"pt": "ângulo 2θ", "en": "2θ angle", "es": "ángulo 2θ"},
    "intensity": {"pt": "intensidade", "en": "intensity", "es": "intensidad"},
}

# ---------------------------------------------------------------------------
# Mensagens. Cada chave e estavel; o texto usa {campos} nomeados.
# ---------------------------------------------------------------------------
MSG: dict[str, dict[str, str]] = {
    # --- leitura do ficheiro: eixos -------------------------------------
    "trace.axis.missing": {
        "pt": "Não encontrei a coluna de {role}. O arquivo tem: {found}. Se o papel da coluna for outro, renomeie o cabeçalho ou converta o arquivo para CSV de duas colunas.",
        "en": "I could not find the {role} column. The file has: {found}. If the column plays a different role, rename the header or convert the file to a two-column CSV.",
        "es": "No encontré la columna de {role}. El archivo tiene: {found}. Si el papel de la columna es otro, renombre el encabezado o convierta el archivo a un CSV de dos columnas.",
    },
    "trace.axis.missing_short": {
        "pt": "Não encontrei a coluna de {role}. O arquivo tem: {found}.",
        "en": "I could not find the {role} column. The file has: {found}.",
        "es": "No encontré la columna de {role}. El archivo tiene: {found}.",
    },
    "trace.axis.unit_unconvertible": {
        "pt": "a coluna está em '{unit}', e converter para a unidade canônica exige um dado que o arquivo não traz (por exemplo a massa da amostra para um sinal absoluto em mW). Forneça o dado ou exporte o sinal normalizado pela massa.",
        "en": "the column is in '{unit}', and converting to the canonical unit needs a value the file does not carry (the sample mass, for instance, for an absolute signal in mW). Supply that value or export the signal normalised by mass.",
        "es": "la columna está en '{unit}', y convertir a la unidad canónica exige un dato que el archivo no trae (por ejemplo la masa de la muestra para una señal absoluta en mW). Proporcione el dato o exporte la señal normalizada por la masa.",
    },
    "trace.axis.factor_unknown": {
        "pt": "conversão '{factor}' não implementada",
        "en": "conversion '{factor}' is not implemented",
        "es": "conversión '{factor}' no implementada",
    },
    "trace.axis.x": {
        "pt": "eixo x: {reason}",
        "en": "x axis: {reason}",
        "es": "eje x: {reason}",
    },
    "trace.axis.y": {
        "pt": "eixo y: {reason}",
        "en": "y axis: {reason}",
        "es": "eje y: {reason}",
    },
    # --- leitura do ficheiro: forma dos dados ---------------------------
    "trace.too_few_points": {
        "pt": "Só {n} ponto(s) utilizáveis: a análise precisa de pelo menos 3.",
        "en": "Only {n} usable point(s): the analysis needs at least 3.",
        "es": "Solo {n} punto(s) utilizables: el análisis necesita al menos 3.",
    },
    "trace.ragged_columns": {
        "pt": "As colunas têm comprimentos diferentes ({nx} e {ny}); usei os {n} primeiros pontos de cada.",
        "en": "The columns have different lengths ({nx} and {ny}); I used the first {n} points of each.",
        "es": "Las columnas tienen longitudes distintas ({nx} y {ny}); usé los {n} primeros puntos de cada una.",
    },
    "trace.non_numeric_dropped": {
        "pt": "{dropped} ponto(s) não numéricos foram descartados.",
        "en": "{dropped} non-numeric point(s) were dropped.",
        "es": "{dropped} punto(s) no numéricos fueron descartados.",
    },
    "trace.after_dropping_too_few": {
        "pt": "Depois de descartar valores não numéricos sobraram menos de 3 pontos.",
        "en": "After dropping non-numeric values, fewer than 3 points remained.",
        "es": "Tras descartar los valores no numéricos quedaron menos de 3 puntos.",
    },
    "trace.x_descending": {
        "pt": "O eixo x vinha decrescente; inverti a ordem.",
        "en": "The x axis came in descending order; I reversed it.",
        "es": "El eje x venía decreciente; invertí el orden.",
    },
    "trace.x_out_of_order": {
        "pt": "{bad} ponto(s) fora de ordem no eixo x foram ignorados.",
        "en": "{bad} out-of-order point(s) on the x axis were ignored.",
        "es": "{bad} punto(s) fuera de orden en el eje x fueron ignorados.",
    },
    "trace.exo_up_inverted": {
        "pt": "O cabeçalho declara exotérmico PARA CIMA (#EXO); inverti o sinal para a convenção endotérmico-para-cima que a análise usa.",
        "en": "The header declares exothermic UP (#EXO); I flipped the sign to the endothermic-up convention the analysis uses.",
        "es": "El encabezado declara exotérmico HACIA ARRIBA (#EXO); invertí el signo a la convención endotérmico-hacia-arriba que usa el análisis.",
    },
    "trace.percent_t_converted": {
        "pt": "O arquivo exporta %T (transmitância); converti para absorbância com A = 2 - log10(%T), que é a grandeza que a análise usa.",
        "en": "The file exports %T (transmittance); I converted to absorbance with A = 2 - log10(%T), which is the quantity the analysis uses.",
        "es": "El archivo exporta %T (transmitancia); convertí a absorbancia con A = 2 - log10(%T), que es la magnitud que usa el análisis.",
    },
    "trace.unresolved": {
        "pt": "não resolvido: {error}",
        "en": "unresolved: {error}",
        "es": "no resuelto: {error}",
    },
    # --- leitura do ficheiro: formatos e cabecalhos ---------------------
    "trace.binary_file": {
        "pt": "o arquivo parece binário, não um export de texto delimitado. Se for um formato proprietário do instrumento (ex.: .tri, .ngb-sd7), exporte-o como texto/CSV, ou informe o formato para que o leitor correto seja usado.",
        "en": "the file looks binary, not a delimited text export. If it is an instrument-proprietary format (e.g. .tri, .ngb-sd7), export it as text/CSV, or state the format so the correct reader is used.",
        "es": "el archivo parece binario, no una exportación de texto delimitada. Si es un formato propio del instrumento (p. ej. .tri, .ngb-sd7), expórtelo como texto/CSV, o indique el formato para que se use el lector correcto.",
    },
    "trace.keyval.no_data_start": {
        "pt": "{name}: o cabeçalho foi lido, mas não encontrei o início dos dados. Um espectro JASCO/PerkinElmer traz uma linha 'XYDATA' antes dos pontos.",
        "en": "{name}: the header was read, but I could not find where the data begins. A JASCO/PerkinElmer spectrum carries an 'XYDATA' line before the points.",
        "es": "{name}: se leyó el encabezado, pero no encontré el inicio de los datos. Un espectro JASCO/PerkinElmer trae una línea 'XYDATA' antes de los puntos.",
    },
    "trace.keyval.no_points": {
        "pt": "{name}: o marcador de dados existe mas não há pontos.",
        "en": "{name}: the data marker is present but there are no points.",
        "es": "{name}: el marcador de datos existe pero no hay puntos.",
    },
    "trace.keyval.no_numeric": {
        "pt": "{name}: nenhuma linha de dados numérica foi lida.",
        "en": "{name}: no numeric data line was read.",
        "es": "{name}: no se leyó ninguna línea de datos numérica.",
    },
    "trace.keyval.unknown_units": {
        "pt": "{name}: o cabeçalho declara XUNITS='{x}' e YUNITS='{y}', que não sei mapear. Espectros conhecidos: XUNITS em 1/CM (número de onda) e YUNITS em ABSORBANCE ou %T.",
        "en": "{name}: the header declares XUNITS='{x}' and YUNITS='{y}', which I cannot map. Known spectra: XUNITS in 1/CM (wavenumber) and YUNITS in ABSORBANCE or %T.",
        "es": "{name}: el encabezado declara XUNITS='{x}' e YUNITS='{y}', que no sé mapear. Espectros conocidos: XUNITS en 1/CM (número de onda) y YUNITS en ABSORBANCE o %T.",
    },
    "trace.tri.no_channel": {
        "pt": "{name}: nenhum canal numérico recuperado do arquivo .tri",
        "en": "{name}: no numeric channel recovered from the .tri file",
        "es": "{name}: ningún canal numérico recuperado del archivo .tri",
    },
    "trace.tri.missing_channels": {
        "pt": "canal de temperatura ou de fluxo de calor ausente: papéis presentes = {roles}",
        "en": "temperature or heat-flow channel missing: roles present = {roles}",
        "es": "canal de temperatura o de flujo de calor ausente: papeles presentes = {roles}",
    },
    "trace.no_data_lines": {
        "pt": "{name}: nenhuma linha de dados encontrada",
        "en": "{name}: no data line found",
        "es": "{name}: no se encontró ninguna línea de datos",
    },
    "trace.percent_t_over_100": {
        "pt": "{n} ponto(s) traziam %T acima de 100 (deriva de linha de base do instrumento); limitei a 100 antes de converter, porque transmitância acima de 100 % é fisicamente impossível e daria absorbância negativa, que a análise recusa.",
        "en": "{n} point(s) carried %T above 100 (instrument baseline drift); I clamped them to 100 before converting, because transmittance above 100 % is physically impossible and would yield a negative absorbance, which the analysis refuses.",
        "es": "{n} punto(s) traían %T por encima de 100 (deriva de línea base del instrumento); los limité a 100 antes de convertir, porque una transmitancia por encima de 100 % es físicamente imposible y daría una absorbancia negativa, que el análisis rechaza.",
    },
    "trace.x_not_monotonic": {
        "pt": "O eixo x não é monotônico ({bad} de {total} passos decrescentes). Isto costuma indicar um método com várias rampas; o PAT analisa uma rampa por vez.",
        "en": "The x axis is not monotonic ({bad} of {total} steps decreasing). This usually indicates a multi-ramp method; PAT analyses one ramp at a time.",
        "es": "El eje x no es monótono ({bad} de {total} pasos decrecientes). Esto suele indicar un método con varias rampas; PAT analiza una rampa a la vez.",
    },
    # --- amostragem e transições ----------------------------------------
    "trace.sparse_points_per_degree": {
        "pt": "O traço tem {ppd:.1f} ponto(s) por grau ({n} pontos em {span:.0f} graus). Abaixo de {minimum:.0f} pontos por grau o degrau de uma transição vítrea é mais estreito que o espaçamento, e nenhum detector pode localizá-lo: um valor de Tg reportado neste arquivo é ruído da linha de base, não uma transição. O pico de fusão, que é largo, continua utilizável.",
        "en": "The trace has {ppd:.1f} point(s) per degree ({n} points over {span:.0f} degrees). Below {minimum:.0f} points per degree the step of a glass transition is narrower than the spacing, and no detector can locate it: a Tg value reported from this file is baseline noise, not a transition. The melting peak, which is broad, remains usable.",
        "es": "La traza tiene {ppd:.1f} punto(s) por grado ({n} puntos en {span:.0f} grados). Por debajo de {minimum:.0f} puntos por grado el escalón de una transición vítrea es más estrecho que el espaciado, y ningún detector puede localizarlo: un valor de Tg informado en este archivo es ruido de la línea base, no una transición. El pico de fusión, que es ancho, sigue siendo utilizable.",
    },
    "trace.sparse_tg_refused": {
        "pt": "O traço tem {ppd:.1f} ponto(s) por grau. Abaixo de {minimum:.0f} nenhuma temperatura de transição vítrea é localizável neste arquivo; um pico largo, como o de fusão, continua utilizável.",
        "en": "The trace has {ppd:.1f} point(s) per degree. Below {minimum:.0f} no glass transition temperature is locatable in this file; a broad peak, such as melting, remains usable.",
        "es": "La traza tiene {ppd:.1f} punto(s) por grado. Por debajo de {minimum:.0f} ninguna temperatura de transición vítrea es localizable en este archivo; un pico ancho, como el de fusión, sigue siendo utilizable.",
    },
    "trace.fields_omitted": {
        "pt": "Os campos {fields} foram omitidos por não serem localizáveis neste arquivo.",
        "en": "The fields {fields} were omitted because they are not locatable in this file.",
        "es": "Los campos {fields} fueron omitidos por no ser localizables en este archivo.",
    },
    # --- TGA ------------------------------------------------------------
    "tga.unattributed_loss": {
        "pt": "{unattributed:.1f} % da perda de massa não faz parte de nenhum passo reportado. Ou está espalhada de forma demasiado gradual para a sua velocidade se destacar do ruído, ou está distribuída por passos que se sobrepõem. Cada passo reportado é real; a lista não é necessariamente completa.",
        "en": "{unattributed:.1f} % of the mass loss is not part of any reported step. It is either spread too gradually for its rate to stand out against the noise, or spread across steps that overlap. Each reported step is real; the list is not necessarily complete.",
        "es": "{unattributed:.1f} % de la pérdida de masa no forma parte de ningún paso informado. O está repartida de forma demasiado gradual para que su velocidad destaque sobre el ruido, o está distribuida entre pasos que se solapan. Cada paso informado es real; la lista no es necesariamente completa.",
    },
    "tga.one_step_early_loss": {
        "pt": "Foi detectado um passo, de {onset:.0f} a {end:.0f} °C, mas {early:.1f} % da sua perda acontece no primeiro quarto desse intervalo. Um evento fraco (humidade ou solvente) está provavelmente a cavalo da decomposição principal; fica incluído neste passo em vez de ser reportado em separado porque a sua velocidade não se destaca do ruído.",
        "en": "One step was detected, spanning {onset:.0f}-{end:.0f} C, but {early:.1f} % of its loss happens in the first quarter of that range. A weak event (moisture or solvent) is probably riding on the main decomposition; it is included in this step rather than reported separately because its rate does not stand out against the noise.",
        "es": "Se detectó un paso, de {onset:.0f} a {end:.0f} °C, pero {early:.1f} % de su pérdida ocurre en el primer cuarto de ese rango. Un evento débil (humedad o disolvente) probablemente cabalga sobre la descomposición principal; queda incluido en este paso en lugar de informarse por separado porque su velocidad no destaca sobre el ruido.",
    },
    "tga.several_steps": {
        "pt": "Foram detectados vários passos. T_max_rate nomeia o mais rápido, que não é necessariamente o primeiro; use a lista de passos para os onsets de cada um.",
        "en": "Several steps were detected. T_max_rate names the fastest one, which is not necessarily the first; use the step list for per-step onsets.",
        "es": "Se detectaron varios pasos. T_max_rate nombra el más rápido, que no es necesariamente el primero; use la lista de pasos para los onsets de cada uno.",
    },
    "tga.residue_negative": {
        "pt": "O traço termina a {residue:.2f} % de massa, um valor negativo e portanto não um resíduo físico. É o valor do próprio instrumento, reportado sem alteração; o ensaio derivou ou foi mal zerado. Não cite isto como resíduo.",
        "en": "The trace ends at {residue:.2f} % mass, which is negative and therefore not a physical residue. This is the instrument's own value, reported unchanged; the run either drifted or was mis-zeroed. Do not quote this as a residue.",
        "es": "La traza termina en {residue:.2f} % de masa, un valor negativo y por tanto no un residuo físico. Es el valor del propio instrumento, informado sin cambios; el ensayo derivó o se puso a cero mal. No cite esto como residuo.",
    },
    "tga.residue_above_start": {
        "pt": "O traço termina a {residue:.2f} % de massa, acima do valor inicial. Impulsão ou uma balança mal zerada são a causa habitual; trate o resíduo como não quantificado.",
        "en": "The trace ends at {residue:.2f} % mass, above the starting value. Buoyancy or a mis-zeroed balance is the usual cause; treat the residue as unquantified.",
        "es": "La traza termina en {residue:.2f} % de masa, por encima del valor inicial. El empuje o una balanza mal puesta a cero son la causa habitual; trate el residuo como no cuantificado.",
    },
    "tga.start_below_100": {
        "pt": "O traço começa a {start_pct:.1f} % em vez de 100 %. É normalizado ao seu próprio primeiro ponto, então o eixo percentual é relativo; um ensaio que começa tão longe de 100 % já perdeu voláteis antes da rampa.",
        "en": "The trace starts at {start_pct:.1f} % rather than 100 %. It is normalised to its own first point, so the percentage axis is relative; a run that begins this far from 100 % has already lost volatiles before the ramp.",
        "es": "La traza empieza en {start_pct:.1f} % en lugar de 100 %. Se normaliza a su propio primer punto, así que el eje porcentual es relativo; un ensayo que empieza tan lejos de 100 % ya ha perdido volátiles antes de la rampa.",
    },
    # --- DSC / cristalinidade -------------------------------------------
    "dsc.ref_enthalpy_from_db": {
        "pt": "Entalpia de referência de 100 % cristalino tomada do banco interno para '{name}' ({key}): {value:g} J/g. Fonte: {source}",
        "en": "Reference enthalpy of 100 % crystalline taken from the internal database for '{name}' ({key}): {value:g} J/g. Source: {source}",
        "es": "Entalpía de referencia de 100 % cristalino tomada de la base interna para '{name}' ({key}): {value:g} J/g. Fuente: {source}",
    },
    "dsc.amorphous_refused": {
        "pt": "A amostra foi reconhecida como {name}, que é amorfo e não tem entalpia de referência: a cristalinidade não se aplica. {note}",
        "en": "The sample was recognised as {name}, which is amorphous and has no reference enthalpy: crystallinity does not apply. {note}",
        "es": "La muestra fue reconocida como {name}, que es amorfa y no tiene entalpía de referencia: la cristalinidad no se aplica. {note}",
    },
    "dsc.heating_rate_missing": {
        "pt": "O arquivo não declara a taxa de aquecimento, então a cristalinidade não foi calculada. O ΔHm é reportado em J/g apenas se a taxa for fornecida.",
        "en": "The file does not declare the heating rate, so crystallinity was not calculated. ΔHm is reported in J/g only if the rate is supplied.",
        "es": "El archivo no declara la velocidad de calentamiento, así que no se calculó la cristalinidad. El ΔHm se informa en J/g solo si se proporciona la velocidad.",
    },
    "dsc.ref_enthalpy_missing": {
        "pt": "Nenhuma entalpia de referência foi fornecida, e o nome da amostra não foi reconhecido no banco interno (GET /api/v1/thermal/crystallinity-references lista o que existe). O ΔHm é reportado, mas sem cristalinidade.",
        "en": "No reference enthalpy was supplied, and the sample name was not recognised in the internal database (GET /api/v1/thermal/crystallinity-references lists what exists). ΔHm is reported, but without crystallinity.",
        "es": "No se proporcionó ninguna entalpía de referencia, y el nombre de la muestra no fue reconocido en la base interna (GET /api/v1/thermal/crystallinity-references lista lo que existe). El ΔHm se informa, pero sin cristalinidad.",
    },
    "dsc.impossible_crystallinity": {
        "pt": "A cristalinidade calculada ({xc:.1f} %) é fisicamente impossível: o ΔHm medido ({dhm:.1f} J/g) excede a entalpia de referência de 100 % cristalino ({ref:g} J/g). O valor é reportado para inspeção, mas não pode ser usado como resultado. Verifique se a referência é a deste polímero, se a amostra tem uma só fase cristalina, e se a linha de base da integração está correta.",
        "en": "The calculated crystallinity ({xc:.1f} %) is physically impossible: the measured ΔHm ({dhm:.1f} J/g) exceeds the reference enthalpy of 100 % crystalline ({ref:g} J/g). The value is reported for inspection but cannot be used as a result. Check whether the reference is the one for this polymer, whether the sample has a single crystalline phase, and whether the integration baseline is correct.",
        "es": "La cristalinidad calculada ({xc:.1f} %) es físicamente imposible: el ΔHm medido ({dhm:.1f} J/g) supera la entalpía de referencia de 100 % cristalino ({ref:g} J/g). El valor se informa para inspección, pero no puede usarse como resultado. Verifique si la referencia es la de este polímero, si la muestra tiene una sola fase cristalina, y si la línea base de integración es correcta.",
    },
}


def role_label(role: str, lang: str | None = IDIOMA_ORIGEM) -> str:
    """Rotulo de um papel de coluna, no idioma pedido."""
    tabela = ROLE.get(role)
    if not tabela:
        return role
    return tabela.get(_norm(lang)) or tabela[IDIOMA_ORIGEM]


def msg(code: str, lang: str | None = IDIOMA_ORIGEM, **params: Any) -> str:
    """A mensagem ``code`` no idioma pedido, com os valores interpolados.

    Um codigo desconhecido devolve o proprio codigo em vez de explodir: a
    mensagem e para o utilizador, e um ``KeyError`` aqui trocaria um aviso por
    um 500. O teste de cobertura garante que isso nunca acontece na pratica.
    """
    tabela = MSG.get(code)
    if not tabela:
        return code
    texto = tabela.get(_norm(lang)) or tabela[IDIOMA_ORIGEM]
    if params:
        try:
            texto = texto.format(**params)
        except (KeyError, IndexError, ValueError):
            # Um valor em falta nao pode fazer desaparecer a mensagem inteira.
            return texto
    return texto
