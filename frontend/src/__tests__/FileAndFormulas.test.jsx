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
  thermalApi: {
    tga: jest.fn(),
    dsc: jest.fn(),
    importFile: jest.fn(),
    analyseFile: jest.fn(),
  },
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

  test('upload mode hands the File object over without reading it', async () => {
    // The molar-mass importer runs on the server and sniffs the vendor
    // convention from the bytes, so the browser must not pre-parse the file.
    const onFile = jest.fn();
    renderWithI18n(<FileDrop onFile={onFile} onError={jest.fn()} />);

    const input = document.querySelector('input[type="file"]');
    const file = new File(['massa;fracao\n1000;0,2\n'], 'export.csv', { type: 'text/csv' });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => expect(onFile).toHaveBeenCalledTimes(1));
    expect(onFile.mock.calls[0][0]).toBe(file);
  });

  test('upload mode accepts extensions the text mode refuses', async () => {
    const onFile = jest.fn();
    const onError = jest.fn();
    renderWithI18n(<FileDrop onFile={onFile} onError={onError} />);

    const input = document.querySelector('input[type="file"]');
    const file = new File(['1\t2\n'], 'report.prn', { type: 'text/plain' });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => expect(onFile).toHaveBeenCalled());
    expect(onError.mock.calls.map((c) => c[0]).filter(Boolean)).toHaveLength(0);
  });

  test('upload mode still refuses a format the importer cannot read', async () => {
    const onFile = jest.fn();
    const onError = jest.fn();
    renderWithI18n(<FileDrop onFile={onFile} onError={onError} />);

    const input = document.querySelector('input[type="file"]');
    const file = new File([new Uint8Array([1, 2, 3])], 'scan.xlsx', {
      type: 'application/vnd.ms-excel',
    });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => expect(onError).toHaveBeenCalled());
    const messages = onError.mock.calls.map((c) => c[0]).filter(Boolean);
    expect(messages.some((m) => m.includes('.xlsx'))).toBe(true);
    expect(onFile).not.toHaveBeenCalled();
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
  /**
   * The file goes to the server, which decides what each column is.
   *
   * The previous version of this test asserted that the panel parsed the file
   * itself and rebuilt a two-column text from the first two numbers on each
   * line. That is the defect: on a NETZSCH export the second column is time,
   * so the trace reaching the analysis was temperature against time, in the
   * wrong unit, with nothing reporting it. The assertion below is the inverse
   * -- the reader's own verdict on the axes must be the one displayed.
   */
  test('sends the file to the server reader and shows the resolved axes', async () => {
    const { thermalApi } = require('../services/api');
    thermalApi.importFile.mockResolvedValue({
      data: {
        x_label: 'Temp./°C',
        y_label: 'DSC/(mW/mg)',
        temperature: [27.4, 50.0, 107.3, 150.0, 194.4],
        signal: [-0.05, 0.2, 0.67, 0.3, 0.02],
        n_values: 5,
        sample_name: '20-100',
        sample_mass_mg: 4.75,
        heating_rate_K_min: 10,
        notes: [],
        refusals: [],
      },
    });
    renderWithI18n(<ThermalPanel />);

    const file = new File(['#SAMPLE:20-100\n##Temp./°C;Time/min;DSC/(mW/mg)\n27.4;91;0.1\n'], 'dsc.txt', {
      type: 'text/plain',
    });
    const input = document.querySelector('input[type="file"]');
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(thermalApi.importFile).toHaveBeenCalled();
    });
    // The two axes the reader resolved are what the panel reports, so a
    // mis-read column is visible rather than implied by a plausible plot.
    // Both must also reach the trace box, whose header is what identifies
    // each column if the text is ever re-read.
    await waitFor(() => {
      expect(screen.getAllByText(/DSC\/\(mW\/mg\)/).length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText(/Temp\.\/°C/).length).toBeGreaterThan(0);
    expect(screen.getByText(/20-100/)).toBeTruthy();
    const area = document.querySelector('textarea');
    expect(area.value).toContain('##Temp./°C');
    expect(area.value).toContain('DSC/(mW/mg)');
    expect(area.value.split('\n').length).toBe(6);
  });

  test('reports a server failure instead of showing an empty plot', async () => {
    const { thermalApi } = require('../services/api');
    thermalApi.importFile.mockRejectedValue(new Error('no numeric columns'));
    renderWithI18n(<ThermalPanel />);
    const file = new File(['not,a,number\nhere,either,at,all\n'], 'junk.csv', {
      type: 'text/csv',
    });
    const input = document.querySelector('input[type="file"]');
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toMatch(/no numeric columns/);
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
