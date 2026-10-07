/** Shared presentational components used by every module panel. */

import React, { useState } from 'react';
import { useI18n, formatNumber } from '../i18n/I18nContext';

/** A single labelled result value, with an optional explanatory note. */
export function Stat({ label, value, unit, note, raw }) {
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
