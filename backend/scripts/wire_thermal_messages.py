#!/usr/bin/env python3
"""Camada 2: liga o catalogo trilingue as mensagens do caminho termico.

O que estava errado
-------------------
As mensagens de recusa e de aviso chegavam ao utilizador no idioma errado, e em
dois idiomas incompatives: ``trace_io`` escrevia em portugues, ``core/thermal``
em ingles. Na pagina em portugues apareciam paragrafos em ingles; na pagina em
ingles, recusas em portugues. Nenhuma auditoria da frontend podia ver isto --
o texto nao vem da frontend.

Alcance desta passagem
----------------------
O caminho termico: leitura de ficheiro (``trace_io``), analise TGA/DSC
(``core/thermal``) e a camada da API (``api/v1/thermal``). E a superficie cujas
mensagens chegam ao ecra (o painel termico renderiza ``refusals``).

Idempotente: cada substituicao so e aplicada se o trecho antigo ainda existir, e
o script recusa correr duas vezes sobre o mesmo trecho.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TRACE = RAIZ / "app" / "core" / "trace_io.py"
THERMAL = RAIZ / "app" / "core" / "thermal.py"
API = RAIZ / "app" / "api" / "v1" / "thermal.py"

# ---------------------------------------------------------------------------
# trace_io.py -- 23 trechos, texto identico ao que esta no ficheiro.
# ---------------------------------------------------------------------------
TRACE_EDICOES: list[tuple] = [
    (
        'raise TraceImportError(\n            "o arquivo parece binário, não um export de texto delimitado. "\n            "Se for um formato proprietário do instrumento (ex.: .tri, .ngb-sd7), "\n            "exporte-o como texto/CSV, ou informe o formato para que o leitor "\n            "correto seja usado."\n        )',
        'raise TraceImportError(msg("trace.binary_file", lang))',
    ),
    (
        'raise TraceImportError(\n            f"{p.name}: o cabeçalho foi lido, mas não encontrei o início dos "\n            "dados. Um espectro JASCO/PerkinElmer traz uma linha \'XYDATA\' "\n            "antes dos pontos."\n        )',
        'raise TraceImportError(msg("trace.keyval.no_data_start", lang, name=p.name))',
    ),
    (
        'raise TraceImportError(f"{p.name}: o marcador de dados existe mas não há pontos.")',
        'raise TraceImportError(msg("trace.keyval.no_points", lang, name=p.name))',
    ),
    (
        'raise TraceImportError(f"{p.name}: nenhuma linha de dados numérica foi lida.")',
        'raise TraceImportError(msg("trace.keyval.no_numeric", lang, name=p.name))',
    ),
    (
        'raise TraceImportError(\n            f"{p.name}: o cabeçalho declara XUNITS=\'{x_unit_raw or \'?\'}\' e "\n            f"YUNITS=\'{y_unit_raw or \'?\'}\', que não sei mapear. Espectros "\n            "conhecidos: XUNITS em 1/CM (número de onda) e YUNITS em "\n            "ABSORBANCE ou %T."\n        )',
        'raise TraceImportError(\n            msg(\n                "trace.keyval.unknown_units",\n                lang,\n                name=p.name,\n                x=x_unit_raw or "?",\n                y=y_unit_raw or "?",\n            )\n        )',
    ),
    (
        'warnings.append(\n            "O arquivo exporta %T (transmitância); converti para absorbância "\n            "com A = 2 - log10(%T), que é a grandeza que a análise de FTIR pede."\n        )',
        'warnings.append(msg("trace.percent_t_converted", lang))',
    ),
    (
        'warnings.append(\n                f"{n_over} ponto(s) traziam %T acima de 100 (deriva de linha "\n                "de base do instrumento); limitei a 100 antes de converter, "\n                "porque transmitância acima de 100 % é fisicamente impossível "\n                "e daria absorbância negativa, que a análise recusa."\n            )',
        'warnings.append(msg("trace.percent_t_over_100", lang, n=n_over))',
    ),
    (
        'raise TraceImportError(f"{p.name}: nenhum canal numérico recuperado do arquivo .tri")',
        'raise TraceImportError(msg("trace.tri.no_channel", lang, name=p.name))',
    ),
    (
        'warnings.append(\n            "canal de temperatura ou de fluxo de calor ausente: "\n            f"papéis presentes = {sorted(r for r in roles if r)}"\n        )',
        'warnings.append(\n            msg(\n                "trace.tri.missing_channels",\n                lang,\n                roles=sorted(r for r in roles if r),\n            )\n        )',
    ),
    (
        'raise TraceImportError(f"{p.name}: nenhuma linha de dados encontrada")',
        'raise TraceImportError(msg("trace.no_data_lines", lang, name=p.name))',
    ),
    (
        'raise TraceImportError(\n            f"Não encontrei a coluna de {_ROLE_LABEL.get(x_role, x_role)}. "\n            f"O arquivo tem: {found}. Se o papel da coluna for outro, "\n            "renomeie o cabeçalho ou converta o arquivo para CSV de duas colunas."\n        )',
        'raise TraceImportError(\n            msg(\n                "trace.axis.missing",\n                lang,\n                role=role_label(x_role, lang),\n                found=found,\n            )\n        )',
    ),
    (
        'raise TraceImportError(\n            f"Não encontrei a coluna de {_ROLE_LABEL.get(y_role, y_role)}. "\n            f"O arquivo tem: {found}."\n        )',
        'raise TraceImportError(\n            msg(\n                "trace.axis.missing_short",\n                lang,\n                role=role_label(y_role, lang),\n                found=found,\n            )\n        )',
    ),
    (
        'raise TraceImportError(f"Só {n} ponto(s) utilizáveis: a análise precisa de pelo menos 3.")',
        'raise TraceImportError(msg("trace.too_few_points", lang, n=n))',
    ),
    (
        'notes.append(\n            f"As colunas têm comprimentos diferentes "\n            f"({len(xc.values)} e {len(yc.values)}); usei os {n} primeiros "\n            "pontos de cada."\n        )',
        'notes.append(\n            msg(\n                "trace.ragged_columns",\n                lang,\n                nx=len(xc.values),\n                ny=len(yc.values),\n                n=n,\n            )\n        )',
    ),
    (
        'notes.append(f"{dropped} ponto(s) não numéricos foram descartados.")',
        'notes.append(msg("trace.non_numeric_dropped", lang, dropped=dropped))',
    ),
    (
        'raise TraceImportError(\n            "Depois de descartar valores não numéricos sobraram menos de 3 " "pontos."\n        )',
        'raise TraceImportError(msg("trace.after_dropping_too_few", lang))',
    ),
    (
        'refusals.append(f"eixo x: {x_refuse}")',
        'refusals.append(msg("trace.axis.x", lang, reason=x_refuse))',
    ),
    (
        'refusals.append(f"eixo y: {y_refuse}")',
        'refusals.append(msg("trace.axis.y", lang, reason=y_refuse))',
    ),
    (
        'notes.append("O eixo x vinha decrescente; inverti a ordem.")',
        'notes.append(msg("trace.x_descending", lang))',
    ),
    (
        'notes.append(f"{bad} ponto(s) fora de ordem no eixo x foram ignorados.")',
        'notes.append(msg("trace.x_out_of_order", lang, bad=bad))',
    ),
    (
        'notes.append(\n            "O cabeçalho declara exotérmico PARA CIMA (#EXO); inverti o sinal "\n            "para a convenção endotérmico-para-cima que a análise usa."\n        )',
        'notes.append(msg("trace.exo_up_inverted", lang))',
    ),
    (
        'raise TraceImportError(\n                f"O eixo x não é monotônico ({bad} de {len(diffs)} passos "\n                "decrescentes). Isto costuma indicar um método com várias "\n                "rampas; o PAT analisa uma rampa por vez."\n            )',
        'raise TraceImportError(\n                msg("trace.x_not_monotonic", lang, bad=bad, total=len(diffs))\n            )',
    ),
    # --- _apply_factor: as duas recusas de conversao de unidade ----------
    (
        'if factor is None:\n        return values, (\n            f"a coluna está em \'{unit}\', e converter para a unidade canônica "\n            "exige um dado que o arquivo não traz (por exemplo a massa da "\n            "amostra para um sinal absoluto em mW). Forneça o dado ou exporte "\n            "o sinal normalizado pela massa."\n        )',
        'if factor is None:\n        return values, msg("trace.axis.unit_unconvertible", lang, unit=unit)',
    ),
    (
        'return values, f"conversão \'{factor}\' não implementada"',
        'return values, msg("trace.axis.factor_unknown", lang, factor=factor)',
    ),
]

#: Assinaturas que passam a receber ``lang``.
ASSINATURAS_TRACE: list[tuple] = [
    ("def _decode(raw: bytes) -> str:", "def _decode(raw: bytes, lang: str = IDIOMA_ORIGEM) -> str:"),
    (
        "def _read_keyval_spectrum(p: Path, text: str) -> TraceFile:",
        "def _read_keyval_spectrum(p: Path, text: str, lang: str = IDIOMA_ORIGEM) -> TraceFile:",
    ),
    (
        "def _read_tri_as_trace_file(p: Path) -> TraceFile:",
        "def _read_tri_as_trace_file(p: Path, lang: str = IDIOMA_ORIGEM) -> TraceFile:",
    ),
    (
        "def read_trace_file(path: str | Path) -> TraceFile:",
        "def read_trace_file(path: str | Path, lang: str = IDIOMA_ORIGEM) -> TraceFile:",
    ),
    (
        "def _apply_factor(\n    values: list[float], factor: float | str | None, unit: str\n) -> tuple[list[float], str | None]:",
        "def _apply_factor(\n    values: list[float],\n    factor: float | str | None,\n    unit: str,\n    lang: str = IDIOMA_ORIGEM,\n) -> tuple[list[float], str | None]:",
    ),
    (
        "def resolve_trace(\n    tf: TraceFile,\n    x_role: str,\n    y_role: str,\n    *,\n    invert_for_endothermic_up: bool = False,\n) -> ResolvedTrace:",
        "def resolve_trace(\n    tf: TraceFile,\n    x_role: str,\n    y_role: str,\n    *,\n    invert_for_endothermic_up: bool = False,\n    lang: str = IDIOMA_ORIGEM,\n) -> ResolvedTrace:",
    ),
    # as chamadas internas
    ("text = _decode(raw)", "text = _decode(raw, lang)"),
    ("return _read_tri_as_trace_file(p)", "return _read_tri_as_trace_file(p, lang)"),
    ("return _read_keyval_spectrum(p, text)", "return _read_keyval_spectrum(p, text, lang)"),
    (
        'x_out, x_refuse = _apply_factor(x_vals, xc.factor, xc.unit or "")',
        'x_out, x_refuse = _apply_factor(x_vals, xc.factor, xc.unit or "", lang)',
    ),
    (
        'y_out, y_refuse = _apply_factor(y_vals, yc.factor, yc.unit or "")',
        'y_out, y_refuse = _apply_factor(y_vals, yc.factor, yc.unit or "", lang)',
    ),
    # o import do catalogo
    (
        "from app.core.trace_io import",  # sentinela -- nao existe; ver IMPORT abaixo
        "from app.core.trace_io import",
    ),
]

IMPORT_TRACE = (
    "from app.core.messages_i18n import IDIOMA_ORIGEM, msg, role_label"
)

# ---------------------------------------------------------------------------
# core/thermal.py -- 6 notas + a recusa da cristalinidade impossivel.
# ---------------------------------------------------------------------------
THERMAL_EDICOES: list[tuple] = [
    (
        'notes.append(\n            f"{unattributed:.1f} % of the mass loss is not part of any reported "\n            "step. It is either spread too gradually for its rate to stand out "\n            "against the noise, or spread across steps that overlap. Each "\n            "reported step is real; the list is not necessarily complete."\n        )',
        'notes.append(msg("tga.unattributed_loss", lang, unattributed=unattributed))',
    ),
    (
        'notes.append(\n                f"One step was detected, spanning {onset:.0f}-{end:.0f} C, but "\n                f"{early[0] - early[-1]:.1f} % of its loss happens in the first "\n                "quarter of that range. A weak event (moisture or solvent) is "\n                "probably riding on the main decomposition; it is included in "\n                "this step rather than reported separately because its rate "\n                "does not stand out against the noise."\n            )',
        'notes.append(\n                msg(\n                    "tga.one_step_early_loss",\n                    lang,\n                    onset=onset,\n                    end=end,\n                    early=early[0] - early[-1],\n                )\n            )',
    ),
    (
        'notes.append(\n            "Several steps were detected. T_max_rate names the fastest one, "\n            "which is not necessarily the first; use the step list for "\n            "per-step onsets."\n        )',
        'notes.append(msg("tga.several_steps", lang))',
    ),
    (
        'notes.append(\n            f"The trace ends at {residue:.2f} % mass, which is negative and "\n            "therefore not a physical residue. This is the instrument\'s own "\n            "value, reported unchanged; the run either drifted or was "\n            "mis-zeroed. Do not quote this as a residue."\n        )',
        'notes.append(msg("tga.residue_negative", lang, residue=residue))',
    ),
    (
        'notes.append(\n            f"The trace ends at {residue:.2f} % mass, above the starting "\n            "value. Buoyancy or a mis-zeroed balance is the usual cause; "\n            "treat the residue as unquantified."\n        )',
        'notes.append(msg("tga.residue_above_start", lang, residue=residue))',
    ),
    (
        'notes.append(\n            f"The trace starts at {start_pct:.1f} % rather than 100 %. It is "\n            "normalised to its own first point, so the percentage axis is "\n            "relative; a run that begins this far from 100 % has already lost "\n            "volatiles before the ramp."\n        )',
        'notes.append(msg("tga.start_below_100", lang, start_pct=start_pct))',
    ),
    (
        'result.crystallinity_refusal = (\n                            f"A cristalinidade calculada ({xc:.1f} %) é "\n                            f"fisicamente impossível: o ΔHm medido "\n                            f"({result.delta_Hm:.1f} J/g) excede a entalpia de "\n                            f"referência de 100 % cristalino "\n                            f"({ref_enthalpy_J_g:g} J/g). O valor é reportado "\n                            "para inspeção, mas não pode ser usado como "\n                            "resultado. Verifique se a referência é a deste "\n                            "polímero, se a amostra tem uma só fase cristalina, "\n                            "e se a linha de base da integração está correta."\n                        )',
        'result.crystallinity_refusal = msg(\n                            "dsc.impossible_crystallinity",\n                            lang,\n                            xc=xc,\n                            dhm=result.delta_Hm,\n                            ref=ref_enthalpy_J_g,\n                        )',
    ),
]

ASSINATURAS_THERMAL: list[tuple] = [
    (
        "def analyse_tga(\n    temperature: Sequence[float],\n    mass_pct: Sequence[float],\n    smooth_window: int = 11,\n    min_step_pct: float = 5.0,\n) -> TGAResult:",
        "def analyse_tga(\n    temperature: Sequence[float],\n    mass_pct: Sequence[float],\n    smooth_window: int = 11,\n    min_step_pct: float = 5.0,\n    lang: str = IDIOMA_ORIGEM,\n) -> TGAResult:",
    ),
    (
        "def analyse_dsc(\n    temperature: Sequence[float],\n    heat_flow: Sequence[float],\n    heating_rate: float | None = None,\n    ref_enthalpy_J_g: float | None = None,\n    smooth_window: int = 11,\n    polarity_known: bool = False,\n) -> DSCResult:",
        "def analyse_dsc(\n    temperature: Sequence[float],\n    heat_flow: Sequence[float],\n    heating_rate: float | None = None,\n    ref_enthalpy_J_g: float | None = None,\n    smooth_window: int = 11,\n    polarity_known: bool = False,\n    lang: str = IDIOMA_ORIGEM,\n) -> DSCResult:",
    ),
]

# ---------------------------------------------------------------------------
# api/v1/thermal.py -- 8 mensagens + o parametro ``lang`` nos endpoints.
# ---------------------------------------------------------------------------
API_EDICOES: list[tuple] = [
    (
        'preview.notes.append(f"não resolvido: {exc}")',
        'preview.notes.append(msg("trace.unresolved", lang, error=exc))',
    ),
    (
        'preview.notes.append(\n                f"O traço tem {ppd:.1f} ponto(s) por grau ({n} pontos em "\n                f"{span:.0f} graus). Abaixo de {_MIN_POINTS_PER_DEGREE:.0f} "\n                "pontos por grau o degrau de uma transição vítrea é mais "\n                "estreito que o espaçamento, e nenhum detector pode localizá-lo: "\n                "um valor de Tg reportado neste arquivo é ruído da linha de "\n                "base, não uma transição. O pico de fusão, que é largo, "\n                "continua utilizável."\n            )',
        'preview.notes.append(\n                msg(\n                    "trace.sparse_points_per_degree",\n                    lang,\n                    ppd=ppd,\n                    n=n,\n                    span=span,\n                    minimum=_MIN_POINTS_PER_DEGREE,\n                )\n            )',
    ),
    (
        'notes.append(\n                    f"Entalpia de referência de 100 % cristalino tomada do banco "\n                    f"interno para \'{entry.display_name}\' ({ref_key}): "\n                    f"{ref_value:g} J/g. Fonte: {ref_source}"\n                )',
        'notes.append(\n                    msg(\n                        "dsc.ref_enthalpy_from_db",\n                        lang,\n                        name=i18n.display_name(entry.key, lang, entry.display_name),\n                        key=ref_key,\n                        value=ref_value,\n                        source=ref_source,\n                    )\n                )',
    ),
    (
        'refusals.append(\n                    f"A amostra foi reconhecida como {entry.display_name}, que é "\n                    f"amorfo e não tem entalpia de referência: a cristalinidade "\n                    f"não se aplica. {entry.note or \'\'}".strip()\n                )',
        'refusals.append(\n                    msg(\n                        "dsc.amorphous_refused",\n                        lang,\n                        name=i18n.display_name(entry.key, lang, entry.display_name),\n                        note=i18n.note(entry.key, lang, entry.note) or "",\n                    ).strip()\n                )',
    ),
    (
        'refusals.append(\n                "O arquivo não declara a taxa de aquecimento, então a "\n                "cristalinidade não foi calculada. O ΔHm é reportado em "\n                "J/g apenas se a taxa for fornecida."\n            )',
        'refusals.append(msg("dsc.heating_rate_missing", lang))',
    ),
    (
        'refusals.append(\n                "Nenhuma entalpia de referência foi fornecida, e o nome da "\n                "amostra não foi reconhecido no banco interno "\n                "(GET /api/v1/thermal/crystallinity-references lista o que "\n                "existe). O ΔHm é reportado, mas sem cristalinidade."\n            )',
        'refusals.append(msg("dsc.ref_enthalpy_missing", lang))',
    ),
    (
        'refusals.append(\n            f"O traço tem {points_per_degree:.1f} ponto(s) por grau. Abaixo de "\n            f"{_MIN_POINTS_PER_DEGREE:.0f} nenhuma temperatura de transição "\n            "vítrea é localizável neste arquivo; um pico largo, como o de "\n            "fusão, continua utilizável."\n        )',
        'refusals.append(\n            msg(\n                "trace.sparse_tg_refused",\n                lang,\n                ppd=points_per_degree,\n                minimum=_MIN_POINTS_PER_DEGREE,\n            )\n        )',
    ),
    (
        'refusals.append(\n                "Os campos "\n                + ", ".join(f"\'{k}\'" for k in removed)\n                + " foram omitidos por não serem localizáveis neste arquivo."\n            )',
        'refusals.append(\n                msg(\n                    "trace.fields_omitted",\n                    lang,\n                    fields=", ".join(f"\'{k}\'" for k in removed),\n                )\n            )',
    ),
    # --- o parametro lang nos endpoints ---------------------------------
    (
        'async def analyse_trace_endpoint(\n    file: UploadFile = File(\n        ..., description="A trace file as the instrument wrote it."\n    ),\n    target: str = Form(\n        "dsc", description="Which analysis to run: \'dsc\' or \'tga\'."\n    ),',
        'async def analyse_trace_endpoint(\n    file: UploadFile = File(\n        ..., description="A trace file as the instrument wrote it."\n    ),\n    target: str = Form(\n        "dsc", description="Which analysis to run: \'dsc\' or \'tga\'."\n    ),\n    lang: str = Form(\n        "pt",\n        description=(\n            "Language for the refusal and warning prose (pt, en, es). "\n            "Unknown codes fall back to the source language."\n        ),\n    ),',
    ),
    (
        'async def import_trace_endpoint(\n    file: UploadFile = File(\n        ..., description="A trace file as the instrument wrote it."\n    ),\n    target: str = Form(\n        "dsc",\n        description=(\n            "Which analysis the file is for: \'dsc\' (temperature + heat flow), "\n            "\'tga\' (temperature + mass)."\n        ),\n    ),',
        'async def import_trace_endpoint(\n    file: UploadFile = File(\n        ..., description="A trace file as the instrument wrote it."\n    ),\n    target: str = Form(\n        "dsc",\n        description=(\n            "Which analysis the file is for: \'dsc\' (temperature + heat flow), "\n            "\'tga\' (temperature + mass)."\n        ),\n    ),\n    lang: str = Form(\n        "pt",\n        description=(\n            "Language for the refusal and warning prose (pt, en, es). "\n            "Unknown codes fall back to the source language."\n        ),\n    ),',
    ),
    ("tf = read_trace_file(tmp_path)", "tf = read_trace_file(tmp_path, lang)", 2),
    (
        "resolved = resolve_trace(\n            tf, x_role, y_role, invert_for_endothermic_up=(target_key == \"dsc\")\n        )",
        "resolved = resolve_trace(\n            tf,\n            x_role,\n            y_role,\n            invert_for_endothermic_up=(target_key == \"dsc\"),\n            lang=lang,\n        )",
        2,
    ),
    (
        "r = analyse_tga(resolved.x, resolved.y)",
        "r = analyse_tga(resolved.x, resolved.y, lang=lang)",
    ),
    (
        "r = analyse_dsc(\n            resolved.x,\n            resolved.y,\n            heating_rate=resolved.heating_rate,\n            ref_enthalpy_J_g=ref_value,",
        "r = analyse_dsc(\n            resolved.x,\n            resolved.y,\n            heating_rate=resolved.heating_rate,\n            ref_enthalpy_J_g=ref_value,\n            lang=lang,",
    ),
    (
        "r = analyse_tga(\n            payload.temperature, payload.mass_pct, smooth_window=payload.smooth_window\n        )",
        "r = analyse_tga(\n            payload.temperature,\n            payload.mass_pct,\n            smooth_window=payload.smooth_window,\n            lang=payload.lang,\n        )",
    ),
    (
        "r = analyse_dsc(\n            payload.temperature,\n            payload.heat_flow,\n            heating_rate=payload.heating_rate,\n            ref_enthalpy_J_g=payload.ref_enthalpy_J_g,\n            smooth_window=payload.smooth_window,",
        "r = analyse_dsc(\n            payload.temperature,\n            payload.heat_flow,\n            heating_rate=payload.heating_rate,\n            ref_enthalpy_J_g=payload.ref_enthalpy_J_g,\n            smooth_window=payload.smooth_window,\n            lang=payload.lang,",
    ),
    (
        "from app.core.trace_io import TraceImportError, read_trace_file, resolve_trace",
        "from app.core import crystallinity_ref_i18n as i18n\nfrom app.core.messages_i18n import msg\nfrom app.core.trace_io import TraceImportError, read_trace_file, resolve_trace",
    ),
]

IMPORT_THERMAL = "from app.core.messages_i18n import IDIOMA_ORIGEM, msg"


def _aplicar(caminho: Path, edicoes: list[tuple]) -> list[str]:
    """Aplica cada par (antigo, novo[, n_esperado]); devolve os problemas.

    O terceiro elemento diz quantas ocorrencias se esperam. Existe porque a
    mesma correcao serve dois sitios -- ``/import`` e ``/analyse`` chamam
    ``read_trace_file`` e ``resolve_trace`` da mesma maneira -- e recusar
    qualquer contagem diferente de 1 obrigaria a duplicar o par, deixando os
    dois livres para divergir depois.
    """
    texto = caminho.read_text(encoding="utf-8")
    problemas: list[str] = []
    for entrada in edicoes:
        antigo, novo = entrada[0], entrada[1]
        esperado = entrada[2] if len(entrada) > 2 else 1
        if antigo == novo:
            continue
        # "Ja aplicado" verifica-se pelo TEXTO NOVO, nao pelo antigo: nos
        # endpoints o novo contem o antigo (acrescenta-se um campo), entao
        # contar o antigo continua a dar 1 depois de aplicado e a segunda
        # execucao duplicava o parametro -- foi o que aconteceu, e so o
        # compilador apanhou ("duplicate argument 'lang'").
        if novo in texto:
            continue
        n = texto.count(antigo)
        if n == esperado:
            texto = texto.replace(antigo, novo)
        else:
            problemas.append(
                f"{caminho.name}: {n} ocorrencia(s), esperava {esperado} -> "
                f"{antigo.splitlines()[0][:80]!r}"
            )
    if not problemas:
        caminho.write_text(texto, encoding="utf-8")
    return problemas


def main() -> int:
    problemas: list[str] = []

    # --- trace_io.py -----------------------------------------------------
    texto = TRACE.read_text(encoding="utf-8")
    if IMPORT_TRACE not in texto:
        # Junto dos outros imports de app.core, para nao ficar solto.
        m = re.search(r"^from app\.core\.bridge_config import .*$", texto, re.M)
        if m:
            texto = texto[: m.end()] + "\n" + IMPORT_TRACE + texto[m.end():]
        else:
            m = re.search(r"^(from __future__ import annotations)$", texto, re.M)
            if not m:
                problemas.append("trace_io.py: nao achei onde meter o import do catalogo")
            else:
                texto = texto[: m.end()] + "\n\n" + IMPORT_TRACE + texto[m.end():]
        TRACE.write_text(texto, encoding="utf-8")

    problemas += _aplicar(TRACE, TRACE_EDICOES)
    problemas += _aplicar(TRACE, ASSINATURAS_TRACE)

    # _ROLE_LABEL deixa de ser usado; o dicionario sai para nao ficar codigo
    # morto a sugerir que os rotulos sao de um so idioma.
    texto = TRACE.read_text(encoding="utf-8")
    if "_ROLE_LABEL = {" in texto:
        texto = re.sub(
            r"#: Rolos nomeados, para mensagens legíveis\.\n_ROLE_LABEL = \{.*?\n\}\n\n",
            "",
            texto,
            flags=re.S,
        )
        TRACE.write_text(texto, encoding="utf-8")

    if problemas:
        print("PROBLEMAS:")
        for p in problemas:
            print("  ", p)
        return 1
    print("trace_io.py: ok")

    # --- core/thermal.py -------------------------------------------------
    texto = THERMAL.read_text(encoding="utf-8")
    if IMPORT_THERMAL not in texto:
        m = re.search(r"^from app\.core\.ingest import .*$", texto, re.M)
        if m:
            texto = texto[: m.end()] + "\n" + IMPORT_THERMAL + texto[m.end():]
        else:
            m = re.search(r"^(from __future__ import annotations)$", texto, re.M)
            if not m:
                problemas.append("thermal.py: nao achei onde meter o import do catalogo")
            else:
                texto = texto[: m.end()] + "\n\n" + IMPORT_THERMAL + texto[m.end():]
        THERMAL.write_text(texto, encoding="utf-8")

    problemas += _aplicar(THERMAL, THERMAL_EDICOES)
    problemas += _aplicar(THERMAL, ASSINATURAS_THERMAL)
    if problemas:
        print("PROBLEMAS:")
        for p in problemas:
            print("  ", p)
        return 1
    print("core/thermal.py: ok")

    # --- api/v1/thermal.py -----------------------------------------------
    problemas += _aplicar(API, API_EDICOES)
    if problemas:
        print("PROBLEMAS:")
        for p in problemas:
            print("  ", p)
        return 1
    print("api/v1/thermal.py: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
