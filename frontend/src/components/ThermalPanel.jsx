/** Thermal module: TGA and DSC trace analysis. */

import React, { useState } from 'react';
import Plot from 'react-plotly.js';
import { thermalApi, describeError } from '../services/api';
import { useI18n } from '../i18n/I18nContext';
import { Stat, StatGrid, DataTable, ErrorBanner, parseTwoColumns } from './ui';

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
