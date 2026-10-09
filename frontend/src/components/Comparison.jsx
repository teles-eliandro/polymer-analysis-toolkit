/**
 * Measured values compared against published reference ranges.
 *
 * The verdict is tri-state and the third state is the feature. "not comparable"
 * is what stops a detector failure from being reported as a finding about the
 * sample: when the glass transition has been placed on a melting flank, the
 * honest answer is that there is no comparison to make, not "outside the
 * published range".
 *
 * The reference ranges are data with citations, so they carry a `read` rung --
 * they are not this tool's inference. Each row names the source it used.
 */

import React from 'react';
import { useI18n } from '../i18n/I18nContext';
import { ConfidenceBadge, READ } from './Confidence';

/** The three verdicts, as the backend spells them. */
export const WITHIN = 'within';
export const OUTSIDE = 'outside';
export const NOT_COMPARABLE = 'not_comparable';

const VERDICT_CLASS = {
  [WITHIN]: 'verdict-within',
  [OUTSIDE]: 'verdict-outside',
  [NOT_COMPARABLE]: 'verdict-none',
};

const VERDICT_ICON = {
  [WITHIN]: '✓',
  [OUTSIDE]: '✗',
  [NOT_COMPARABLE]: '—',
};

/** A single comparison row: the value, the range, the verdict, the source. */
export function ComparisonRow({ comparison }) {
  const { t, tOrNull } = useI18n();
  const c = comparison;
  const cls = VERDICT_CLASS[c.verdict] || 'verdict-none';
  const icon = VERDICT_ICON[c.verdict] || '—';

  // Prefer a translation of the reason code; fall back to the server's English
  // prose, which is the canonical wording. A code this build does not know
  // must show that prose rather than nothing.
  const reason =
    (c.reason_code && tOrNull(`comparison.reason.${c.reason_code}`)) || c.reason;

  const hasRange =
    c.reference_low !== null &&
    c.reference_low !== undefined &&
    c.reference_high !== null &&
    c.reference_high !== undefined;

  return (
    <div className={`comparison ${cls}`}>
      <div className="comparison-head">
        <span className="comparison-icon" aria-hidden="true">{icon}</span>
        <span className="comparison-prop">{c.property}</span>
        <span className="comparison-verdict">
          {t(`comparison.${c.verdict}`)}
        </span>
      </div>

      <div className="comparison-values">
        <span className="comparison-measured">
          {c.measured === null || c.measured === undefined
            ? t('comparison.notReported')
            : `${Number(c.measured).toFixed(2)} ${c.unit || ''}`.trim()}
        </span>
        {hasRange ? (
          <span className="comparison-range">
            {t('comparison.publishedRange')}{' '}
            <strong>
              {Number(c.reference_low).toFixed(0)}–{Number(c.reference_high).toFixed(0)}{' '}
              {c.reference_unit}
            </strong>
            {c.reference_method ? (
              <em className="comparison-method"> · {c.reference_method}</em>
            ) : null}
          </span>
        ) : null}
      </div>

      {reason ? <p className="comparison-reason">{reason}</p> : null}

      {c.reference_note ? (
        <p className="comparison-note">{c.reference_note}</p>
      ) : null}

      {c.reference_source ? (
        <p className="comparison-source">
          <span className="comparison-source-label">{t('comparison.source')}:</span>{' '}
          {c.reference_source}
        </p>
      ) : null}

      {c.polymer ? (
        <p className="comparison-polymer">
          <span className="comparison-source-label">{t('comparison.polymer')}:</span>{' '}
          {c.polymer} <ConfidenceBadge claim={{ confidence: READ }} />
        </p>
      ) : null}
    </div>
  );
}

/** The comparison block: a heading and one row per comparable property. */
export function ComparisonPanel({ comparisons }) {
  const { t } = useI18n();
  if (!comparisons || comparisons.length === 0) return null;

  return (
    <section className="comparison-panel">
      <h4>{t('comparison.title')}</h4>
      <p className="comparison-intro">{t('comparison.intro')}</p>
      <div className="comparison-list">
        {comparisons.map((c) => (
          <ComparisonRow key={c.property} comparison={c} />
        ))}
      </div>
    </section>
  );
}
