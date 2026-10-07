/** Rheology module: oscillatory shear frequency sweep. */

import React, { useState } from 'react';
import Plot from 'react-plotly.js';
import { rheologyApi, describeError } from '../services/api';
import { useI18n } from '../i18n/I18nContext';
import { Stat, StatGrid, ErrorBanner } from './ui';
import FileDrop from './FileDrop';
import { Formula, FormulaDisclosure } from './Formula';

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
  const [fileNote, setFileNote] = useState('');

  /**
   * A rheometer export is usually three columns, so the file is
   * re-serialised as tab-separated triples rather than routed through the
   * two-column parser. Only the numbers are sent.
   */
  const loadFile = (raw, file) => {
    setError('');
    setFileNote('');
    if (!file) {
      setText('');
      return;
    }
    const { w, gp, gpp } = parseThreeColumns(raw);
    if (w.length === 0) {
      setError(t('file.noPoints', { name: file.name }));
      return;
    }
    setText(w.map((v, i) => `${v}\t${gp[i]}\t${gpp[i]}`).join('\n'));
    setFileNote(t('file.loaded', { name: file.name, n: w.length }));
  };

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

      <FormulaDisclosure>
        <Formula
          name={t('rheo.f.moduli.name')}
          expression="G' = (s0/g0)cos d      G'' = (s0/g0)sin d"
          symbols={[
            { symbol: "G'", meaning: t('rheo.f.moduli.Gp') },
            { symbol: "G''", meaning: t('rheo.f.moduli.Gpp') },
            { symbol: 'd', meaning: t('rheo.f.moduli.delta') },
          ]}
          note={t('rheo.f.moduli.note')}
          reference="ISO 6721-10:2015, Plastics - Determination of dynamic mechanical properties - Part 10: Complex shear viscosity using a parallel-plate oscillatory rheometer."
        />
        <Formula
          name={t('rheo.f.tan.name')}
          expression="tan d = G'' / G'"
          note={t('rheo.f.tan.note')}
          reference="ASTM D4440-15, Standard Test Method for Plastics: Dynamic Mechanical Properties: Melt Rheology."
        />
        <Formula
          name={t('rheo.f.gel.name')}
          expression="gel point: the w where |G' - G''| / G' <= tolerance,  with G' > G''"
          note={t('rheo.f.gel.note')}
          reference="Winter & Chambon, Analysis of linear viscoelasticity of a crosslinking polymer at the gel point, Journal of Rheology 30 (1986) 367-382. The rigorous criterion is a power law in both moduli; crossing of the two is a practical approximation."
        />
        <Formula
          name={t('rheo.f.cross.name')}
          expression="cross-over: G' = G''  ->  tan d = 1"
          note={t('rheo.f.cross.note')}
        />
      </FormulaDisclosure>
    </div>
  );
}
