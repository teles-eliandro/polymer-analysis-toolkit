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
 *
 * Why `reference` and `referenceNote` are separate props, and why only one of
 * them goes through `t()`:
 *
 * A reference is two things glued together. "ASTM D638-22, Standard Test
 * Method for Tensile Properties of Plastics" is a citation: a name that
 * identifies a document, which a reader will search for verbatim. "Both
 * require the modulus from the initial linear region" is prose, written for
 * the person reading the page. They have opposite translation rules -- the
 * citation must never be translated (a translated standard name retrieves
 * nothing), and the prose must always be. Kept in one string they can only be
 * translated together, so the prose was left in English on every page and the
 * Portuguese page showed English paragraphs under a Portuguese heading.
 *
 * The same split applies to `expression` and `expressionNote`: the notation
 * "E = Δσ / Δε" is the same in every language, while the parenthetical
 * "(slope of the initial linear region)" is not.
 */
export function Formula({
  name,
  expression,
  expressionNote,
  symbols = [],
  reference,
  referenceNote,
  note,
}) {
  const { t } = useI18n();
  return (
    <div className="formula">
      <div className="formula-head">
        <span className="formula-name">{name}</span>
      </div>
      <div className="formula-expression">
        <code>{expression}</code>
        {expressionNote ? (
          <span className="formula-expression-note"> {expressionNote}</span>
        ) : null}
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
      {reference || referenceNote ? (
        <p className="formula-reference">
          <span className="formula-reference-label">{t('common.ref')}</span>{' '}
          {reference ? <span className="formula-citation">{reference}</span> : null}
          {reference && referenceNote ? ' ' : null}
          {referenceNote ? (
            <span className="formula-reference-note">{referenceNote}</span>
          ) : null}
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
