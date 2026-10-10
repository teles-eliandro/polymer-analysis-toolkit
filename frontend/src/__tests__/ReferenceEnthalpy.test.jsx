/**
 * The reference-enthalpy field, filled from the internal database.
 *
 * Crystallinity by DSC is Xc = dHm / dHf100, and dHf100 is never measured --
 * it comes from the literature and is specific to the polymer (293 J/g for PE
 * against 93 J/g for PLA). A free numeric field hides that: any number is
 * accepted, nothing says where it came from, and a wrong choice produces a
 * crystallinity that looks like a result.
 *
 * What is asserted here is what the user sees: the database can be chosen
 * from, choosing it fills the number *and* shows the citation, and typing a
 * value by hand stops the panel from claiming the citation still applies.
 *
 * Follows the mock pattern in ThermalModeAndClear.test.jsx: the api module is
 * replaced wholesale and the implementations are re-armed in beforeEach,
 * because CRA's jest config resets them between tests.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';

jest.mock('react-plotly.js', () => ({
  __esModule: true,
  default: () => <div data-testid="plot" />,
}));

const REFERENCES = [
  {
    key: 'PE',
    label: 'Polietileno (PE, HDPE/LDPE)',
    names: ['pe', 'hdpe', 'ldpe'],
    value_J_g: 293.0,
    crystal_form: 'ortorrômbica',
    source: "B. Wunderlich, F. M. Cormier, 'Heat of fusion of polyethylene'",
    confidence: 'verified',
    copolymer: false,
    note: null,
    alternatives: [
      { value_J_g: 290.0, source: 'Polymer Handbook, 4th ed.', crystal_form: null },
    ],
  },
  {
    key: 'PLA',
    label: 'Ácido poliláctico (PLA / PLLA)',
    names: ['pla'],
    value_J_g: 93.0,
    crystal_form: 'α (hélice 10/3)',
    source: 'E. W. Fischer et al., Kolloid-Z. Z. Polym. 251 (1973) 980-990',
    confidence: 'verified',
    copolymer: false,
    note: null,
    alternatives: [],
  },
  {
    key: 'PS',
    label: 'Poliestireno atático (PS, GPPS/HIPS)',
    names: ['ps'],
    value_J_g: null,
    crystal_form: null,
    source: null,
    confidence: null,
    copolymer: false,
    note: 'O poliestireno atático é amorfo: não cristaliza.',
    alternatives: [],
  },
];

jest.mock('../services/api', () => ({
  API_BASE_URL: 'http://test.local',
  describeError: (e) => `error: ${e}`,
  healthApi: { check: jest.fn() },
  thermalApi: {
    tga: jest.fn(),
    dsc: jest.fn(),
    crystallinityReferences: jest.fn(),
  },
}));

const { thermalApi, healthApi } = jest.requireMock('../services/api');

beforeEach(() => {
  healthApi.check.mockImplementation(() => Promise.resolve({ data: { status: 'ok' } }));
  thermalApi.tga.mockImplementation(() =>
    Promise.resolve({ data: { temperature: [30, 400], mass_pct: [100, 10] } })
  );
  thermalApi.dsc.mockImplementation(() =>
    Promise.resolve({
      data: { Tg: 100, Tm: null, temperature: [30, 180], heat_flow: [-0.13, -0.2] },
    })
  );
  thermalApi.crystallinityReferences.mockImplementation(() =>
    Promise.resolve({ data: { note: 'Xc', references: REFERENCES } })
  );
});

/**
 * Switch the panel to DSC and return the field that holds the reference
 * enthalpy, so a test can reach the dropdown and the number inside it.
 *
 * The field is found by its *label text*. The earlier version selected
 * `input[type="number"][min="0.1"]` on the assumption that only the enthalpy
 * input carries that attribute — but the heating-rate input carries it too,
 * so the selector returned the wrong input and `closest('label')` handed back
 * a label that never contains a dropdown.
 *
 * `expectDropDown` is false for the one case where the database is meant to be
 * unreachable: there the absence of the picker is the assertion, so waiting
 * for it would be waiting for the failure.
 */
