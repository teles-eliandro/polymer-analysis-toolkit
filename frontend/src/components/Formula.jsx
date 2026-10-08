/**
 * Formula and model disclosure for a result panel.
 *
 * Every module states which expression it applied and where that expression
 * comes from. Recording it next to the result is the difference between a
 * number a reader can check and a number they have to trust: the same tool
 * implementing Scherrer and a tool implementing a fitted peak area will
 * disagree, and the only way to tell them apart is to name the model.
 */

import React from 'react';
import { useI18n } from '../i18n/I18nContext';

/**
 * One entry in a formula list.
 *
 * `symbols` documents each symbol the expression uses. A formula whose
 * symbols are undefined is not reproducible, so this is required for any
 * expression with more than trivial notation.
 */
export function Formula({
  name,
  expression,
  symbols = [],
  reference,
  note,
}) {
  return (
    <div className="formula">
      <div className="formula-head">
        <span className="formula-name">{name}</span>
      </div>
      <div className="formula-expression">
        <code>{expression}</code>
      </div>
      {symbols.length > 0 ? (
        <dl className="formula-symbols">
          {symbols.map((s) => (
            <div className="formula-symbol" key={s.symbol}>
              <dt>{s.symbol}</dt>
              <dd>{s.meaning}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {note ? <p className="formula-note">{note}</p> : null}
      {reference ? (
        <p className="formula-reference">
          <span className="formula-reference-label">Ref.</span> {reference}
        </p>
      ) : null}
    </div>
  );
}

/**
 * Collapsible container for the formula/model block of a panel.
 *
 * Collapsed by default: the expressions matter to a reader checking the
 * result, not to someone reading the number. Kept in the DOM rather than
 * conditionally rendered so the text is found by in-page search and read by
 * assistive technology even while closed.
 */
export function FormulaDisclosure({ title, children, defaultOpen = false }) {
  const { t } = useI18n();
  const [open, setOpen] = React.useState(defaultOpen);
  return (
    <section className="formula-block">
      <button
        type="button"
        className="formula-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="formula-caret" aria-hidden="true">
          {open ? '▾' : '▸'}
        </span>
        <span className="formula-toggle-title">
          {title || t('common.formulasAndModels')}
        </span>
      </button>
      <div className="formula-body" hidden={!open}>
        {children}
      </div>
    </section>
  );
}

export default FormulaDisclosure;
