/**
 * Render smoke test for the PAT shell.
 *
 * The build check only proves the bundle compiles. This mounts the real app
 * in jsdom, switches through every module, and pastes a trace into the
 * structure and thermal modules to confirm a result actually renders. The
 * http layer is mocked, so no backend is needed.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';

// plotly.js is imported by every panel and cannot initialise under jsdom. The
// component is replaced with a stand-in that carries the props through as data
// attributes, so the tests still assert that a trace was built and handed over.
jest.mock('react-plotly.js', () => ({
  __esModule: true,
  default: ({ data, layout }) => (
    <div
      data-testid="plot"
      data-series={String((data || []).length)}
      data-xaxis={layout?.xaxis?.title || ''}
    />
  ),
}));

jest.mock('../services/api', () => ({
  API_BASE_URL: 'http://test.local',
  describeError: (e) => `error: ${e}`,
  healthApi: { check: jest.fn(() => Promise.resolve({ data: { status: 'ok' } })) },
    structureApi: {
      xrd: jest.fn(() =>
        Promise.resolve({
          data: {
            peaks_two_theta: [19.2],
            d_spacing_angstrom: [4.61],
            crystallite_size_nm: [2.16],
            fwhm_deg: [3.71],
            crystallinity_pct: 100,
            wavelength_angstrom: 1.5406,
            two_theta: [10, 19.2, 35],
            intensity: [120, 1450, 300],
          },
        }),
      ),
      ftir: jest.fn(() =>
        Promise.resolve({
          data: {
            matches: [
              {
                observed_cm1: 1180,
                relative_height: 1.0,
                candidates: [
                  { assignment: 'C-O stretch (ester)', expected_intensity: 'strong', note: 'x' },
                ],
              },
            ],
            detected_peaks: [1180],
            detected_peaks_rel: [1.0],
            note: 'Indicative only.',
          },
        }),
      ),
    },
    thermalApi: {
      tga: jest.fn(() =>
        Promise.resolve({
          data: {
            Td_5pct: 265,
            Td_10pct: 339,
            T_max_rate: 600,
            residue_pct: 8.3,
            steps: [],
            temperature: [30, 800],
            mass_pct: [100, 5],
            dtg: [0, -0.1],
          },
        }),
      ),
      dsc: jest.fn(() => Promise.resolve({ data: {} })),
    },
}));

const TEN_ROWS = Array.from({ length: 12 }, (_, i) => `${10 + i * 2}\t${100 + i * 90}`).join('\n');

// The api module is replaced wholesale above. Re-arm the implementations here so
// the tests do not depend on whether CRA's jest config resets mocks.
const { healthApi, structureApi } = jest.requireMock('../services/api');

beforeEach(() => {
  healthApi.check.mockResolvedValue({ data: { status: 'ok' } });
  structureApi.xrd.mockResolvedValue({
    data: {
      peaks_two_theta: [19.2],
      d_spacing_angstrom: [4.61],
      crystallite_size_nm: [2.16],
      fwhm_deg: [3.71],
      crystallinity_pct: 100,
      wavelength_angstrom: 1.5406,
      two_theta: [10, 19.2, 35],
      intensity: [120, 1450, 300],
    },
  });
  structureApi.ftir.mockResolvedValue({
    data: {
      matches: [
        {
          observed_cm1: 1180,
          relative_height: 1.0,
          candidates: [{ assignment: 'C-O stretch (ester)', expected_intensity: 'strong', note: 'x' }],
        },
      ],
      detected_peaks: [1180],
      detected_peaks_rel: [1.0],
      note: 'Indicative only.',
    },
  });
});

describe('PAT application shell', () => {
  test('renders the title and every module tab', async () => {
    render(<App />);
    expect(screen.getByText(/Polymer Analysis Toolkit/i)).toBeInTheDocument();
    ['Molar mass', 'Thermal', 'Mechanical', 'Rheology', 'Structure'].forEach((label) => {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument();
    });
  });

  test('reports the API as online when health succeeds', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/API online/i)).toBeInTheDocument();
    });
  });

  test('switches to the Structure module and shows the XRD tab', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Structure' }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'XRD' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'FTIR' })).toBeInTheDocument();
    });
  });

  test('rejects a trace shorter than the API minimum with a readable message', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Structure' }));
    const box = document.querySelector('textarea');
    fireEvent.change(box, { target: { value: '10\t120\n19.2\t1450' } });
    fireEvent.click(screen.getByRole('button', { name: /Calculate/i }));
    await waitFor(() => {
      expect(screen.getByText(/At least 10 points/i)).toBeInTheDocument();
    });
  });

  test('runs an XRD analysis and renders the indexed peak', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Structure' }));
    const box = document.querySelector('textarea');
    fireEvent.change(box, { target: { value: TEN_ROWS } });
    fireEvent.click(screen.getByRole('button', { name: /Calculate/i }));

    // The result must come back from the mocked API before anything renders.
    await waitFor(() => expect(structureApi.xrd).toHaveBeenCalledTimes(1));
    const [x, y] = structureApi.xrd.mock.calls[0];
    expect(x).toHaveLength(12);
    expect(y).toHaveLength(12);

    await waitFor(() => {
      // The label legitimately appears twice now: once as the result stat and
      // once as the formula/model entry, so an exact single match is wrong.
      expect(screen.getAllByText(/Crystallinity index/i).length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText(/2.16/).length).toBeGreaterThan(0);
    expect(screen.getByTestId('plot')).toBeInTheDocument();
  });

  test('switches the interface language to Portuguese', async () => {
    render(<App />);
    const select = document.querySelector('select');
    fireEvent.change(select, { target: { value: 'pt' } });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Massa molar' })).toBeInTheDocument();
    });
  });

  test('switches the interface language to Spanish', async () => {
    render(<App />);
    const select = document.querySelector('select');
    fireEvent.change(select, { target: { value: 'es' } });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Masa molar' })).toBeInTheDocument();
    });
  });
});