const openDscForm = async ({ expectDropDown = true } = {}) => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: 'Thermal' }));
  fireEvent.click(screen.getByRole('tab', { name: /DSC/i }));

  const findField = () =>
    [...document.querySelectorAll('label.field')].find((l) =>
      /reference.*enthalpy/i.test(l.textContent)
    );

  await waitFor(() => expect(findField()).toBeDefined());
  const field = findField();
  if (expectDropDown) {
    // The database arrives asynchronously and the picker is rendered only
    // once it does, so the number input can exist before the dropdown does.
    await waitFor(() => expect(field.querySelector('select')).not.toBeNull());
  }
  return field;
};

describe('reference enthalpy from the internal database', () => {
  test('offers the polymers with their values', async () => {
    const field = await openDscForm();
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Polietileno.*293/ })).toBeInTheDocument();
    });
    expect(screen.getByRole('option', { name: /láctico.*93/ })).toBeInTheDocument();
  });

  test('choosing an entry fills the number and shows the citation', async () => {
    const field = await openDscForm();
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Polietileno/ })).toBeInTheDocument();
    });
    const select = field.querySelector('select');

    fireEvent.change(select, { target: { value: 'PE' } });

    const input = field.querySelector('input[type="number"]');
    await waitFor(() => {
      expect(input.value).toBe('293');
    });
    // A citação precisa aparecer: um valor sem fonte não é verificável.
    expect(screen.getByText(/Wunderlich/)).toBeInTheDocument();
    // E a forma cristalina, que distingue polimorfos.
    expect(screen.getByText(/ortorrômbica/)).toBeInTheDocument();
  });

  test('shows the alternative value rather than hiding the disagreement', async () => {
    const field = await openDscForm();
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Polietileno/ })).toBeInTheDocument();
    });
    fireEvent.change(field.querySelector('select'), { target: { value: 'PE' } });
    await waitFor(() => {
      expect(screen.getByText(/Polymer Handbook/)).toBeInTheDocument();
    });
  });

  test('an amorphous polymer is offered as not applicable, with no number', async () => {
    const field = await openDscForm();
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Poliestireno/ })).toBeInTheDocument();
    });

    fireEvent.change(field.querySelector('select'), { target: { value: 'PS' } });

    const input = field.querySelector('input[type="number"]');
    await waitFor(() => {
      // Sem número: o PS atático não cristaliza.
      expect(input.value).toBe('');
    });
    // Mas o motivo aparece, em vez de um campo vazio sem explicação.
    expect(screen.getByText(/amorfo/i)).toBeInTheDocument();
  });

  test('typing a value stops the panel claiming the citation applies', async () => {
    const field = await openDscForm();
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Polietileno/ })).toBeInTheDocument();
    });
    fireEvent.change(field.querySelector('select'), { target: { value: 'PE' } });
    await waitFor(() => {
      expect(screen.getByText(/Wunderlich/)).toBeInTheDocument();
    });

    const input = field.querySelector('input[type="number"]');
    fireEvent.change(input, { target: { value: '150' } });

    await waitFor(() => {
      // 150 não é o valor do PE: manter a citação ao lado diria que é.
      expect(screen.queryByText(/Wunderlich/)).not.toBeInTheDocument();
    });
    expect(input.value).toBe('150');
  });

  test('a database that cannot be reached leaves the field usable', async () => {
    // O banco é conveniência; se cair, o campo numérico continua funcionando.
    thermalApi.crystallinityReferences.mockImplementationOnce(() =>
      Promise.reject(new Error('offline'))
    );
    const field = await openDscForm({ expectDropDown: false });
    // Sem lista: nenhum dropdown, mas o input continua lá e aceita um valor.
    expect(field.querySelector('select')).toBeNull();
    const input = field.querySelector('input[type="number"]');
    expect(input).not.toBeNull();
    fireEvent.change(input, { target: { value: '290' } });
    expect(input.value).toBe('290');
  });
});
