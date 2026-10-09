/**
 * Tests for the thermal module's mode clarity and clear button.
 *
 * The two things a user complained about, turned into assertions:
 *
 *  1. It was not obvious whether the trace they loaded would be analysed as
 *     TGA or DSC. A build test cannot see this -- the panel renders either
 *     way. What is asserted here is that the *rendered text* names the active
 *     mode and says what the second column will be read as, and that the text
 *     changes when the mode changes.
 *
 *  2. There was no way to empty the input area. The clear button must wipe
 *     both the trace and any result on screen, since a cleared textarea
 *     sitting above a stale plot is not actually clear.
 *
 * Rendered through <App /> like the other render tests, so the module nav and
 * the i18n provider are the real ones.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';

jest.mock('react-plotly.js', () => ({
  __esModule: true,
  default: () => <div data-testid="plot" />,
}));

jest.mock('../services/api', () => ({
  API_BASE_URL: 'http://test.local',
  describeError: (e) => `error: ${e}`,
  healthApi: { check: jest.fn(() => Promise.resolve({ data: { status: 'ok' } })) },
  thermalApi: {
    tga: jest.fn(() =>
      Promise.resolve({
        data: {
          Td_5pct: 350,
          Td_10pct: 380,
          T_max_rate: 400,
          residue_pct: 10,
          steps: [],
          temperature: [30, 400, 800],
          mass_pct: [100, 50, 10],
          dtg: [0, 1, 0],
        },
      }),
    ),
    dsc: jest.fn(() =>
      Promise.resolve({
        data: {
          Tg: 100,
          Tm: null,
          delta_cp: 0.24,
          temperature: [30, 180],
          heat_flow: [-0.13, -0.2],
        },
      }),
    ),
  },
}));

const { thermalApi, healthApi } = jest.requireMock('../services/api');

// The api module is replaced wholesale by the mock above. Re-arm the
// implementations before every test, following the pattern in
// App.render.test.jsx: CRA's jest config resets mock implementations between
// tests, and the app calls healthApi on mount, so an un-armed mock makes
// healthApi.check() return undefined and throw before any assertion runs.
beforeEach(() => {
  healthApi.check.mockImplementation(() => Promise.resolve({ data: { status: 'ok' } }));
  thermalApi.tga.mockImplementation(() =>
    Promise.resolve({
      data: {
        Td_5pct: 350,
        Td_10pct: 380,
        T_max_rate: 400,
        residue_pct: 10,
        steps: [],
        temperature: [30, 400, 800],
        mass_pct: [100, 50, 10],
        dtg: [0, 1, 0],
      },
    }),
  );
});

const TGA_ROWS = Array.from({ length: 12 }, (_, i) => `${30 + i * 60}\t${100 - i * 8}`).join('\n');

const openThermal = () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: 'Thermal' }));
  return document.querySelector('textarea');
};

/** The card wraps the mode banner and the input, so its text is what is read. */
const cardText = () => document.querySelector('.card').textContent;

/**
 * The trace box, addressed as the textarea.
 *
 * The DSC panel also carries a text input for the sample name, so a bare
 * getByRole('textbox') now matches two elements. Naming the textarea keeps
 * these assertions about the trace rather than about whichever text field
 * happens to come first in the DOM.
 */
const traceBox = () => document.querySelector('textarea');

describe('thermal mode clarity', () => {
  test('the active mode is stated in words, not just a highlighted tab', () => {
    openThermal();
    // Names the active analysis...
    expect(cardText()).toMatch(/Active: TGA/i);
    // ...and says what the second column is read as, which is the part that
    // was ambiguous: the same two numbers mean different things in TGA/DSC.
    expect(cardText()).toMatch(/read as mass remaining/i);
  });

  test('switching to DSC changes what the panel says it will do', () => {
    openThermal();
    fireEvent.click(screen.getByRole('tab', { name: /DSC/i }));

    expect(cardText()).toMatch(/Active: DSC/i);
    // The TGA interpretation must be gone, not merely supplemented, or a user
    // could still read the wrong one.
    expect(cardText()).not.toMatch(/read as mass remaining/i);
    expect(cardText()).toMatch(/read as heat flow/i);
  });

  test('each mode states what it returns, so the choice is informed', () => {
    openThermal();
    // The summary on the tabs carries the outputs of each, not just a label.
    expect(document.body.textContent).toMatch(/residue/i);
    expect(document.body.textContent).toMatch(/crystallinity/i);
  });
});

describe('thermal clear button', () => {
  const clearBtn = () => screen.getByRole('button', { name: /^clear$/i });

  test('is disabled until there is something to clear', () => {
    openThermal();
    expect(clearBtn()).toBeDisabled();
  });

  test('empties the trace it was given', () => {
    const box = openThermal();
    fireEvent.change(box, { target: { value: TGA_ROWS } });
    expect(box).toHaveValue(TGA_ROWS);

    fireEvent.click(clearBtn());
    expect(traceBox()).toHaveValue('');
  });

  test('removes the result on screen, not only the input', async () => {
    const box = openThermal();
    fireEvent.change(box, { target: { value: TGA_ROWS } });
    fireEvent.click(screen.getByRole('button', { name: /Calculate/i }));

    await waitFor(() => expect(thermalApi.tga).toHaveBeenCalledTimes(1));
    // A plot proves a result actually rendered.
    await waitFor(() => expect(screen.getByTestId('plot')).toBeInTheDocument());

    fireEvent.click(clearBtn());
    // Both the plot and the textarea must be gone, or the panel is not clear.
    expect(screen.queryByTestId('plot')).not.toBeInTheDocument();
    expect(traceBox()).toHaveValue('');
  });

  test("clearing one mode does not touch the other mode's data", () => {
    const tgaBox = openThermal();
    fireEvent.change(tgaBox, { target: { value: TGA_ROWS } });

    fireEvent.click(screen.getByRole('tab', { name: /DSC/i }));
    const dscBox = traceBox();
    fireEvent.change(dscBox, { target: { value: '30\t-0.13\n180\t-0.2' } });
    fireEvent.click(clearBtn());
    expect(dscBox).toHaveValue('');

    fireEvent.click(screen.getByRole('tab', { name: /TGA/i }));
    // The TGA trace was never cleared, so it must still be there.
    expect(traceBox()).toHaveValue(TGA_ROWS);
  });
});
