/** Thermal module: TGA and DSC trace analysis. */

import React, { useState } from 'react';
import Plot from 'react-plotly.js';
import { thermalApi, describeError } from '../services/api';
import { useI18n } from '../i18n/I18nContext';
import { Stat, StatGrid, DataTable, ErrorBanner, parseTwoColumns } from './ui';
import FileDrop from './FileDrop';
import { Formula, FormulaDisclosure } from './Formula';

function TraceInput({ label, hint, placeholder, value, onChange }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <textarea
        rows={7}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
      {hint ? <span className="field-hint">{hint}</span> : null}
    </label>
  );
}

export default function ThermalPanel() {
  const { t } = useI18n();
  const [mode, setMode] = useState('tga');

  const [tgaText, setTgaText] = useState('');
  const [dscText, setDscText] = useState('');
  const [heatingRate, setHeatingRate] = useState('10');
  const [refEnthalpy, setRefEnthalpy] = useState('');

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fileNote, setFileNote] = useState('');

  /**
   * A file fills the same textarea the paste box uses, so the two routes
   * cannot drift apart: whatever the parser accepts by hand, it accepts from
   * a file. Nothing is uploaded here — only the parsed numbers reach the API.
   */
  const loadFile = (text, file) => {
    setError('');
    setFileNote('');
    if (!file) {
      if (mode === 'tga') setTgaText('');
      else setDscText('');
      return;
    }
    const { x, y } = parseTwoColumns(text);
    if (x.length === 0) {
      setError(t('file.noPoints', { name: file.name }));
      return;
    }
    const rebuilt = x.map((v, i) => `${v}\t${y[i]}`).join('\n');
    if (mode === 'tga') setTgaText(rebuilt);
    else setDscText(rebuilt);
    setFileNote(
      t('file.loaded', { name: file.name, n: x.length }) +
        (x.length < 10 ? ` ${t('thermal.shortTraceWarning')}` : ''),
    );
  };

  const run = async () => {
    setError('');
    setResult(null);
    const text = mode === 'tga' ? tgaText : dscText;
    const { x, y } = parseTwoColumns(text);
    const minPoints = 3;
    if (x.length < minPoints || y.length < minPoints) {
      setError(t('error.tooFewPoints', { n: minPoints }));
      return;
    }
    if (x.length !== y.length) {
      setError(t('error.mismatched'));
      return;
    }
    setLoading(true);
    try {
      if (mode === 'tga') {
        const res = await thermalApi.tga(x, y);
        setResult({ kind: 'tga', data: res.data });
      } else {
        const res = await thermalApi.dsc(x, y, {
          heatingRate: heatingRate === '' ? null : Number(heatingRate),
          refEnthalpy: refEnthalpy === '' ? null : Number(refEnthalpy),
        });
        setResult({ kind: 'dsc', data: res.data });
      }
    } catch (err) {
      setError(describeError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <h2>{t('thermal.title')}</h2>
      <p className="intro">{t('thermal.intro')}</p>

      <div className="tabs">
        <button
          type="button"
          className={mode === 'tga' ? 'tab active' : 'tab'}
          onClick={() => {
            setMode('tga');
            setResult(null);
            setError('');
          }}
        >
          {t('thermal.tga')}
        </button>
        <button
          type="button"
          className={mode === 'dsc' ? 'tab active' : 'tab'}
          onClick={() => {
            setMode('dsc');
            setResult(null);
            setError('');
          }}
        >
          {t('thermal.dsc')}
        </button>
      </div>

      <div className="card">
        <FileDrop
          onText={loadFile}
          onError={setError}
          hint={t('file.accepted', { list: 'CSV, TSV, TXT, DAT, ASC' })}
        />
        {fileNote ? (
          <p className="preview-meta" role="status">
            {fileNote}
          </p>
        ) : null}
        {mode === 'tga' ? (
          <TraceInput
            label={`${t('thermal.temperature')} / ${t('thermal.massPct')}`}
            hint="One row per point: temperature mass_percent. Comma, tab or space separated."
            placeholder={'30\t100\n100\t99\n350\t85\n500\t40\n800\t10'}
            value={tgaText}
            onChange={setTgaText}
          />
        ) : (
          <>
            <TraceInput
              label={`${t('thermal.temperature')} / ${t('thermal.heatFlow')}`}
              hint="One row per point: temperature heat_flow_w_per_g. Endothermic up."
              placeholder={'0\t0.30\n100\t0.85\n165\t3.30\n250\t0.35'}
              value={dscText}
              onChange={setDscText}
            />
            <div className="two-col">
              <label className="field">
                <span className="field-label">{t('thermal.heatingRate')}</span>
                <input
                  type="number"
                  step="1"
                  min="0.1"
                  value={heatingRate}
                  onChange={(e) => setHeatingRate(e.target.value)}
                />
                <span className="field-hint">{t('thermal.heatingRateHint')}</span>
              </label>
              <label className="field">
                <span className="field-label">
                  {t('thermal.refEnthalpy')} <em>({t('common.optional')})</em>
                </span>
                <input
                  type="number"
                  step="1"
                  min="0.1"
                  value={refEnthalpy}
                  placeholder="e.g. 290"
                  onChange={(e) => setRefEnthalpy(e.target.value)}
                />
                <span className="field-hint">{t('thermal.refEnthalpyHint')}</span>
              </label>
            </div>
          </>
        )}

        <button type="button" className="submit-btn" disabled={loading} onClick={run}>
          {loading ? t('common.calculating') : t('common.calculate')}
        </button>
      </div>

      <ErrorBanner message={error} />

      {result?.kind === 'tga' ? <TgaResults data={result.data} t={t} /> : null}
      {result?.kind === 'dsc' ? <DscResults data={result.data} t={t} /> : null}

      <FormulaDisclosure>
        <Formula
          name={t('thermal.f.dtg.name')}
          expression="DTG(T) = −dm/dT   (%/°C)"
          symbols={[
            { symbol: 'm', meaning: t('thermal.f.dtg.m') },
            { symbol: 'T', meaning: t('thermal.f.dtg.T') },
          ]}
          note={t('thermal.f.dtg.note')}
          reference="ASTM E1131-20, Standard Test Method for Compositional Analysis by Thermogravimetry. The DTG is the first derivative of the mass loss curve; its maximum is the temperature of greatest decomposition rate."
        />
        <Formula
          name={t('thermal.f.td.name')}
          expression="Td(x%) : the T where m(T) = 100 − x   (linear interpolation)"
          symbols={[
            { symbol: 'x', meaning: t('thermal.f.td.x') },
            { symbol: 'm', meaning: t('thermal.f.td.m') },
          ]}
          note={t('thermal.f.td.note')}
          reference="ISO 11358-1:2022, Plastics — Thermogravimetry (TG) of polymers — Part 1: General principles. Defines the onset temperature by the mass-loss criterion and the extrapolated tangent."
        />
        <Formula
          name={t('thermal.f.res.name')}
          expression="residue (%) = m(T_final)"
          note={t('thermal.f.res.note')}
          reference="ISO 11358-1:2022 (residue determination). The residue includes any inorganic filler, ash or char, so it is an upper bound on the filler content, not a measurement of it."
        />
        <Formula
          name={t('thermal.f.smooth.name')}
          expression="m_smooth(T) = (1/w) Σ m(T_i)   over a window of w points, edge-padded"
          symbols={[{ symbol: 'w', meaning: t('thermal.f.smooth.w') }]}
          note={t('thermal.f.smooth.note')}
        />
        <Formula
          name={t('thermal.f.uniform.name')}
          expression="DTG computed on a uniform 1 °C grid after interpolation"
          note={t('thermal.f.uniform.note')}
        />
        <Formula
          name={t('thermal.f.dscpeak.name')}
          expression="ΔHm = (1/β) ∫ [q(T) − baseline(T)] dT"
          symbols={[
            { symbol: 'ΔHm', meaning: t('thermal.f.dscpeak.Hm') },
            { symbol: 'q', meaning: t('thermal.f.dscpeak.q') },
            { symbol: 'β', meaning: t('thermal.f.dscpeak.beta') },
          ]}
          note={t('thermal.f.dscpeak.note')}
          reference="ASTM E793-06(2018), Standard Test Method for Enthalpies of Fusion and Crystallization by DSC. The peak area is bounded by a baseline drawn between the flanks of the transition."
        />
        <Formula
          name={t('thermal.f.xc.name')}
          expression="Xc (%) = 100 · ΔHm / ΔHm°"
          symbols={[
            { symbol: 'ΔHm', meaning: t('thermal.f.xc.Hm') },
            { symbol: 'ΔHm°', meaning: t('thermal.f.xc.Hm0') },
          ]}
          note={t('thermal.f.xc.note')}
          reference="Kong & Hay, 'The measurement of the crystallinity of polymers by DSC', Polymer 43 (2002) 3873–3878. Xc from DSC is a mass fraction, and is only as good as ΔHm°."
        />
      </FormulaDisclosure>
    </div>
  );
}

function TgaResults({ data, t }) {
  const stepRows = (data.steps || []).map((s, i) => ({ ...s, idx: i + 1 }));
  const traces = [
    {
      x: data.temperature,
      y: data.mass_pct,
      type: 'scatter',
      mode: 'lines',
      name: t('thermal.trace'),
      line: { color: '#2b7de9' },
      yaxis: 'y',
    },
    {
      x: data.temperature,
      y: data.dtg,
      type: 'scatter',
      mode: 'lines',
      name: t('thermal.dtg'),
      line: { color: '#d9534f', dash: 'dot' },
      yaxis: 'y2',
    },
  ];
  return (
    <section className="results">
      <h3>{t('common.results')}</h3>
      <StatGrid>
        <Stat label={t('thermal.Td5')} value={data.Td_5pct} unit="°C" />
        <Stat label={t('thermal.Td10')} value={data.Td_10pct} unit="°C" />
        <Stat
          label={t('thermal.TmaxRate')}
          value={data.T_max_rate}
          unit="°C"
          note={t('thermal.TmaxRateNote')}
        />
        <Stat label={t('thermal.residue')} value={data.residue_pct} unit="%" />
      </StatGrid>

      {stepRows.length > 0 ? (
        <>
          <h4>{t('thermal.steps')}</h4>
          <DataTable
            columns={[
              { key: 'onset_C', label: 'onset (°C)', digits: 1 },
              { key: 'end_C', label: 'end (°C)', digits: 1 },
              { key: 'loss_pct', label: 'loss (%)', digits: 1 },
            ]}
            rows={stepRows}
          />
        </>
      ) : null}

      <div className="plot">
        <Plot
          data={traces}
          layout={{
            height: 380,
            margin: { l: 60, r: 60, t: 40, b: 50 },
            xaxis: { title: t('thermal.temperature') },
            yaxis: { title: t('thermal.massPct') },
            yaxis2: {
              title: 'DTG (%/°C)',
              overlaying: 'y',
              side: 'right',
              showgrid: false,
            },
            legend: { orientation: 'h', y: -0.2 },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
        />
      </div>
    </section>
  );
}

function DscResults({ data, t }) {
  return (
    <section className="results">
      <h3>{t('common.results')}</h3>
      <StatGrid>
        <Stat
          label={t('thermal.Tg')}
          value={data.Tg}
          unit="°C"
          note={t('thermal.TgNote')}
        />
        <Stat label={t('thermal.Tm')} value={data.Tm} unit="°C" />
        <Stat label={t('thermal.deltaHm')} value={data.delta_Hm} unit="J/g" />
        <Stat label={t('thermal.deltaCp')} value={data.delta_cp} unit="J/(g·K)" />
        {data.crystallinity_pct !== null && data.crystallinity_pct !== undefined ? (
          <Stat
            label={t('thermal.crystallinity')}
            value={data.crystallinity_pct}
            unit="%"
            note={t('thermal.crystallinityNote')}
          />
        ) : null}
      </StatGrid>

      <div className="plot">
        <Plot
          data={[
            {
              x: data.temperature,
              y: data.heat_flow,
              type: 'scatter',
              mode: 'lines',
              name: t('thermal.trace'),
              line: { color: '#2b7de9' },
            },
          ]}
          layout={{
            height: 380,
            margin: { l: 60, r: 20, t: 40, b: 50 },
            xaxis: { title: t('thermal.temperature') },
            yaxis: { title: t('thermal.heatFlow') },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
        />
      </div>
    </section>
  );
}
