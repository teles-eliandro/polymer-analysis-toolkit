/** Mechanical module: tensile properties from a stress-strain curve. */

import React, { useState } from 'react';
import Plot from 'react-plotly.js';
import { mechanicalApi, describeError } from '../services/api';
import { useI18n } from '../i18n/I18nContext';
import { Stat, StatGrid, ErrorBanner, parseTwoColumns } from './ui';

export default function MechanicalPanel() {
  const { t } = useI18n();
  const [text, setText] = useState('');
  const [windowLo, setWindowLo] = useState('');
  const [windowHi, setWindowHi] = useState('');
  const [result, setResult] = useState(null);
  const [input, setInput] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const run = async () => {
    setError('');
    setResult(null);
    const { x, y } = parseTwoColumns(text);
    if (x.length < 4 || y.length < 4) {
      setError(t('error.tooFewPoints', { n: 4 }));
      return;
    }
    if (x.length !== y.length) {
      setError(t('error.mismatched'));
      return;
    }
    setLoading(true);
    try {
      const useWindow = windowLo !== '' && windowHi !== '';
      const res = await mechanicalApi.tensile(
        x,
        y,
        useWindow ? [Number(windowLo), Number(windowHi)] : null,
      );
      setResult(res.data);
      setInput({ x, y });
    } catch (err) {
      setError(describeError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <h2>{t('mechanical.title')}</h2>
      <p className="intro">{t('mechanical.intro')}</p>

      <div className="card">
        <label className="field">
          <span className="field-label">
            {t('mechanical.strain')} / {t('mechanical.stress')}
          </span>
          <textarea
            rows={8}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={'0\t0\n0.5\t10\n1\t20\n2\t40\n5\t100'}
          />
          <span className="field-hint">
            One row per point: strain_percent stress_MPa. The modulus is taken from the
            initial linear region unless a window is given below.
          </span>
        </label>

        <div className="two-col">
          <label className="field">
            <span className="field-label">
              {t('mechanical.window')} — min (%) <em>({t('common.optional')})</em>
            </span>
            <input
              type="number"
              step="0.1"
              value={windowLo}
              onChange={(e) => setWindowLo(e.target.value)}
            />
          </label>
          <label className="field">
            <span className="field-label">
              {t('mechanical.window')} — max (%)
            </span>
            <input
              type="number"
              step="0.1"
              value={windowHi}
              onChange={(e) => setWindowHi(e.target.value)}
            />
          </label>
        </div>

        <button type="button" className="submit-btn" disabled={loading} onClick={run}>
          {loading ? t('common.calculating') : t('common.calculate')}
        </button>
      </div>

      <ErrorBanner message={error} />

      {result ? (
        <section className="results">
          <h3>{t('common.results')}</h3>
          <StatGrid>
            <Stat
              label={t('mechanical.modulus')}
              value={result.E_MPa}
              unit="MPa"
              note={t('mechanical.modulusNote')}
            />
            <Stat label={t('mechanical.stressMax')} value={result.stress_max_MPa} unit="MPa" />
            <Stat label={t('mechanical.strainMax')} value={result.strain_max_pct} unit="%" />
            <Stat label={t('mechanical.stressBreak')} value={result.stress_break_MPa} unit="MPa" />
            <Stat label={t('mechanical.strainBreak')} value={result.strain_break_pct} unit="%" />
            {result.stress_yield_MPa !== null && result.stress_yield_MPa !== undefined ? (
              <Stat label={t('mechanical.stressYield')} value={result.stress_yield_MPa} unit="MPa" />
            ) : null}
            {result.strain_yield_pct !== null && result.strain_yield_pct !== undefined ? (
              <Stat label={t('mechanical.strainYield')} value={result.strain_yield_pct} unit="%" />
            ) : null}
            <Stat
              label={t('mechanical.toughness')}
              value={result.toughness_MJ_m3}
              unit="MJ/m³"
              note={t('mechanical.toughnessNote')}
            />
          </StatGrid>

          <div className="flags">
            {result.modulus_window ? (
              <span className="flag">
                {t('mechanical.window')}: {result.modulus_window[0]}–{result.modulus_window[1]} %
              </span>
            ) : null}
            <span className={`flag ${result.yielded ? 'on' : ''}`}>
              {t('mechanical.yielded')}: {result.yielded ? '✓' : '—'}
            </span>
            <span className={`flag ${result.brittle ? 'on' : ''}`}>
              {t('mechanical.brittle')}: {result.brittle ? '✓' : '—'}
            </span>
          </div>

          {input ? (
            <div className="plot">
              <Plot
                data={[
                  {
                    x: input.x,
                    y: input.y,
                    type: 'scatter',
                    mode: 'lines',
                    name: t('mechanical.curve'),
                    line: { color: '#2b7de9' },
                  },
                ]}
                layout={{
                  height: 380,
                  margin: { l: 60, r: 20, t: 40, b: 50 },
                  xaxis: { title: t('mechanical.strain') },
                  yaxis: { title: t('mechanical.stress') },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
