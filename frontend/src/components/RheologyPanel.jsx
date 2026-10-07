/** Rheology module: oscillatory shear frequency sweep. */

import React, { useState } from 'react';
import Plot from 'react-plotly.js';
import { rheologyApi, describeError } from '../services/api';
import { useI18n } from '../i18n/I18nContext';
import { Stat, StatGrid, ErrorBanner, parseTwoColumns } from './ui';

function parseThreeColumns(text) {
  const w = [];
  const gp = [];
  const gpp = [];
  String(text)
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0 && !l.startsWith('#'))
    .forEach((line) => {
      if (!/\d/.test(line)) return;
      const parts = line.split(/[\s,;\t]+/).filter((p) => p.length > 0);
      if (parts.length < 3) return;
      const nums = parts.slice(0, 3).map((s) => {
        const cleaned = s.replace(/[^0-9eE+\-.]/g, '');
        const v = Number(cleaned.includes(',') ? cleaned.replace(',', '.') : cleaned);
        return Number.isFinite(v) ? v : null;
      });
      if (nums.some((v) => v === null)) return;
      w.push(nums[0]);
      gp.push(nums[1]);
      gpp.push(nums[2]);
    });
  return { w, gp, gpp };
}

export default function RheologyPanel() {
  const { t } = useI18n();
  const [text, setText] = useState('');
  const [gelTolerance, setGelTolerance] = useState('0.15');
  const [result, setResult] = useState(null);
  const [input, setInput] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const run = async () => {
    setError('');
    setResult(null);
    const { w, gp, gpp } = parseThreeColumns(text);
    if (w.length < 4) {
      setError(t('error.tooFewPoints', { n: 4 }));
      return;
    }
    setLoading(true);
    try {
      const res = await rheologyApi.sweep(w, gp, gpp, Number(gelTolerance) || 0.15);
      setResult(res.data);
      setInput({ w, gp, gpp });
    } catch (err) {
      setError(describeError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <h2>{t('rheology.title')}</h2>
      <p className="intro">{t('rheology.intro')}</p>

      <div className="card">
        <label className="field">
          <span className="field-label">
            {t('rheology.omega')} / {t('rheology.gPrime')} / {t('rheology.gDoublePrime')}
          </span>
          <textarea
            rows={8}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={'0.1\t900\t9000\n1\t9000\t9000\n10\t90000\t9000'}
          />
          <span className="field-hint">
            One row per point: frequency G_prime G_double_prime. All values must be positive.
          </span>
        </label>

        <label className="field">
          <span className="field-label">Gel tolerance (relative tan δ spread)</span>
          <input
            type="number"
            step="0.01"
            min="0.001"
            value={gelTolerance}
            onChange={(e) => setGelTolerance(e.target.value)}
          />
          <span className="field-hint">
            How flat tan(δ) must be across the sweep to flag a Winter-Chambon critical gel.
          </span>
        </label>

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
              label={t('rheology.crossover')}
              value={result.cross_over_freq}
              unit="rad/s"
              note={t('rheology.crossoverNote')}
            />
            <Stat label={t('rheology.relaxation')} value={result.relaxation_time_s} unit="s" />
            <Stat
              label={t('rheology.plateau')}
              value={result.plateau_modulus_G0}
              unit="Pa"
              note={t('rheology.plateauNote')}
            />
            <Stat label={t('rheology.zeroShear')} value={result.zero_shear_viscosity_Pas} unit="Pa·s" />
          </StatGrid>

          <h4>{t('rheology.slopes')}</h4>
          <p className="field-hint">{t('rheology.slopesNote')}</p>
          <StatGrid>
            <Stat label="d log G' / d log ω" value={result.terminal_slope_Gprime} />
            <Stat label="d log G'' / d log ω" value={result.terminal_slope_Gpp} />
          </StatGrid>

          <div className="flags">
            <span className={`flag ${result.gel_point_detected ? 'on' : ''}`}>
              {t('rheology.gel')}:{' '}
              {result.gel_point_detected ? t('rheology.gelYes') : t('rheology.gelNo')}
            </span>
            <span className="flag">
              {result.solid_like_at_low_freq ? t('rheology.solidLike') : t('rheology.liquidLike')}
            </span>
          </div>

          {input ? (
            <div className="plot">
              <Plot
                data={[
                  {
                    x: input.w,
                    y: input.gp,
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: "G'",
                    line: { color: '#2b7de9' },
                  },
                  {
                    x: input.w,
                    y: input.gpp,
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: "G''",
                    line: { color: '#d9534f' },
                  },
                ]}
                layout={{
                  title: t('rheology.masterCurve'),
                  height: 380,
                  margin: { l: 60, r: 20, t: 40, b: 50 },
                  xaxis: { title: t('rheology.omega'), type: 'log' },
                  yaxis: { title: "G', G'' (Pa)", type: 'log' },
                  legend: { orientation: 'h', y: -0.2 },
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
