/** Structure module: XRD pattern indexing and FTIR band assignment. */

import React, { useState } from 'react';
import Plot from 'react-plotly.js';
import { structureApi, describeError } from '../services/api';
import { useI18n } from '../i18n/I18nContext';
import { Stat, StatGrid, DataTable, ErrorBanner, Disclosure, parseTwoColumns } from './ui';
import FileDrop from './FileDrop';
import { Formula, FormulaDisclosure } from './Formula';

// The API rejects shorter traces with a 422, so the limit is enforced here too
// and the user gets a readable message instead of a validation dump.
const MIN_XRD_POINTS = 10;
const MIN_FTIR_POINTS = 10;

function TraceInput({ label, hint, placeholder, value, onChange, rows = 8 }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <textarea rows={rows} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
      {hint ? <span className="field-hint">{hint}</span> : null}
    </label>
  );
}

export default function StructurePanel() {
  const { t } = useI18n();
  const [mode, setMode] = useState('xrd');

  const [xrdText, setXrdText] = useState('');
  const [ftirText, setFtirText] = useState('');
  const [wavelength, setWavelength] = useState('1.5406');
  const [kFactor, setKFactor] = useState('0.9');
  const [instFwhm, setInstFwhm] = useState('0.0');
  const [tolerance, setTolerance] = useState('0.0');

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fileNote, setFileNote] = useState('');

  /** A file fills the same textarea the paste box uses, so both routes share
   *  one parser and cannot drift apart. Only the numbers are sent. */
  const loadFile = (text, file) => {
    setError('');
    setFileNote('');
    const setText = mode === 'xrd' ? setXrdText : setFtirText;
    if (!file) {
      setText('');
      return;
    }
    const { x, y } = parseTwoColumns(text);
    if (x.length === 0) {
      setError(t('file.noPoints', { name: file.name }));
      return;
    }
    setText(x.map((v, i) => `${v}\t${y[i]}`).join('\n'));
    setFileNote(t('file.loaded', { name: file.name, n: x.length }));
  };

  const run = async () => {
    setError('');
    setResult(null);
    const text = mode === 'xrd' ? xrdText : ftirText;
    const minPoints = mode === 'xrd' ? MIN_XRD_POINTS : MIN_FTIR_POINTS;
    const { x, y } = parseTwoColumns(text);
    if (x.length !== y.length) {
      setError(t('error.mismatched'));
      return;
    }
    if (x.length < minPoints) {
      setError(t('error.tooFewPoints', { n: minPoints }));
      return;
    }
    setLoading(true);
    try {
      if (mode === 'xrd') {
        const res = await structureApi.xrd(x, y, {
          wavelengthAngstrom: wavelength === '' ? undefined : Number(wavelength),
          K: kFactor === '' ? undefined : Number(kFactor),
          instrumentalFwhmDeg: instFwhm === '' ? undefined : Number(instFwhm),
        });
        setResult({ kind: 'xrd', data: res.data });
      } else {
        const res = await structureApi.ftir(x, y, {
          toleranceCm1: tolerance === '' ? undefined : Number(tolerance),
        });
        setResult({ kind: 'ftir', data: res.data, input: { x, y } });
      }
    } catch (err) {
      setError(describeError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <h2>{t('structure.title')}</h2>
      <p className="intro">{t('structure.intro')}</p>

      <div className="tabs">
        <button
          type="button"
          className={mode === 'xrd' ? 'tab active' : 'tab'}
          onClick={() => {
            setMode('xrd');
            setResult(null);
            setError('');
          }}
        >
          {t('structure.xrd')}
        </button>
        <button
          type="button"
          className={mode === 'ftir' ? 'tab active' : 'tab'}
          onClick={() => {
            setMode('ftir');
            setResult(null);
            setError('');
          }}
        >
          {t('structure.ftir')}
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
        {mode === 'xrd' ? (
          <>
            <TraceInput
              label={`${t('structure.twoTheta')} / ${t('structure.intensity')}`}
              hint={`One row per point: 2theta intensity. At least ${MIN_XRD_POINTS} rows.`}
              placeholder={'10\t120\n17.5\t980\n19.2\t1450\n23.5\t760\n35\t300'}
              value={xrdText}
              onChange={setXrdText}
            />
            <div className="two-col">
              <label className="field">
                <span className="field-label">{t('structure.wavelength')}</span>
                <input
                  type="number"
                  step="0.0001"
                  min="0.1"
                  value={wavelength}
                  onChange={(e) => setWavelength(e.target.value)}
                />
              </label>
              <label className="field">
                <span className="field-label">{t('structure.instrumentFwhm')}</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={instFwhm}
                  onChange={(e) => setInstFwhm(e.target.value)}
                />
                <span className="field-hint">{t('structure.instrumentFwhmHint')}</span>
              </label>
            </div>
            <div className="two-col">
              <label className="field">
                <span className="field-label">{t('structure.kFactor')}</span>
                <input
                  type="number"
                  step="0.05"
                  min="0.1"
                  max="2"
                  value={kFactor}
                  onChange={(e) => setKFactor(e.target.value)}
                />
                <span className="field-hint">{t('structure.kFactorHint')}</span>
              </label>
            </div>
          </>
        ) : (
          <>
            <TraceInput
              label={`${t('structure.wavenumber')} / ${t('structure.absorbance')}`}
              hint={`One row per point: wavenumber absorbance. At least ${MIN_FTIR_POINTS} rows.`}
              placeholder={'1750\t0.82\n1450\t0.41\n1180\t0.66\n1080\t0.58\n750\t0.23'}
              value={ftirText}
              onChange={setFtirText}
            />
            <div className="two-col">
              <label className="field">
                <span className="field-label">{t('structure.tolerance')}</span>
                <input
                  type="number"
                  step="1"
                  min="0"
                  value={tolerance}
                  onChange={(e) => setTolerance(e.target.value)}
                />
                <span className="field-hint">{t('structure.toleranceHint')}</span>
              </label>
            </div>
          </>
        )}

        <button type="button" className="submit-btn" disabled={loading} onClick={run}>
          {loading ? t('common.calculating') : t('common.calculate')}
        </button>
      </div>

      <ErrorBanner message={error} />

      {result?.kind === 'xrd' ? <XrdResults data={result.data} t={t} kFactor={kFactor} /> : null}
      {result?.kind === 'ftir' ? <FtirResults data={result.data} t={t} input={result.input} /> : null}

      <FormulaDisclosure>
        <Formula
          name={t('structure.f.bragg.name')}
          expression="d = λ / (2 sin θ)"
          symbols={[
            { symbol: 'd', meaning: t('structure.f.bragg.d') },
            { symbol: 'λ', meaning: t('structure.f.bragg.lambda') },
            { symbol: 'θ', meaning: t('structure.f.bragg.theta') },
          ]}
          note={t('structure.f.bragg.note')}
          reference="Bragg & Bragg, 'The reflection of X-rays by crystals', Proc. R. Soc. A 88 (1913) 428–438."
        />
        <Formula
          name={t('structure.f.scherrer.name')}
          expression="D = K λ / (β cos θ)"
          symbols={[
            { symbol: 'D', meaning: t('structure.f.scherrer.D') },
            { symbol: 'K', meaning: t('structure.f.scherrer.K') },
            { symbol: 'λ', meaning: t('structure.f.scherrer.lambda') },
            { symbol: 'β', meaning: t('structure.f.scherrer.beta') },
            { symbol: 'θ', meaning: t('structure.f.scherrer.theta') },
          ]}
          note={t('structure.f.scherrer.note')}
          reference="Scherrer, 'Bestimmung der Größe und der inneren Struktur von Kolloidteilchen mittels Röntgenstrahlen', Göttinger Nachrichten 2 (1918) 98–100."
          referenceNote={t('structure.f.scherrer.referenceNote')}
        />
        <Formula
          name={t('structure.f.fwhm.name')}
          expression="β = 2·|2θ(meia) − 2θ(pico)|"
          expressionNote={t('structure.f.fwhm.expressionNote')}
          symbols={[
            { symbol: 'β', meaning: t('structure.f.fwhm.beta') },
            { symbol: '2θ', meaning: t('structure.f.fwhm.tt') },
          ]}
          note={t('structure.f.fwhm.note')}
          referenceNote={t('structure.f.fwhm.referenceNote')}
        />
        <Formula
          name={t('structure.f.xc.name')}
          expression="CI (%) = 100 · A_c / A_t"
          expressionNote={t('structure.f.xc.expressionNote')}
          symbols={[
            { symbol: 'A', meaning: t('structure.f.xc.A') },
            { symbol: 'At', meaning: t('structure.f.xc.At') },
          ]}
          note={t('structure.f.xc.note')}
          reference="Segal et al., 'An empirical method for estimating the degree of crystallinity of native cellulose using the X-ray diffractometer', Textile Research Journal 29 (1959) 786–794."
          referenceNote={t('structure.f.xc.referenceNote')}
        />
      </FormulaDisclosure>
    </div>
  );
}

function XrdResults({ data, t, kFactor }) {
  // The API returns parallel arrays, one entry per indexed peak.
  const positions = data.peaks_two_theta || [];
  const rows = positions.map((tt, i) => ({
    idx: i + 1,
    two_theta: tt,
    d_spacing: (data.d_spacing_angstrom || [])[i],
    fwhm: (data.fwhm_deg || [])[i],
    size: (data.crystallite_size_nm || [])[i],
  }));

  const sizes = rows.map((r) => r.size).filter((v) => typeof v === 'number' && Number.isFinite(v));
  const meanSize = sizes.length > 0 ? sizes.reduce((a, b) => a + b, 0) / sizes.length : null;

  // Mark where peaks were found, at the observed intensity.
  const markers = positions.map((tt, i) => {
    const nearest = nearestIndex(data.two_theta || [], tt);
    return {
      x: tt,
      y: nearest === -1 ? null : (data.intensity || [])[nearest],
      type: 'scatter',
      mode: 'markers',
      marker: { color: '#d9534f', size: 10, symbol: 'triangle-down' },
      showlegend: false,
      hovertext: `2θ = ${tt}`,
    };
  });

  return (
    <section className="results">
      <h3>{t('common.results')}</h3>
      <StatGrid>
        <Stat label={t('structure.peaks')} value={positions.length} />
        {data.crystallinity_pct !== null && data.crystallinity_pct !== undefined ? (
          <Stat
            label={t('structure.crystallinity')}
            value={data.crystallinity_pct}
            unit="%"
            note={t('structure.crystallinityNote')}
          />
        ) : null}
        {meanSize !== null ? (
          <Stat label={t('structure.size')} value={meanSize} unit="nm" note={`Scherrer, K = ${kFactor}`} />
        ) : null}
      </StatGrid>

      {rows.length > 0 ? (
        <>
          <h4>{t('structure.peaks')}</h4>
          <DataTable
            columns={[
              { key: 'idx', label: '#' },
              { key: 'two_theta', label: t('structure.peak'), digits: 3 },
              { key: 'd_spacing', label: t('structure.dSpacing'), digits: 3 },
              { key: 'fwhm', label: t('structure.fwhm'), digits: 4 },
              { key: 'size', label: t('structure.size'), digits: 2 },
            ]}
            rows={rows}
          />
        </>
      ) : null}

      <div className="plot">
        <Plot
          data={[
            {
              x: data.two_theta,
              y: data.intensity,
              type: 'scatter',
              mode: 'lines',
              name: t('structure.pattern'),
              line: { color: '#2b7de9' },
            },
            ...markers,
          ]}
          layout={{
            height: 380,
            margin: { l: 60, r: 20, t: 40, b: 50 },
            xaxis: { title: t('structure.twoTheta') },
            yaxis: { title: t('structure.intensity') },
            legend: { orientation: 'h', y: -0.2 },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
        />
      </div>
    </section>
  );
}

/** Index of the trace value closest to `target`, or -1 if the array is empty. */
function nearestIndex(values, target) {
  let best = -1;
  let bestDist = Infinity;
  for (let i = 0; i < values.length; i += 1) {
    const d = Math.abs(values[i] - target);
    if (d < bestDist) {
      bestDist = d;
      best = i;
    }
  }
  return best;
}

function FtirResults({ data, t, input }) {
  const matches = data.matches || [];
  const rows = matches.map((m, i) => ({
    idx: i + 1,
    observed: m.observed_cm1,
    height: m.relative_height,
    assignments: (m.candidates || []).map((c) => c.assignment),
  }));

  // FTIRResult does not echo the spectrum back, so the plot uses the values
  // the user supplied rather than inventing a trace.
  const spectrum = input || { x: [], y: [] };

  return (
    <section className="results">
      <h3>{t('common.results')}</h3>
      <StatGrid>
        <Stat label={t('structure.bands')} value={(data.detected_peaks || []).length} />
      </StatGrid>

      {rows.length > 0 ? <div className="note-box">{data.note || t('structure.ftirWarning')}</div> : null}

      {rows.length > 0 ? (
        <>
          <h4>{t('structure.bands')}</h4>
          <DataTable
            columns={[
              { key: 'idx', label: '#' },
              { key: 'observed', label: t('structure.wavenumber'), digits: 1 },
              { key: 'height', label: t('structure.intensity'), digits: 2 },
              {
                key: 'assignments',
                label: t('structure.assignments'),
                render: (row) => (row.assignments.length > 0 ? row.assignments.join(' · ') : '—'),
              },
            ]}
            rows={rows}
          />

          <Disclosure title={t('structure.assignments')}>
            {matches.map((m, i) => (
              <div key={i} className="assignment-block">
                <strong>
                  {m.observed_cm1} cm⁻¹ (rel. {Math.round((m.relative_height || 0) * 100)}%)
                </strong>
                <ul className="log">
                  {(m.candidates || []).map((c, j) => (
                    <li key={j}>
                      {c.assignment} — {c.expected_intensity}. {c.note}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </Disclosure>
        </>
      ) : null}

      {spectrum.x.length > 0 ? (
        <div className="plot">
          <Plot
            data={[
              {
                x: spectrum.x,
                y: spectrum.y,
                type: 'scatter',
                mode: 'lines',
                name: t('structure.spectrum'),
                line: { color: '#2b7de9' },
              },
              ...(data.detected_peaks || []).map((wn) => ({
                x: wn,
                y: [spectrum.y[nearestIndex(spectrum.x, wn)]],
                type: 'scatter',
                mode: 'markers',
                marker: { color: '#d9534f', size: 10, symbol: 'triangle-down' },
                showlegend: false,
                hovertext: `${wn} cm⁻¹`,
              })),
            ]}
            layout={{
              height: 380,
              margin: { l: 60, r: 20, t: 40, b: 50 },
              xaxis: { title: t('structure.wavenumber'), autorange: 'reversed' },
              yaxis: { title: t('structure.absorbance') },
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%' }}
          />
        </div>
      ) : null}
    </section>
  );
}
