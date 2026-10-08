/**
 * Tests for exporting the plot as an image, plus the combined results bundle.
 *
 * The user asked for the results to be downloadable "including the graph".
 * A JSON export already existed but carried no picture -- the numbers without
 * the curve they were read off are not much use in a report.
 *
 * What these assert:
 *
 *  1. An image button exists after an analysis and, when clicked, actually
 *     calls the plot's own image export (Plotly's toImage) with PNG format --
 *     not a no-op.
 *  2. The download carries a real filename ending in .png.
 *  3. When the plot cannot produce an image, the page degrades instead of
 *     throwing -- a failed export must not take the results down with it.
 *
 * The plot is mocked, as in the other render tests: plotly cannot initialise
 * under jsdom. The mock exposes toImage as a jest.fn so the call can be seen.
 *
 * Mock re-arming in beforeEach follows ThermalModeAndClear.test.jsx: CRA's
 * jest config resets implementations between tests, and the app calls
 * healthApi on mount.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';

const mockToImage = jest.fn(() =>
  Promise.resolve('data:image/png;base64,iVBORw0KGgo='),
);

jest.mock('react-plotly.js', () => {
  // Required inside the factory: jest.mock may not close over outer variables
  // unless the name is prefixed with `mock`.
  const R = require('react');
  return {
    __esModule: true,
    default: R.forwardRef((props, ref) => {
      // Hand the parent the same surface a real <Plot> gives it.
      R.useImperativeHandle(ref, () => ({ toImage: mockToImage }));
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

const DSC_RESULT = {
  Tg: 100.0,
  Tm: 170.0,
  delta_Hm: 40.0,
  delta_cp: 0.2,
  crystallinity_pct: 30.0,
  temperature: [30, 100, 170, 200],
  heat_flow: [0, 0.1, 0.5, 0],
};

beforeEach(() => {
  mockToImage.mockClear();
  healthApi.check.mockImplementation(() => Promise.resolve({ data: { status: 'ok' } }));
  thermalApi.dsc.mockImplementation(() => Promise.resolve({ data: DSC_RESULT }));
  thermalApi.tga.mockImplementation(() => Promise.resolve({ data: null }));
});

const IMAGE_BUTTON = /download.*(png|image)|(png|image).*download/i;

/** Open the thermal module, pick DSC, paste a trace and analyse it. */
const analyseDsc = async () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: 'Thermal' }));
  // The TGA/DSC switch is a tablist, not a pair of buttons.
  fireEvent.click(screen.getByRole('tab', { name: /dsc/i }));
  const box = document.querySelector('textarea');
  fireEvent.change(box, { target: { value: '30,0\n100,0.1\n170,0.5\n200,0' } });
  fireEvent.click(screen.getByRole('button', { name: /calculate/i }));
  await waitFor(() => expect(screen.getByTestId('plot')).toBeInTheDocument());
};

describe('plot image export', () => {
  it('offers an image download once a result is on screen', async () => {
    await analyseDsc();
    expect(screen.getByRole('button', { name: IMAGE_BUTTON })).toBeInTheDocument();
  });

  it('asks the plot for a PNG, with a .png filename', async () => {
    await analyseDsc();
    fireEvent.click(screen.getByRole('button', { name: IMAGE_BUTTON }));

    await waitFor(() => expect(mockToImage).toHaveBeenCalled());
    const [opts] = mockToImage.mock.calls[0];
    expect(opts.format).toBe('png');
    expect(opts.filename).toMatch(/\.png$/);
  });

  it('keeps the page alive when the plot cannot produce an image', async () => {
    mockToImage.mockRejectedValueOnce(new Error('no canvas'));
    await analyseDsc();

    fireEvent.click(screen.getByRole('button', { name: IMAGE_BUTTON }));

    // A failed export is not a crash: the button and the plot remain.
    await waitFor(() =>
      expect(screen.getByRole('button', { name: IMAGE_BUTTON })).toBeInTheDocument(),
    );
    expect(screen.getByTestId('plot')).toBeInTheDocument();
  });
});

describe('combined results + graph download', () => {
  const BUNDLE = /download results|\.zip/i;

  it('offers a combined download alongside the image one', async () => {
    await analyseDsc();
    expect(screen.getByRole('button', { name: BUNDLE })).toBeInTheDocument();
  });

  it('builds the bundle without throwing when the plot cannot render', async () => {
    mockToImage.mockRejectedValueOnce(new Error('no canvas'));
    await analyseDsc();
    // Must not reject: the numbers are still worth downloading.
    fireEvent.click(screen.getByRole('button', { name: BUNDLE }));
    await waitFor(() =>
      expect(screen.getByRole('button', { name: BUNDLE })).toBeInTheDocument(),
    );
    expect(screen.getByTestId('plot')).toBeInTheDocument();
  });
});
