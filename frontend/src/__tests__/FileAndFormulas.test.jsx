/**
 * Tests for the file-upload route and the formula/model disclosure.
 *
 * These assert behaviour that a build and a curl cannot see: that a file
 * reaches the same parser as a pasted trace, and that the formulas are
 * actually present in the rendered output. A build compiles regardless, and
 * the formulas are the one part of the interface a user is told to check the
 * numbers against, so their absence would be silent.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import fs from 'fs';
import path from 'path';

import { I18nProvider } from '../i18n/I18nContext';
import ThermalPanel from '../components/ThermalPanel';
import FileDrop from '../components/FileDrop';
import { Formula, FormulaDisclosure } from '../components/Formula';

jest.mock('../services/api', () => ({
  thermalApi: { tga: jest.fn(), dsc: jest.fn() },
  describeError: (e) => String(e),
}));

const renderWithI18n = (ui) => render(<I18nProvider>{ui}</I18nProvider>);

describe('FileDrop', () => {
  test('reads a CSV file and returns its text', async () => {
    const onText = jest.fn();
    renderWithI18n(<FileDrop onText={onText} onError={jest.fn()} />);

    const input = document.querySelector('input[type="file"]');
    const file = new File(['30\t100\n350\t85\n500\t40\n'], 'trace.csv', {
      type: 'text/csv',
    });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => expect(onText).toHaveBeenCalled());
    expect(onText.mock.calls[0][0]).toContain('350');
    expect(onText.mock.calls[0][1].name).toBe('trace.csv');
  });

  test('rejects an extension it cannot parse, with the extension named', async () => {
    const onText = jest.fn();
    const onError = jest.fn();
    renderWithI18n(<FileDrop onText={onText} onError={onError} />);

    const input = document.querySelector('input[type="file"]');
    const file = new File(['binary'], 'scan.raw', { type: 'application/octet-stream' });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => expect(onError).toHaveBeenCalled());
    // The first call clears any previous message; the rejection follows.
    const messages = onError.mock.calls.map((c) => c[0]).filter(Boolean);
    expect(messages.some((m) => m.includes('.raw'))).toBe(true);
    expect(onText).not.toHaveBeenCalled();
  });
});

describe('formula disclosure', () => {
  test('keeps the expressions in the DOM while collapsed', () => {
    renderWithI18n(
      <FormulaDisclosure title="Formulas">
        <Formula name="Scherrer" expression="D = K λ / (β cos θ)" reference="Ref A" />
      </FormulaDisclosure>,
    );
    // Present but hidden: in-page search and assistive tech still reach it.
    const body = document.querySelector('.formula-body');
    expect(body).not.toBeNull();
    expect(body.hasAttribute('hidden')).toBe(true);
    expect(body.textContent).toContain('K λ / (β cos θ)');
  });

  test('reveals the expressions when opened', () => {
    renderWithI18n(
      <FormulaDisclosure title="Formulas">
        <Formula name="Scherrer" expression="D = K λ / (β cos θ)" reference="Ref A" />
      </FormulaDisclosure>,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(document.querySelector('.formula-body').hasAttribute('hidden')).toBe(false);
  });

  test('renders each symbol and the literature reference', () => {
    renderWithI18n(
      <Formula
        name="Scherrer equation"
        expression="D = K λ / (β cos θ)"
        symbols={[
          { symbol: 'K', meaning: 'shape factor' },
          { symbol: 'β', meaning: 'peak width at half maximum' },
        ]}
        reference="Scherrer (1918)"
      />,
    );
    expect(screen.getByText('Scherrer equation')).toBeTruthy();
    expect(screen.getByText('shape factor')).toBeTruthy();
    expect(screen.getByText('peak width at half maximum')).toBeTruthy();
    expect(screen.getByText(/Scherrer \(1918\)/)).toBeTruthy();
  });
});

describe('ThermalPanel file route', () => {
  test('fills the trace box from a file so both routes share one parser', async () => {
    renderWithI18n(<ThermalPanel />);

    const csv = '30,100\n100,99\n350,85\n500,40\n800,10\n';
    const file = new File([csv], 'pei.csv', { type: 'text/csv' });
    const input = document.querySelector('input[type="file"]');
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      const area = document.querySelector('textarea');
      expect(area.value).toContain('350');
      expect(area.value.split('\n').length).toBe(5);
    });
    // The load is reported, not silent.
    expect(screen.getByRole('status').textContent).toMatch(/5/);
  });

  test('reports a file with no numeric pairs instead of sending nothing', async () => {
    renderWithI18n(<ThermalPanel />);
    const file = new File(['not,a,number\nhere,either,at,all\n'], 'junk.csv', {
      type: 'text/csv',
    });
    const input = document.querySelector('input[type="file"]');
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toMatch(/junk\.csv/);
    });
  });

  test('shows the TGA and DSC formulas with their standards', () => {
    renderWithI18n(<ThermalPanel />);
    const panel = document.querySelector('.panel');

    // Open the disclosure and check the container holds every expression.
    fireEvent.click(within(panel).getByRole('button', { name: /Formulas|Fórmulas/i }));
    const text = document.querySelector('.formula-body').textContent;

    expect(text).toContain('DTG(T) = −dm/dT');
    expect(text).toContain('Xc (%) = 100 · ΔHm / ΔHm°');
    expect(text).toContain('ASTM E1131');
    expect(text).toContain('ISO 11358-1');
    expect(text).toContain('ASTM E793');
    expect(text).toContain('Kong & Hay');
  });
});

describe('responsive stylesheet', () => {
  // A missing stylesheet is invisible to every other test: the component tree
  // renders, the build passes, and the page just looks unstyled on a phone.
  const css = fs.readFileSync(
    path.resolve(__dirname, '..', 'App.css'),
    'utf8',
  );

  test('styles every class the panels actually use', () => {
    const required = [
      'stat-grid',
      'data-table',
      'table-wrap',
      'field-label',
      'module-nav',
      'disclosure-toggle',
      'formula-expression',
      'file-drop',
      'error-message',
      'api-status',
    ];
    const missing = required.filter((c) => !css.includes(`.${c}`));
    expect(missing).toEqual([]);
  });

  test('has breakpoints for small screens and larger ones', () => {
    const breakpoints = [...css.matchAll(/@media[^{]*min-width:\s*(\d+)px/g)].map(
      (m) => Number(m[1]),
    );
    expect(breakpoints.some((b) => b <= 600)).toBe(true);
    expect(breakpoints.some((b) => b >= 900)).toBe(true);
  });

  test('lets grid tracks shrink below their content width', () => {
    // min-width: auto on a grid/flex child is what makes a long value push the
    // page sideways; minmax(0, 1fr) is what prevents it.
    expect(css).toMatch(/minmax\(0,\s*1fr\)/);
    expect(css).toContain('min-width: 0');
  });

  test('keeps wide tables scrolling inside their own container', () => {
    expect(css).toMatch(/\.table-wrap\s*\{[^}]*overflow-x:\s*auto/s);
  });

  test('uses a 16px base font so iOS does not zoom on focus', () => {
    const inputs = css.match(/font-size:\s*16px/g) || [];
    expect(inputs.length).toBeGreaterThan(0);
  });
});
