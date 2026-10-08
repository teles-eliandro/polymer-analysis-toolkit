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
import { Formula, FormulaDisclosure } from './Formula';
import FileDrop from './FileDrop';

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

  const handleFileChange = async (f) => {
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
          <FileDrop
            onFile={handleFileChange}
            onError={setError}
            label={t('molecular.uploadLabel')}
            hint={t('file.accepted', {
              list: 'CSV, TSV, TXT, DAT, ASC, PRN, XY, JSON',
            })}
          />
          <p className="field-hint">{t('molecular.uploadHint')}</p>

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

      <FormulaDisclosure>
        <Formula
          name={t('mol.f.mn.name')}
          expression="Mn = sum(Ni Mi) / sum(Ni)      Mw = sum(Ni Mi^2) / sum(Ni Mi)"
          symbols={[
            { symbol: 'Ni', meaning: t('mol.f.mn.Ni') },
            { symbol: 'Mi', meaning: t('mol.f.mn.Mi') },
          ]}
          note={t('mol.f.mn.note')}
          reference="IUPAC, Compendium of Macromolecular Nomenclature (1991), recommendations on molecular weight distributions. Also ASTM D5296-19 for GPC/SEC of polystyrene."
        />
        <Formula
          name={t('mol.f.pdi.name')}
          expression="D = Mw / Mn   (dispersity, formerly polydispersity index)"
          symbols={[
            { symbol: 'D', meaning: t('mol.f.pdi.D') },
            { symbol: 'Mw', meaning: t('mol.f.pdi.Mw') },
            { symbol: 'Mn', meaning: t('mol.f.pdi.Mn') },
          ]}
          note={t('mol.f.pdi.note')}
          reference="IUPAC recommends the term dispersity and the symbol D. A value below 1 is not a narrow distribution but an error in the data or the calculation."
        />
        <Formula
          name={t('mol.f.mz.name')}
          expression="Mz = sum(Ni Mi^3) / sum(Ni Mi^2)"
          symbols={[
            { symbol: 'Ni', meaning: t('mol.f.mz.Ni') },
            { symbol: 'Mi', meaning: t('mol.f.mz.Mi') },
          ]}
          note={t('mol.f.mz.note')}
          reference="The z-average is weighted towards the heaviest chains, so it responds to a high-mass tail that Mw barely registers."
        />
        <Formula
          name={t('mol.f.mh.name')}
          expression="[eta] = K Mv^a      (Mark-Houwink-Sakurada)"
          symbols={[
            { symbol: 'Mv', meaning: t('mol.f.mh.Mv') },
            { symbol: 'K', meaning: t('mol.f.mh.K') },
            { symbol: 'a', meaning: t('mol.f.mh.a') },
          ]}
          note={t('mol.f.mh.note')}
          reference="Mark-Houwink-Sakurada relation; K and a are tabulated per polymer-solvent-temperature combination in the Polymer Handbook. They are not universal constants."
        />
        <Formula
          name={t('mol.f.gpc.name')}
          expression="log M = f(elution volume)   calibrated against narrow standards"
          symbols={[
            { symbol: 'M', meaning: t('mol.f.gpc.M') },
          ]}
          note={t('mol.f.gpc.note')}
          reference="Conventional GPC calibration assumes the sample and the standards have the same hydrodynamic volume at a given elution volume. Reporting the result as absolute molar mass without a light-scattering or viscometry detector overstates what the measurement supports."
        />
        <Formula
          name={t('mol.f.log.name')}
          expression={
            "w(log M) = (1 / (M sigma sqrt(2 pi))) exp( -(ln M - mu)^2 / (2 sigma^2) )"
          }
          symbols={[
            { symbol: 'w', meaning: t('mol.f.log.w') },
            { symbol: 'sigma', meaning: t('mol.f.log.sigma') },
            { symbol: 'mu', meaning: t('mol.f.log.mu') },
          ]}
          note={t('mol.f.log.note')}
          reference="Schulz-Zimm and log-normal distributions are the usual models for a SEC trace; the log-normal is used here because its Mw/Mn follows directly from sigma."
        />
      </FormulaDisclosure>
    </div>
  );
}
