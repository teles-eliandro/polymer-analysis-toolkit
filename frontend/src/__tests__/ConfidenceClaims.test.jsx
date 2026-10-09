/**
 * The confidence rung and the evidence behind a value must reach the screen.
 *
 * The backend returns every number with a confidence rung and, for a suggested
 * transition, the observations that produced it. None of that helps if the
 * panel renders a bare float: a Tg that is an inference would then look exactly
 * like a Tg that is a measurement, which is the failure mode the whole rung
 * ladder exists to prevent.
 *
 * These assert three things a reader needs:
 *   1. a suggested transition is visibly labelled as suggested;
 *   2. the basis is reachable from the value, not buried elsewhere;
 *   3. a panel given no claims renders no badge, rather than an empty one.
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

const withClaims = (over) => ({
  Tg: 98.2,
  Tg_onset: 95,
  Tg_end: 101,
  Tm: null,
  delta_Hm: null,
  delta_cp: 0.21,
  crystallinity_pct: null,
  Tg_uncertainty_C: 0.4,
  Tg_reliable: true,
  temperature: [30, 100, 170, 200],
  heat_flow: [0, 0.1, 0.5, 0],
  claims: {
    Tg: {
      value: 98.2,
      confidence: 'suggested',
      evidence: ['ASTM D3418 midpoint of 95.0 and 101.0 C'],
      note: 'A suggested glass transition, not a measurement.',
    },
    delta_cp: {
      value: 0.21,
      confidence: 'formula',
      evidence: ['step between the plateaux flanking the transition'],
      note: 'Derived from the suggested Tg.',
    },
  },
  ...over,
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

describe('Confidence rungs on screen', () => {
  const rungs = () => Array.from(document.querySelectorAll('.rung'));
  const rungFor = (word) =>
    rungs().find((el) => el.textContent.trim().toLowerCase() === word);

  it('labels a suggested transition as suggested', async () => {
    thermalApi.dsc.mockImplementation(() => Promise.resolve({ data: withClaims({}) }));
    await analyseDsc();

    const suggested = rungFor('suggested');
    expect(suggested).toBeTruthy();
    // A suggested value must be visually distinct from a read/formula one, not
    // merely present: the class is what carries the colour.
    expect(suggested.className).toMatch(/rung-suggested/);
  });

  it('distinguishes a formula result from a suggestion', async () => {
    thermalApi.dsc.mockImplementation(() => Promise.resolve({ data: withClaims({}) }));
    await analyseDsc();

    const formula = rungFor('formula');
    expect(formula).toBeTruthy();
    expect(formula.className).toMatch(/rung-formula/);
    // The two kinds of claim must not render identically.
    expect(formula.className).not.toMatch(/rung-suggested/);
  });

  it('makes the basis of a suggestion reachable from the value', async () => {
    thermalApi.dsc.mockImplementation(() => Promise.resolve({ data: withClaims({}) }));
    await analyseDsc();

    const toggle = document.querySelector('.claim-toggle');
    expect(toggle).not.toBeNull();
    expect(toggle.getAttribute('aria-expanded')).toBe('false');

    fireEvent.click(toggle);

    const list = document.querySelector('.claim-list');
    expect(list).not.toBeNull();
    expect(list.textContent).toMatch(/ASTM D3418/);
    // The caveat travels with the evidence.
    expect(list.textContent).toMatch(/not a measurement/i);
  });

  it('renders no badge when the backend sends no claims', async () => {
    // Older payloads, or a module that has not been given claims yet.
    thermalApi.dsc.mockImplementation(() =>
      Promise.resolve({ data: withClaims({ claims: {} }) }),
    );
    await analyseDsc();

    expect(rungs()).toHaveLength(0);
    expect(document.querySelector('.claim-toggle')).toBeNull();
  });

  it('shows an unknown rung rather than crashing on it', async () => {
    // Forward compatibility: a rung the frontend does not know about must not
    // take the panel down, because the backend may add one.
    thermalApi.dsc.mockImplementation(() =>
      Promise.resolve({
        data: withClaims({
          claims: {
            Tg: {
              value: 98.2,
              confidence: 'estimated',
              evidence: ['something new'],
              note: null,
            },
          },
        }),
      }),
    );
    await analyseDsc();

    const badge = rungs().find((el) => el.textContent.trim() === 'estimated');
    expect(badge).toBeTruthy();
    expect(badge.className).toMatch(/rung-suggested/);
  });
});
