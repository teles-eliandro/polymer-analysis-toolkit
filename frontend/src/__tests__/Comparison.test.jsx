/**
 * The comparison verdicts must be distinguishable on screen.
 *
 * The failure this guards is specific: a tri-state verdict is easy to build in
 * the backend and then flatten in the UI to "in range / not in range", which
 * turns "we could not compare this" into "this is out of range" -- a claim
 * about the sample that the data does not support. So each of the three states
 * is asserted separately, including that the third one renders.
 *
 * The reference ranges are data with citations, so the row must also surface
 * the source: an unverifiable range is no better than no range.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';

jest.mock('react-plotly.js', () => {
  const R = require('react');
  return {
    __esModule: true,
    default: R.forwardRef((props, ref) => {
      R.useImperativeHandle(ref, () => ({ toImage: jest.fn() }));
      return R.createElement('div', { 'data-testid': 'plot' });
    }),
  };
});

jest.mock('../services/api', () => ({
  API_BASE_URL: 'http://test.local',
  describeError: (e) => `error: ${e}`,
  healthApi: { check: jest.fn() },
  thermalApi: { tga: jest.fn(), dsc: jest.fn() },
  molecularApi: { analyse: jest.fn() },
  mechanicalApi: { analyse: jest.fn() },
  rheologyApi: { analyse: jest.fn() },
  structureApi: { analyse: jest.fn() },
}));

const { thermalApi, healthApi } = jest.requireMock('../services/api');

const row = (over) => ({
  property: 'Tg',
  verdict: 'within',
  measured: 100.0,
  unit: '°C',
  reference_low: 80,
  reference_high: 110,
  reference_unit: '°C',
  reference_source: 'Brandrup et al., Polymer Handbook, 4th ed.',
  reference_method: 'DSC',
  reference_note: null,
  reason: null,
  polymer: 'PS',
  ...over,
});

const payload = (comparisons) => ({
  Tg: 100.0,
  Tg_onset: 95,
  Tg_end: 105,
  Tm: null,
  delta_Hm: null,
  delta_cp: 0.2,
  crystallinity_pct: null,
  Tg_uncertainty_C: 0.4,
  Tg_reliable: true,
  temperature: [30, 100, 170, 200],
  heat_flow: [0, 0.1, 0.5, 0],
  claims: {},
  comparisons,
});

beforeEach(() => {
  healthApi.check.mockImplementation(() => Promise.resolve({ data: { status: 'ok' } }));
  thermalApi.tga.mockImplementation(() => Promise.resolve({ data: null }));
});

const analyseDsc = async () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: 'Thermal' }));
  fireEvent.click(screen.getByRole('tab', { name: /dsc/i }));
  fireEvent.change(document.querySelector('textarea'), {
    target: { value: '30,0\n100,0.1\n170,0.5\n200,0' },
  });
  fireEvent.click(screen.getByRole('button', { name: /calculate/i }));
  await waitFor(() => expect(screen.getByTestId('plot')).toBeInTheDocument());
};

describe('Comparison against published values', () => {
  const rows = () => Array.from(document.querySelectorAll('.comparison'));

  it('shows a within-range verdict distinctly', async () => {
    thermalApi.dsc.mockImplementation(() =>
      Promise.resolve({ data: payload([row({})]) }),
    );
    await analyseDsc();

    expect(rows()).toHaveLength(1);
    expect(rows()[0].className).toMatch(/verdict-within/);
    expect(rows()[0].textContent).toMatch(/within range/i);
    expect(rows()[0].textContent).toMatch(/80–110/);
  });

  it('shows an outside-range verdict distinctly', async () => {
    thermalApi.dsc.mockImplementation(() =>
      Promise.resolve({
        data: payload([row({ verdict: 'outside', measured: 176.3, polymer: 'PP' })]),
      }),
    );
    await analyseDsc();

    expect(rows()[0].className).toMatch(/verdict-outside/);
    expect(rows()[0].textContent).toMatch(/outside range/i);
    // Must not be confused with the neutral state.
    expect(rows()[0].className).not.toMatch(/verdict-none/);
  });

  it('renders the third state and its reason, not as a failure', async () => {
    thermalApi.dsc.mockImplementation(() =>
      Promise.resolve({
        data: payload([
          row({
            verdict: 'not_comparable',
            measured: 75.9,
            reference_low: null,
            reference_high: null,
            reference_source: null,
            reason:
              'No published range for Tm of PS is held in the reference repertoire.',
          }),
        ]),
      }),
    );
    await analyseDsc();

    expect(rows()[0].className).toMatch(/verdict-none/);
    expect(rows()[0].textContent).toMatch(/not comparable/i);
    // The reason must reach the reader: it is the whole content of the verdict.
    expect(rows()[0].textContent).toMatch(/No published range/);
    // And it must not be presented as a range violation.
    expect(rows()[0].className).not.toMatch(/verdict-outside/);
  });

  it('names the source of every range it uses', async () => {
    thermalApi.dsc.mockImplementation(() =>
      Promise.resolve({ data: payload([row({})]) }),
    );
    await analyseDsc();

    // An unverifiable range is no better than no range.
    expect(rows()[0].textContent).toMatch(/Polymer Handbook/);
    expect(rows()[0].textContent).toMatch(/Source/);
  });

  it('renders nothing when the backend sends no comparisons', async () => {
    thermalApi.dsc.mockImplementation(() =>
      Promise.resolve({ data: payload([]) }),
    );
    await analyseDsc();

    expect(document.querySelector('.comparison-panel')).toBeNull();
  });

  it('sends the sample name so the comparison can be made at all', async () => {
    thermalApi.dsc.mockImplementation(() =>
      Promise.resolve({ data: payload([row({})]) }),
    );
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Thermal' }));
    fireEvent.click(screen.getByRole('tab', { name: /dsc/i }));
    fireEvent.change(document.querySelector('textarea'), {
      target: { value: '30,0\n100,0.1\n170,0.5\n200,0' },
    });
    const nameInput = screen.getByPlaceholderText(/PLA1-AR/);
    fireEvent.change(nameInput, { target: { value: 'PS5-AR' } });
    fireEvent.click(screen.getByRole('button', { name: /calculate/i }));
    await waitFor(() => expect(screen.getByTestId('plot')).toBeInTheDocument());

    const call = thermalApi.dsc.mock.calls[0];
    expect(call[2]).toMatchObject({ sampleName: 'PS5-AR' });
  });
});
