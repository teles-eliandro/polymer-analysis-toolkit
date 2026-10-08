/**
 * The footing under Tg has to reach the screen.
 *
 * A backend field nobody renders helps nobody. These assert the DSC panel
 * shows the uncertainty beside the glass transition, and that an unstable
 * value is marked as such rather than looking exactly like a good one.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';

jest.mock('react-plotly.js', () => {
  // Required inside the factory: jest.mock may not close over outer variables.
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

const baseResult = (over) => ({
  Tg: 75.0,
  Tg_onset: 70,
  Tg_end: 80,
  Tm: 170.0,
  delta_Hm: 40.0,
  delta_cp: 0.2,
  crystallinity_pct: 30.0,
  temperature: [30, 100, 170, 200],
  heat_flow: [0, 0.1, 0.5, 0],
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

describe('Tg footing on screen', () => {
  // Scoped to the footing element: the page carries other prose that happens
  // to contain these words, so a document-wide match proves nothing.
  const footing = () => document.querySelector('.stat-footing');

  it('shows the uncertainty beside the glass transition', async () => {
    thermalApi.dsc.mockImplementation(() =>
      Promise.resolve({ data: baseResult({ Tg_uncertainty_C: 0.17, Tg_reliable: true }) }),
    );
    await analyseDsc();
    expect(footing()).not.toBeNull();
    expect(footing().textContent).toMatch(/±0\.2|±0\.1/);
  });

  it('marks an unstable glass transition so it cannot pass for a good one', async () => {
    thermalApi.dsc.mockImplementation(() =>
      Promise.resolve({ data: baseResult({ Tg_uncertainty_C: 3.85, Tg_reliable: false }) }),
    );
    await analyseDsc();
    expect(footing()).not.toBeNull();
    expect(footing().textContent).toMatch(/unstable/i);
    expect(footing().textContent).toMatch(/±3\.9|±3\.8/);
    // The warning is what makes it impossible to mistake for a good value.
    expect(footing().className).toMatch(/warn/);
  });

  it('says nothing when the backend reports no footing', async () => {
    thermalApi.dsc.mockImplementation(() => Promise.resolve({ data: baseResult({}) }));
    await analyseDsc();
    expect(footing()).toBeNull();
  });
});
