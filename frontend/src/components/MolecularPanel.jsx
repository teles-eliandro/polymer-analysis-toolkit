/**
 * Molecular module: molar-mass averages, with the tolerant file importer.
 *
 * Two input paths, both of which the backend supports and the tests cover:
 * uploading an instrument export, or entering the distribution directly.
 * The importer's decision log is surfaced so that a misread file is visible.
 */

import React, { useState } from 'react';
import Plot from 'react-plotly.js';
import { molecularApi, describeError } from '../services/api';
import { useI18n, formatNumber } from '../i18n/I18nContext';
import { Stat, StatGrid, Disclosure, ErrorBanner } from './ui';

const MOLECULAR_KEYS = [
  ['Mn', 'molecular.Mn', 'molecular.MnNote'],
  ['Mw', 'molecular.Mw', 'molecular.MwNote'],
  ['Mz', 'molecular.Mz', 'molecular.MzNote'],
  ['Mz_plus_1', 'molecular.Mz1', 'molecular.Mz1Note'],
];

export default function MolecularPanel() {
  const { t } = useI18n();

  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [normalise, setNormalise] = useState(false);
  const [markHouwink, setMarkHouwink] = useState('');

  const [massesText, setMassesText] = useState('');
  const [fractionsText, setFractionsText] = useState('');

  const [result, setResult] = useState(null);
  const [inputData, setInputData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [refDispersity, setRefDispersity] = useState('1.5');
  const [refMn, setRefMn] = useState('50000');

  const parseColumn = (text) =>
    String(text)
      .split(/[\s,;\t\r\n]+/)
      .map((s) => s.replace(',', '.'))
      .filter((s) => s.length > 0)
      .map(Number);

  const resetOutput = () => {
    setResult(null);
    setError('');
  };

  const handleFileChange = async (e) => {
    const f = e.target.files?.[0] || null;
    setFile(f);
    resetOutput();
    setPreview(null);
    if (!f) return;
    try {
      const res = await molecularApi.previewImport(f);
      setPreview(res.data);
    } catch (err) {
      // The preview is a convenience: if it fails, still let the user try the
      // calculation, whose error message will be equally specific.
      setPreview(null);
    }
  };

  const runFromFile = async () => {
    if (!file) {
      setError(t('error.needFile'));
      return;
    }
    setLoading(true);
    resetOutput();
    try {
      const a = markHouwink === '' ? null : Number(markHouwink);
      if (a !== null && (!Number.isFinite(a) || a <= 0)) {
        throw new Error('The Mark-Houwink exponent must be a positive number.');
      }
      const res = await molecularApi.calculateFromFile(file, { normalise, markHouwinkA: a });
      setResult(res.data);
      setInputData({ masses: preview?.masses, weight_fractions: preview?.weight_fractions });
    } catch (err) {
      setError(err.message && !err.response ? err.message : describeError(err));
    } finally {
      setLoading(false);
    }
  };

  const runFromInput = async () => {
    const masses = parseColumn(massesText);
    const fractions = parseColumn(fractionsText);
    if (masses.length === 0 || fractions.length === 0) {
      setError(t('error.needData'));
      return;
    }
    if (masses.length !== fractions.length) {
      setError(t('error.mismatched'));
      return;
    }
    if (masses.some((v) => !Number.isFinite(v)) || fractions.some((v) => !Number.isFinite(v))) {
      setError(t('error.badNumbers'));
      return;
    }
    setLoading(true);
    resetOutput();
    try {
      const a = markHouwink === '' ? null : Number(markHouwink);
      const res = await molecularApi.calculate({
        masses,
        weight_fractions: fractions,
        normalise,
        mark_houwink_a: a,
      });
      setResult(res.data);
      setInputData({ masses, weight_fractions: fractions });
    } catch (err) {
      setError(describeError(err));
    } finally {
      setLoading(false);
    }
  };

  const generateReference = async () => {
    setLoading(true);
    resetOutput();
    try {
      const res = await molecularApi.logNormal(Number(refMn), Number(refDispersity));
      setResult(res.data);
      setInputData(null);
    } catch (err) {
      setError(describeError(err));
    } finally {
      setLoading(false);
    }
  };

  const exportJson = () => {
    const blob = new Blob([JSON.stringify({ result, input: inputData }, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'pat-molar-mass.json';
    link.click();
    URL.revokeObjectURL(url);
  };

  // The weight distribution, computed client-side purely for plotting: the
  // backend has already returned the authoritative averages.
  const distributionTrace =
    inputData?.masses && inputData?.weight_fractions
      ? {
          x: inputData.masses,
          y: inputData.weight_fractions,
          type: 'bar',
          marker: { color: '#2b7de9' },
          name: t('molecular.distribution'),
        }
      : null;

  return (
    <div className="panel">
      <h2>{t('molecular.title')}</h2>
      <p className="intro">{t('molecular.intro')}</p>

      <div className="input-options">
        <section className="card">
          <h3>{t('common.upload')}</h3>
          <label className="field">
            <span className="field-label">{t('molecular.uploadLabel')}</span>
            <input type="file" accept=".csv,.txt,.tsv,.dat" onChange={handleFileChange} />
            <span className="field-hint">{t('molecular.uploadHint')}</span>
          </label>
          {file ? <div className="file-name">{file.name}</div> : null}

          <div className="options-row">
            <label className="checkbox">
              <input
                type="checkbox"
                checked={normalise}
                onChange={(e) => setNormalise(e.target.checked)}
              />
              <span>
                {t('molecular.normalise')}
                <span className="field-hint">{t('molecular.normaliseHint')}</span>
              </span>
            </label>
          </div>

          <label className="field">
            <span className="field-label">
              {t('molecular.markHouwink')} <em>({t('common.optional')})</em>
            </span>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={markHouwink}
              placeholder="e.g. 0.70"
              onChange={(e) => setMarkHouwink(e.target.value)}
            />
            <span className="field-hint">{t('molecular.markHouwinkHint')}</span>
          </label>

          {preview ? (
            <Disclosure title={t('common.importDecisions')}>
              <ul className="decisions">
                {preview.decisions.map((d, i) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
              <div className="preview-meta">
                {preview.n_slices} {t('common.slices')} · {preview.scale_detected}
                {preview.instrument_Mn ? ` · Mn(file)=${formatNumber(preview.instrument_Mn)}` : ''}
                {preview.instrument_Mw ? ` · Mw(file)=${formatNumber(preview.instrument_Mw)}` : ''}
              </div>
            </Disclosure>
          ) : null}

          <button
            type="button"
            className="submit-btn"
            disabled={loading || !file}
            onClick={runFromFile}
          >
            {loading ? t('common.calculating') : t('common.calculate')}
          </button>
        </section>

        <section className="card">
          <h3>{t('molecular.manualEntry')}</h3>
          <div className="two-col">
            <label className="field">
              <span className="field-label">{t('molecular.masses')}</span>
              <textarea
                rows={6}
                value={massesText}
                onChange={(e) => setMassesText(e.target.value)}
                placeholder={'1000\n2000\n5000'}
              />
            </label>
            <label className="field">
              <span className="field-label">{t('molecular.fractions')}</span>
              <textarea
                rows={6}
                value={fractionsText}
                onChange={(e) => setFractionsText(e.target.value)}
                placeholder={'0.2\n0.5\n0.3'}
              />
            </label>
          </div>
          <span className="field-hint">{t('molecular.pairHint')}</span>
          <button
            type="button"
            className="submit-btn"
            disabled={loading}
            onClick={runFromInput}
          >
            {loading ? t('common.calculating') : t('common.calculate')}
          </button>
        </section>

        <section className="card">
          <h3>{t('molecular.reference')}</h3>
          <p className="field-hint">{t('molecular.referenceNote')}</p>
          <div className="two-col">
            <label className="field">
              <span className="field-label">Mn (g/mol)</span>
              <input
                type="number"
                value={refMn}
                onChange={(e) => setRefMn(e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field-label">{t('molecular.referenceDispersity')}</span>
              <input
                type="number"
                step="0.01"
                min="1"
                value={refDispersity}
                onChange={(e) => setRefDispersity(e.target.value)}
              />
            </label>
          </div>
          <button type="button" className="submit-btn ghost" disabled={loading} onClick={generateReference}>
            {t('molecular.generate')}
          </button>
        </section>
      </div>

      <ErrorBanner message={error} />

      {result ? (
        <section className="results">
          <div className="results-head">
            <h3>{t('common.results')}</h3>
            <button type="button" className="link-btn" onClick={exportJson}>
              {t('common.exportJson')}
            </button>
          </div>

          <StatGrid>
            {MOLECULAR_KEYS.map(([key, labelKey, noteKey]) => (
              <Stat
                key={key}
                label={t(labelKey)}
                value={result[key]}
                unit="g/mol"
                note={t(noteKey)}
              />
            ))}
            {result.Mv !== null && result.Mv !== undefined ? (
              <Stat
                label={t('molecular.Mv')}
                value={result.Mv}
                unit="g/mol"
                note={`a = ${result.mark_houwink_a}`}
              />
            ) : null}
            <Stat
              label={t('molecular.dispersity')}
              value={result.dispersity}
              note={t('molecular.dispersityNote')}
            />
          </StatGrid>

          {preview?.instrument_Mn || preview?.instrument_Mw ? (
            <div className="crosscheck">
              <h4>{t('molecular.crossCheck')}</h4>
              <p className="field-hint">{t('molecular.crossCheckNote')}</p>
              <table className="data-table">
                <thead>
                  <tr>
                    <th />
                    <th>{t('molecular.fileMn')}</th>
                    <th>{t('molecular.calcMn')}</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.instrument_Mn ? (
                    <tr>
                      <td>Mn</td>
                      <td>{formatNumber(preview.instrument_Mn)}</td>
                      <td>{formatNumber(result.Mn)}</td>
                    </tr>
                  ) : null}
                  {preview.instrument_Mw ? (
                    <tr>
                      <td>Mw</td>
                      <td>{formatNumber(preview.instrument_Mw)}</td>
                      <td>{formatNumber(result.Mw)}</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          ) : null}

          {distributionTrace ? (
            <div className="plot">
              <Plot
                data={[distributionTrace]}
                layout={{
                  title: t('molecular.distribution'),
                  xaxis: { title: 'M (g/mol)', type: 'log' },
                  yaxis: { title: 'weight fraction' },
                  height: 340,
                  margin: { l: 60, r: 20, t: 40, b: 50 },
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
