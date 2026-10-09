/**
 * API client for the Polymer Analysis Toolkit.
 *
 * The base URL must be configured through REACT_APP_API_URL at build time.
 * Release 0.1.0 shipped without that variable set anywhere, so the deployed
 * bundle fell back to http://localhost:8000 - the visitor's own machine - and
 * every request failed. The fallback is kept for local development only, and
 * a warning is emitted in production when it is used, so the failure is
 * visible in the console instead of looking like a network outage.
 */

import axios from 'axios';

const PRODUCTION_FALLBACK = 'http://localhost:8000';

export const API_BASE_URL = process.env.REACT_APP_API_URL || PRODUCTION_FALLBACK;

if (process.env.NODE_ENV === 'production' && !process.env.REACT_APP_API_URL) {
  // eslint-disable-next-line no-console
  console.warn(
    '[PAT] REACT_APP_API_URL is not set. The app is falling back to ' +
      `${PRODUCTION_FALLBACK}, which points at the visitor's own machine and ` +
      'will fail. Set REACT_APP_API_URL in the hosting environment.',
  );
}

const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // large traces (thousands of points) are slow to analyse
});

/** Turn any axios failure into a message worth showing a user. */
export function describeError(error) {
  if (error?.response?.data?.detail) {
    const detail = error.response.data.detail;
    if (typeof detail === 'string') return detail;
    // FastAPI validation errors arrive as an array of objects.
    if (Array.isArray(detail)) {
      return detail
        .map((d) => `${(d.loc || []).join('.')}: ${d.msg}`)
        .join('; ');
    }
    return JSON.stringify(detail);
  }
  if (error?.response?.status) {
    return `HTTP ${error.response.status} from ${API_BASE_URL}`;
  }
  if (error?.code === 'ECONNABORTED') {
    return 'The request timed out. Very large datasets can take a while; try a coarser export.';
  }
  return (
    `Could not reach the API at ${API_BASE_URL}. ` +
    'Check that the backend is running and that its CORS settings allow this origin.'
  );
}

const postJson = (path, payload) => http.post(path, payload);

export const molecularApi = {
  /** JSON body mode. */
  calculate: (payload) => postJson('/api/v1/molecular/calc', payload),

  /** File upload mode. */
  calculateFromFile: (file, { normalise = false, markHouwinkA = null } = {}) => {
    const form = new FormData();
    form.append('file', file);
    if (normalise) form.append('normalise', 'true');
    if (markHouwinkA) form.append('mark_houwink_a', String(markHouwinkA));
    // Do NOT set Content-Type manually: the browser must add the multipart
    // boundary. Setting it was part of why 0.1.0 only worked by accident.
    return http.post('/api/v1/molecular/calc', form);
  },

  /** Inspect how a file will be parsed, without calculating. */
  previewImport: (file) => {
    const form = new FormData();
    form.append('file', file);
    return http.post('/api/v1/molecular/import', form);
  },

  /** Reference log-normal distribution. */
  logNormal: (Mn, dispersity, nPoints = 2000) => {
    const form = new FormData();
    form.append('Mn', String(Mn));
    form.append('dispersity', String(dispersity));
    form.append('n_points', String(nPoints));
    return http.post('/api/v1/molecular/log-normal', form);
  },
};

export const thermalApi = {
  tga: (temperature, massPct, smoothWindow = 11) =>
    postJson('/api/v1/thermal/tga', {
      temperature,
      mass_pct: massPct,
      smooth_window: smoothWindow,
    }),

  dsc: (
    temperature,
    heatFlow,
    { heatingRate = null, refEnthalpy = null, smoothWindow = 11, sampleName = null } = {},
  ) =>
    postJson('/api/v1/thermal/dsc', {
      temperature,
      heat_flow: heatFlow,
      heating_rate: heatingRate,
      ref_enthalpy_J_g: refEnthalpy,
      smooth_window: smoothWindow,
      sample_name: sampleName,
    }),

  /**
   * Upload an instrument file and let the server say what it found.
   *
   * The panel used to parse the file in the browser and post the two numbers
   * it had picked by position. On a NETZSCH export the second column is
   * *time*, so the trace analysed was temperature against time, in the wrong
   * unit, with nothing reporting it. The server reader resolves each column's
   * role from its label and unit; this is the only way to reach it.
   */
  importFile: (file, target) => {
    const form = new FormData();
    form.append('file', file);
    form.append('target', target);
    return http.post('/api/v1/thermal/import', form);
  },

  /**
   * Upload an instrument file and analyse it in one step.
   *
   * The heating rate is not sent: the server reads it from the instrument
   * header, which is the only place it is authoritative. Offering it as a
   * form field here would invite a second, silently differing value.
   */
  analyseFile: (file, target, { refEnthalpy = null } = {}) => {
    const form = new FormData();
    form.append('file', file);
    form.append('target', target);
    if (refEnthalpy !== null) form.append('ref_enthalpy_J_g', String(refEnthalpy));
    return http.post('/api/v1/thermal/analyse', form);
  },
};

export const mechanicalApi = {
  tensile: (strainPct, stressMPa, modulusWindow = null) =>
    postJson('/api/v1/mechanical/tensile', {
      strain_pct: strainPct,
      stress_MPa: stressMPa,
      modulus_window: modulusWindow,
    }),
};

export const rheologyApi = {
  sweep: (omega, gPrime, gDoublePrime, gelTolerance = 0.15) =>
    postJson('/api/v1/rheology/sweep', {
      omega,
      G_prime: gPrime,
      G_double_prime: gDoublePrime,
      gel_tolerance: gelTolerance,
    }),
};

export const structureApi = {
  xrd: (twoTheta, intensity, opts = {}) =>
    postJson('/api/v1/structure/xrd', {
      two_theta: twoTheta,
      intensity,
      wavelength_angstrom: opts.wavelengthAngstrom ?? 1.5406,
      K: opts.K ?? 0.9,
      instrumental_fwhm_deg: opts.instrumentalFwhmDeg ?? 0.0,
      prominence_frac: opts.prominenceFrac ?? 0.05,
    }),

  ftir: (wavenumber, absorbance, opts = {}) =>
    postJson('/api/v1/structure/ftir', {
      wavenumber,
      absorbance,
      prominence_frac: opts.prominenceFrac ?? 0.08,
      tolerance_cm1: opts.toleranceCm1 ?? 0.0,
    }),
};

export const healthApi = {
  check: () => http.get('/health'),
};

export default http;
