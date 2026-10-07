/**
 * Polymer Analysis Toolkit - application shell.
 *
 * Five characterisation modules share one page. Each panel owns its own input,
 * request and result state, so switching modules never discards work in
 * another one. Language is handled by I18nProvider; the switcher here only
 * picks the locale.
 */

import React, { useState } from 'react';
import MolecularPanel from './components/MolecularPanel';
import ThermalPanel from './components/ThermalPanel';
import MechanicalPanel from './components/MechanicalPanel';
import RheologyPanel from './components/RheologyPanel';
import StructurePanel from './components/StructurePanel';
import { ApiStatus } from './components/ui';
import { I18nProvider, useI18n, LANGUAGES } from './i18n/I18nContext';
import { healthApi, API_BASE_URL, describeError } from './services/api';
import './App.css';

const MODULES = [
  { id: 'molecular', labelKey: 'nav.molecular', Panel: MolecularPanel },
  { id: 'thermal', labelKey: 'nav.thermal', Panel: ThermalPanel },
  { id: 'mechanical', labelKey: 'nav.mechanical', Panel: MechanicalPanel },
  { id: 'rheology', labelKey: 'nav.rheology', Panel: RheologyPanel },
  { id: 'structure', labelKey: 'nav.structure', Panel: StructurePanel },
];

function LanguageSwitcher() {
  const { language, setLanguage, t } = useI18n();
  return (
    <label className="lang-switcher">
      <span className="lang-label">{t('common.language')}</span>
      <select value={language} onChange={(e) => setLanguage(e.target.value)}>
        {LANGUAGES.map(({ code, label }) => (
          <option key={code} value={code}>
            {label}
          </option>
        ))}
      </select>
    </label>
  );
}

function Shell() {
  const { t } = useI18n();
  const [active, setActive] = useState('molecular');
  const [online, setOnline] = useState(null);
  const [apiError, setApiError] = useState('');

  // Probe the backend once on mount so a misconfigured deployment is visible
  // before the user spends time pasting data.
  React.useEffect(() => {
    let cancelled = false;
    healthApi
      .check()
      .then(() => {
        if (!cancelled) setOnline(true);
      })
      .catch((err) => {
        if (!cancelled) {
          setOnline(false);
          setApiError(describeError(err));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const ActivePanel = MODULES.find((m) => m.id === active)?.Panel;

  return (
    <div className="App">
      <header>
        <div className="header-top">
          <div>
            <h1>{t('app.title')}</h1>
            <p className="subtitle">{t('app.subtitle')}</p>
          </div>
          <LanguageSwitcher />
        </div>
        <p className="tagline">{t('app.tagline')}</p>
        <ApiStatus online={online} error={apiError} />
      </header>

      <nav className="module-nav">
        {MODULES.map((m) => (
          <button
            key={m.id}
            type="button"
            className={active === m.id ? 'nav-tab active' : 'nav-tab'}
            onClick={() => setActive(m.id)}
          >
            {t(m.labelKey)}
          </button>
        ))}
      </nav>

      <main>{ActivePanel ? <ActivePanel /> : null}</main>

      <footer>
        <p>
          {t('app.footer.developed')} <strong>Eliandro P. Teles</strong> ·{' '}
          <a href="https://github.com/teles-eliandro/polymer-analysis-toolkit" target="_blank" rel="noopener noreferrer">
            {t('app.footer.repo')}
          </a>{' '}
          ·{' '}
          <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noopener noreferrer">
            {t('app.footer.docs')}
          </a>
        </p>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <I18nProvider>
      <Shell />
    </I18nProvider>
  );
}
