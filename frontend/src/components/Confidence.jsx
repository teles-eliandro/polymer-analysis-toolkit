/**
 * Confidence badges for reported values.
 *
 * The backend returns every number with a confidence rung and the evidence
 * behind it, because the modules do not all do the same kind of work: reading
 * an instrument file is deterministic, while deciding which transition is which
 * is an inference that is measurably wrong on real data. Showing the number
 * without the rung is how a guess gets quoted as a measurement.
 *
 * Rungs, in trust order:
 *   read       a property of the input, or a deterministic transform of it
 *   formula    a published formula over a declared input; reproducible
 *   suggested  an inference from the trace shape; can be wrong
 */

import React, { useState } from 'react';
import { useI18n } from '../i18n/I18nContext';

/** The rung names, as the backend spells them. */
export const READ = 'read';
export const FORMULA = 'formula';
export const SUGGESTED = 'suggested';

const RUNG_CLASS = {
  [READ]: 'rung-read',
  [FORMULA]: 'rung-formula',
  [SUGGESTED]: 'rung-suggested',
};

/**
 * A small badge naming the confidence of the value next to it.
 *
 * Renders nothing when there is no claim, so a panel that has not been given
 * claims does not sprout an empty badge.
 */
export function ConfidenceBadge({ claim }) {
  const { t } = useI18n();
  if (!claim || !claim.confidence) return null;

  const key = `confidence.${claim.confidence}`;
  const translated = t(key);
  // t() returns the key itself when a translation is missing, which would put
  // "confidence.estimated" on screen for a rung the backend added and this
  // build does not know. Fall back to the raw rung name instead: an untranslated
  // word is readable, a namespace-qualified key is not.
  const label = translated === key ? claim.confidence : translated;
  const cls = RUNG_CLASS[claim.confidence] || 'rung-suggested';

  return (
    <span
      className={`rung ${cls}`}
      title={t(`confidence.${claim.confidence}.hint`)}
    >
      {label}
    </span>
  );
}

/**
 * The evidence and caveat behind a suggested value, collapsed by default.
 *
 * Collapsed because the number must stay scannable, and expanded because a
 * suggestion whose basis cannot be inspected is just a number with a friendlier
 * label. The note is shown in the summary line so the caveat is visible even
 * when the block is closed.
 */
export function ClaimEvidence({ claim }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);

  if (!claim) return null;
  const evidence = claim.evidence || [];
  const hasDetail = evidence.length > 0 || claim.note;
  if (!hasDetail) return null;

  return (
    <div className="claim">
      <button
        type="button"
        className="claim-toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="claim-caret">{open ? '▾' : '▸'}</span>
        {t('confidence.why')}
      </button>
      {open ? (
        <ul className="claim-list">
          {evidence.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
          {claim.note ? <li className="claim-note">{claim.note}</li> : null}
        </ul>
      ) : null}
    </div>
  );
}

/**
 * Everything a reader needs about one reported value: the number, its rung,
 * and the basis for it.
 *
 * This wraps the existing `Stat` presentation rather than replacing it, so the
 * layout of the results grid is unchanged and only the trust information is
 * added.
 */
export function ClaimedStat({ label, value, unit, note, claim, children }) {
  return (
    <div className="stat">
      <div className="stat-label">
        {label} <ConfidenceBadge claim={claim} />
      </div>
      {children || (
        <div className="stat-value">
          {value === null || value === undefined
            ? '—'
            : Number(value).toFixed(2)}
          {unit ? <span className="stat-unit">{unit}</span> : null}
        </div>
      )}
      {note ? <div className="stat-note">{note}</div> : null}
      <ClaimEvidence claim={claim} />
    </div>
  );
}
