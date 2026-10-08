/** Shared presentational components used by every module panel. */

import React, { useState } from 'react';
import { saveAs } from 'file-saver';
import { useI18n, formatNumber } from '../i18n/I18nContext';
import { buildZip, dataUrlToBytes, toCsv } from '../services/zip';

/** A single labelled result value, with an optional explanatory note. */
export function Stat({ label, value, unit, note, raw, footing, footingWarning }) {
  const display =
    raw !== undefined && raw !== null && typeof raw !== 'number'
      ? raw
      : formatNumber(value);
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">
        {display}
        {unit ? <span className="stat-unit">{unit}</span> : null}
      </div>
      {footing ? (
        // How much to trust the number above. Deliberately next to the value
        // rather than in a footnote: a research value without its footing is
        // the thing that gets misquoted later.
        <div className={footingWarning ? 'stat-footing warn' : 'stat-footing'}>{footing}</div>
      ) : null}
      {note ? <div className="stat-note">{note}</div> : null}
    </div>
  );
}

/** A grid of stats. */
export function StatGrid({ children }) {
  return <div className="stat-grid">{children}</div>;
}

/** A collapsible block, used for the importer's decision log and long tables. */
export function Disclosure({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const { t } = useI18n();
  return (
    <div className="disclosure">
      <button
        type="button"
        className="disclosure-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="disclosure-caret">{open ? '▾' : '▸'}</span>
        {title}
        <span className="disclosure-hint">
          {open ? t('common.hideDetails') : t('common.showDetails')}
        </span>
      </button>
      {open ? <div className="disclosure-body">{children}</div> : null}
    </div>
  );
}

/** A generic table from columns + rows. */
export function DataTable({ columns, rows }) {
  if (!rows || rows.length === 0) return null;
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c.key}>
                  {c.render ? c.render(row) : formatNumber(row[c.key], c.digits)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Confirmation that the API answered, or the reason it did not. */
export function ApiStatus({ online, error }) {
  const { t } = useI18n();
  if (online === null) return null;
  return (
    <div className={`api-status ${online ? 'is-online' : 'is-offline'}`}>
      <span className="dot" />
      {online ? t('common.apiOk') : `${t('common.apiUnreachable')}${error ? `: ${error}` : ''}`}
    </div>
  );
}

/** The error banner. */
export function ErrorBanner({ message }) {
  const { t } = useI18n();
  if (!message) return null;
  return (
    <div className="error-message" role="alert">
      <strong>{t('common.error')}:</strong> {message}
    </div>
  );
}

/**
 * Parse a pasted two-column numeric block.
 *
 * Accepts whitespace, comma, semicolon or tab separated values, one pair per
 * line, and tolerates decimal commas. Returns { x: [], y: [], error }.
 */
export function parseTwoColumns(text) {
  const x = [];
  const y = [];
  const lines = String(text)
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0 && !l.startsWith('#') && !l.startsWith('//'));

  for (const line of lines) {
    // Skip an obvious header row.
    const numeric = line.match(/-?\d/);
    if (!numeric) continue;
    const parts = line
      .split(/[\s,;\t]+/)
      .map((p) => p.trim())
      .filter((p) => p.length > 0);
    if (parts.length < 2) continue;
    const toNum = (s) => {
      const cleaned = s.replace(/[^0-9eE+\-.,]/g, '');
      const norm =
        cleaned.includes(',') && cleaned.includes('.')
          ? cleaned.replace(/\./g, '').replace(',', '.')
          : cleaned.replace(',', '.');
      const v = Number(norm);
      return Number.isFinite(v) ? v : null;
    };
    const a = toNum(parts[0]);
    const b = toNum(parts[1]);
    if (a === null || b === null) continue;
    x.push(a);
    y.push(b);
  }
  return { x, y, error: null };
}


/**
 * Downloads the chart that sits beside it as a PNG.
 *
 * The results JSON already existed, but a number without the curve it was read
 * off is hard to defend in a report, so the picture has to travel with it.
 * The image comes from the plot's own toImage (Plotly renders the SVG/canvas it
 * already has) rather than from an external screenshot library -- no extra
 * dependency, and the axes, legend and annotations come out exactly as drawn.
 *
 * A failed export must never take the results down with it: a canvas-less or
 * partially-initialised plot rejects here, and we swallow that, leaving the
 * page intact and telling the user in the text it can render.
 */
export function PlotExportButton({ plotRef, filename = 'plot', label, failedLabel }) {
  const [state, setState] = React.useState('idle');

  const handleClick = async () => {
    const el = plotRef && plotRef.current;
    if (!el || typeof el.toImage !== 'function') {
      setState('failed');
      return;
    }
    try {
      const url = await el.toImage({
        format: 'png',
        // Plotly appends its own extension inconsistently across versions, so
        // the name is passed complete and normalised once, here.
        filename: filename.endsWith('.png') ? filename : `${filename}.png`,
        // Twice the drawn size: a chart pasted into a paper is usually
        // reproduced larger than it appears on screen.
        width: el.offsetWidth ? el.offsetWidth * 2 : 1200,
        height: el.offsetHeight ? el.offsetHeight * 2 : 760,
      });
      const link = document.createElement('a');
      link.href = url;
      link.download = filename.endsWith('.png') ? filename : `${filename}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setState('idle');
    } catch (err) {
      // Swallowed on purpose: an unrenderable image is not a failed analysis.
      setState('failed');
    }
  };

  return (
    <>
      <button type="button" className="export-btn" onClick={handleClick}>
        {label || 'Download PNG'}
      </button>
      {state === 'failed' ? (
        <span className="field-hint" role="status">
          {failedLabel || 'Could not render the image.'}
        </span>
      ) : null}
    </>
  );
}

/**
 * Downloads the graph *and* the numbers in one file, as a zip.
 *
 * This is what a report actually needs: the curve as an image, the values as
 * JSON for reuse, and the raw trace as CSV to re-plot elsewhere. Kept separate
 * from the PNG button so a user who only wants the picture is not forced
 * through a dialog.
 */
export function ResultsBundleButton({
  plotRef,
  basename = 'results',
  results,
  columns = [],
  rows = [],
  label,
  failedLabel,
}) {
  const [state, setState] = React.useState('idle');

  const handleClick = async () => {
    try {
      const files = [];
      const pngName = `${basename}-graph.png`;

      // The graph is best-effort: a bundle without the picture still beats no
      // export at all, so a failure here does not abort the download.
      try {
        const el = plotRef && plotRef.current;
        if (el && typeof el.toImage === 'function') {
          const url = await el.toImage({
            format: 'png',
            width: el.offsetWidth ? el.offsetWidth * 2 : 1200,
            height: el.offsetHeight ? el.offsetHeight * 2 : 760,
          });
          files.push({ name: pngName, data: dataUrlToBytes(url) });
        }
      } catch (err) {
        // Fall through: the JSON and CSV are still worth having.
      }

      files.push({
        name: `${basename}-results.json`,
        data: JSON.stringify(results, null, 2),
      });
      if (columns.length && rows.length) {
        files.push({ name: `${basename}-trace.csv`, data: toCsv(columns, rows) });
      }

      saveAs(buildZip(files), `${basename}.zip`);
      setState('idle');
    } catch (err) {
      setState('failed');
    }
  };

  return (
    <>
      <button type="button" className="export-btn" onClick={handleClick}>
        {label || 'Download results + graph (.zip)'}
      </button>
      {state === 'failed' ? (
        <span className="field-hint" role="status">
          {failedLabel || 'Could not build the download.'}
        </span>
      ) : null}
    </>
  );
}
