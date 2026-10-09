/**
 * Minimal i18n for the toolkit.
 *
 * Deliberately not i18next: the app has one page per module and a fixed
 * vocabulary, so a hand-rolled lookup keeps the bundle small and makes every
 * string greppable. Scientific terms that have one accepted form in the
 * literature (Mn, Mw, dispersity, Scherrer, Mark-Houwink) are NOT translated -
 * translating them would make the output harder to compare with a paper, not
 * easier.
 *
 * Adding a language: add one entry to MESSAGES with the same keys. A missing
 * key falls back to English and logs a warning in development, so a partial
 * translation degrades rather than crashing.
 */

import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

export const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'pt', label: 'Português' },
  { code: 'es', label: 'Español' },
];

const MESSAGES = {
  en: {
    'mech.f.fit.E': 'Tensile modulus, the slope of the fitted line, in MPa.',
    'mech.f.fit.eps': 'Strain of point i within the fitted window.',
    'mech.f.fit.sig': 'Stress of point i within the fitted window, in MPa.',
    'mech.f.toughness.U': 'Energy at break per unit volume, the area under the curve, in MJ/m3.',
    'mech.f.toughness.sig': 'Engineering stress, in MPa.',
    'mech.f.toughness.eps': 'Engineering strain, dimensionless.',
    'mol.f.pdi.D': 'Dispersity, Mw divided by Mn. 1.0 means every chain is the same length.',
    'mol.f.pdi.Mw': 'Mass-average molar mass.',
    'mol.f.pdi.Mn': 'Number-average molar mass.',
    'mol.f.mz.Ni': 'Number of chains of molar mass Mi.',
    'mol.f.mz.Mi': 'Molar mass of the i-th species.',
    'mol.f.gpc.M': 'Molar mass read from the calibration curve at the given elution volume.',
    'mol.f.log.w': 'Weight fraction in the slice of the distribution centred on M.',
    'mol.f.log.sigma': 'Width of the log-normal distribution in ln M.',
    'mol.f.log.mu': 'Mean of ln M for the distribution.',
    'rheo.f.tan.Gpp': 'Loss modulus, the viscous (energy-dissipating) response.',
    'rheo.f.tan.Gp': 'Storage modulus, the elastic (energy-storing) response.',
    'rheo.f.gel.Gp': 'Storage modulus at the gel point.',
    'rheo.f.gel.Gpp': 'Loss modulus at the gel point.',
    'rheo.f.cross.Gp': 'Storage modulus, in Pa.',
    'rheo.f.cross.Gpp': 'Loss modulus, in Pa.',
    "rheo.f.cross.tan": "Loss tangent, G'' / G'. Equals 1 exactly at the cross-over.",
    'structure.f.fwhm.beta': 'Full width at half maximum of the reflection, in radians.',
    'structure.f.fwhm.tt': 'Diffraction angle, twice the Bragg angle, in degrees.',
    'structure.f.xc.A': 'Area of the crystalline reflections above the amorphous background.',
    'structure.f.xc.At': 'Total area of the pattern over the same angular range.',
    'thermal.f.res.mf': 'Mass at the end of the run, as a percentage of the starting mass.',
    'thermal.f.uniform.dtg': 'Rate of mass loss, in percent per degree Celsius.',

    'app.title': 'Polymer Analysis Toolkit',
    'app.subtitle': 'Open characterisation tools for polymer scientists',
    'app.tagline':
      'Every result states its method, its units and its assumptions. Nothing here is a black box.',
    'app.footer.developed': 'Developed by',
    'app.footer.repo': 'Source code',
    'app.footer.docs': 'API documentation',

    'nav.molecular': 'Molar mass',
    'nav.thermal': 'Thermal',
    'nav.mechanical': 'Mechanical',
    'nav.rheology': 'Rheology',
    'nav.structure': 'Structure',

    'common.calculate': 'Calculate',
    'common.calculating': 'Calculating…',
    'common.reset': 'Clear',
    'common.loading': 'Loading…',
    'common.results': 'Results',
    'common.error': 'Error',
    'common.optional': 'optional',
    'common.required': 'required',
    'common.upload': 'Upload a file',
    'common.chooseFile': 'Choose file',
    'common.downloadPng': 'Download graph (PNG)',
    'common.downloadPngFailed': 'The graph could not be rendered as an image.',
    'common.downloadBundle': 'Download results + graph (.zip)',
    'common.downloadBundleFailed': 'The download could not be prepared.',
    'common.noFile': 'No file selected',
    'common.exportJson': 'Export JSON',
    'common.importDecisions': 'How the file was read',
    'common.showDetails': 'Show details',
    'common.hideDetails': 'Hide details',
    'common.formulasAndModels': 'Formulas, models and references',
    'common.slices': 'slices',
    'common.apiUrl': 'API',
    'common.apiUnreachable': 'API unreachable',
    'common.apiOk': 'API online',
    'common.language': 'Language',

    'molecular.title': 'Molar mass distribution',
    'molecular.intro':
      'Calculate the molar-mass averages from a distribution, either by uploading an instrument export or by entering the values directly.',
    'molecular.uploadLabel': 'Instrument export (CSV or delimited text)',
    'molecular.uploadHint':
      'Any of these are accepted: mass/fraction in g/mol, percentages, raw detector intensity, a logM axis, comma or semicolon delimiters, decimal comma, header in English or Portuguese.',
    'molecular.preview': 'Inspect file',
    'molecular.previewHint':
      'Shows how the importer interpreted the file before anything is calculated.',
    'molecular.normalise': 'Normalise the fractions by their sum',
    'molecular.normaliseHint':
      'Use when the values are percentages or raw intensities rather than fractions that sum to one.',
    'molecular.markHouwink': 'Mark-Houwink exponent a',
    'molecular.markHouwinkHint':
      'Optional. Supplying a value also computes Mv, the viscosity-average molar mass. The exponent is specific to the polymer, solvent and temperature, and must come from a handbook or paper.',
    'molecular.manualEntry': 'Enter the distribution directly',
    'molecular.masses': 'Molar masses (g/mol)',
    'molecular.fractions': 'Weight fractions',
    'molecular.pairHint': 'One value per line, in matching order.',
    'molecular.Mn': 'Number average',
    'molecular.Mw': 'Weight average',
    'molecular.Mz': 'Z average',
    'molecular.Mz1': 'Z+1 average',
    'molecular.Mv': 'Viscosity average',
    'molecular.dispersity': 'Dispersity (Đ)',
    'molecular.dispersityNote':
      'Đ = Mw/Mn. Near 1.0 for a controlled polymerisation, above 1.5 for uncontrolled radical polymerisation.',
    'molecular.MnNote': 'Weighted by the number of chains.',
    'molecular.MwNote': 'Weighted by mass. The value a light-scattering measurement gives.',
    'molecular.MzNote': 'Sensitive to the high-mass tail.',
    'molecular.Mz1Note': 'Very sensitive to the high-mass tail.',
    'molecular.distribution': 'Weight distribution',
    'molecular.crossCheck': 'Cross-check against the file',
    'molecular.crossCheckNote':
      'The instrument reported its own averages. A large difference means the file was misread.',
    'molecular.fileMn': 'Mn in file',
    'molecular.fileMw': 'Mw in file',
    'molecular.calcMn': 'Mn calculated',
    'molecular.calcMw': 'Mw calculated',
    'molecular.reference': 'Reference case',
    'molecular.referenceNote':
      'A log-normal distribution is the shape a well-controlled radical polymerisation approaches. Its properties are known analytically, so it is a useful sanity check.',
    'molecular.referenceDispersity': 'Target dispersity',
    'molecular.generate': 'Generate',

    'thermal.title': 'Thermal analysis',
    'thermal.intro':
      'TGA gives degradation temperatures and residue; DSC gives the glass transition, melting and crystallinity.',
    'thermal.tga': 'TGA',
    'thermal.dsc': 'DSC',
    'thermal.f.dtg.name': 'DTG (derivative thermogravimetry)',
    'thermal.f.dtg.m': 'sample mass, as a percentage of the initial mass',
    'thermal.f.dtg.T': 'furnace temperature (°C)',
    'thermal.f.dtg.note': "The sign is chosen so a mass loss is positive. Only the temperature of the maximum is reported, not its height, because the height scales with the heating rate and cannot be compared between runs at different rates.",
    'thermal.f.td.name': 'Decomposition temperature Td',
    'thermal.f.td.x': 'the mass loss defining the onset, 5 % and 10 % here',
    'thermal.f.td.m': 'smoothed mass percent remaining',
    'thermal.f.td.note': "Td(5 %) is the conventional onset. Values below about 150 °C are usually residual water or solvent, not chain scission, so a Td(5 %) near 100 °C does not mean the polymer is unstable.",
    'thermal.f.res.name': 'Residue',
    'thermal.f.res.note': 'Read at the last temperature of the run, so it is instrument-range dependent. A run that ends at 600 °C and one that ends at 800 °C can report different residues for the same material.',
    'thermal.f.smooth.name': 'Smoothing',
    'thermal.f.smooth.w':
      'window length in points; a larger w means more smoothing, and an even value is reduced by one so the window stays centred',
    'thermal.f.smooth.note': 'Differentiation amplifies noise, so the mass curve is smoothed first. The default window of 11 points is a compromise: wider is steadier but merges closely spaced steps.',
    'thermal.f.uniform.name': 'Uneven temperature axis',
    'thermal.f.uniform.note': "Instrument exports are neither sorted nor evenly spaced: the same set-point is logged many times and the spacing varies within a run. Taking the derivative on that axis makes np.gradient divide by a zero-width interval and return NaN, and the peak search then reports the end of the scan. The trace is therefore sorted, samples sharing a temperature are averaged, and the derivative is taken on a uniform grid.",
    'thermal.f.dscpeak.name': 'Heat of fusion',
    'thermal.f.dscpeak.Hm': 'specific enthalpy of the melting transition (J/g)',
    'thermal.f.dscpeak.q': 'heat flow per unit mass (W/g), endothermic up',
    'thermal.f.dscpeak.beta': 'heating rate (K/s); dividing by it converts the integral over time into an enthalpy',
    'thermal.f.dscpeak.note': 'The result depends strongly on the baseline. This tool fits the baseline on the flanks outside the peak, because a straight line joining the two ends of the scan follows the change in heat capacity and inflates the enthalpy.',
    'thermal.f.xc.name': 'Degree of crystallinity',
    'thermal.f.xc.Hm': 'measured enthalpy of fusion (J/g)',
    'thermal.f.xc.Hm0': 'enthalpy of fusion of the fully crystalline polymer, supplied by you (e.g. 139.5 J/g for PCL, 93 J/g for PLLA)',
    'thermal.f.xc.note': 'Xc is only meaningful if ΔHm° matches your polymer and your crystal form. It is a mass fraction, ignores rigid amorphous material, and cannot exceed 100 %: a value above it means the baseline is wrong, not that the sample is exceptional.',
    'thermal.shortTraceWarning':
      'A short trace gives an unreliable DTG; export the full run if you can.',
    'thermal.temperature': 'Temperature (°C)',
    'thermal.massPct': 'Mass remaining (%)',
    'thermal.heatFlow': 'Heat flow (W/g)',
    'thermal.heatingRate': 'Heating rate (K/min)',
    'thermal.heatingRateHint':
      'Required for enthalpies: the signal is integrated over temperature, so the scan rate is needed to get J/g.',
    'thermal.refEnthalpy': 'Reference melting enthalpy (J/g)',
    'thermal.refEnthalpyHint':
      'The melting enthalpy of the same polymer in a fully crystalline state. Required for a crystallinity value, and it must be the right polymorph.',
    'thermal.Td5': 'Td at 5 % loss',
    'thermal.Td10': 'Td at 10 % loss',
    'thermal.TmaxRate': 'Peak decomposition rate',
    'thermal.TmaxRateNote':
      'The step that loses mass fastest. With several steps this is not necessarily the first one.',
    'thermal.residue': 'Residue',
    'thermal.steps': 'Decomposition steps',
    'thermal.Tg': 'Glass transition',
    'confidence.read': 'read',
    'confidence.read.hint':
      'A property of the input file, or a deterministic transform of it. Nothing here is an inference.',
    'confidence.formula': 'formula',
    'confidence.formula.hint':
      'A published formula applied to a declared input. Cite the formula and its bounds and you reproduce the number.',
    'confidence.suggested': 'suggested',
    'confidence.suggested.hint':
      'An inference from the shape of the trace. It can be wrong: on real instrument data the transition identification is not reliable enough to call a measurement.',
    'confidence.why': 'Why this value?',
    'thermal.reliable': 'stable on resampling',
    'thermal.notReliable': 'UNSTABLE - do not quote without repeats',
    'thermal.TgNote':
      'ASTM D3418 midpoint. A single heating scan carries the sample history; a heat-cool-heat cycle read on the second heating is more reliable.',
    'thermal.Tm': 'Melting point',
    'thermal.deltaHm': 'Melting enthalpy',
    'thermal.deltaCp': 'Heat capacity step',
    'thermal.crystallinity': 'Crystallinity',
    'thermal.crystallinityNote':
      'Uses the reference enthalpy supplied above. A value above 100 % means the reference does not match the sample.',
    'thermal.trace': 'Trace',
    'thermal.dtg': 'Derivative',
    'thermal.modeQuestion': 'Which analysis will run?',
    'thermal.modeTgaWhat': 'Mass loss vs temperature. Gives Td, the DTG peak and residue.',
    'thermal.modeDscWhat':
      'Heat flow vs temperature. Gives Tg, Tm, melting enthalpy and crystallinity.',
    'thermal.activeMode': 'Active: {mode}',
    'thermal.runsAs': 'Your data will be analysed as a {mode} trace.',
    'thermal.runsAsTga':
      'Your data will be analysed as a TGA trace: the second column is read as mass remaining (%).',
    'thermal.runsAsDsc':
      'Your data will be analysed as a DSC trace: the second column is read as heat flow (W/g).',
    'thermal.switchWarn':
      'You have data loaded for {from}. Switching to {to} will not analyse it.',
    'thermal.clear': 'Clear',
    'thermal.clearHint': 'Empties the current trace and any result.',
    'thermal.cleared': 'Cleared.',

    'mechanical.title': 'Tensile properties',
    'mechanical.intro':
      'Standard descriptors from an engineering stress-strain curve, per ISO 527-1.',
    'mechanical.strain': 'Strain (%)',
    'mechanical.stress': 'Stress (MPa)',
    'mechanical.modulus': "Young's modulus",
    'mechanical.modulusNote':
      'Slope of the initial linear region. The strain window used is reported so the value can be checked.',
    'mechanical.window': 'Strain window used',
    'mechanical.stressMax': 'Tensile strength',
    'mechanical.strainMax': 'Strain at maximum',
    'mechanical.stressBreak': 'Stress at break',
    'mechanical.strainBreak': 'Strain at break',
    'mechanical.stressYield': 'Yield stress',
    'mechanical.strainYield': 'Yield strain',
    'mechanical.toughness': 'Toughness',
    'mechanical.toughnessNote': 'Area under the curve. The least precise number here.',
    'mechanical.yielded': 'Shows a yield point',
    'mechanical.brittle': 'Breaks at maximum stress',
    'mechanical.curve': 'Stress-strain curve',

    'rheology.title': 'Oscillatory shear',
    'rheology.intro': 'Descriptors of a small-amplitude frequency sweep.',
    'rheology.omega': 'Angular frequency (rad/s)',
    'rheology.gPrime': "Storage modulus G' (Pa)",
    'rheology.gDoublePrime': "Loss modulus G'' (Pa)",
    'rheology.crossover': 'Crossover',
    'rheology.crossoverNote': "Frequency where G' = G''. Its inverse is the terminal relaxation time.",
    'rheology.plateau': 'Plateau modulus',
    'rheology.plateauNote':
      'Estimated from the minimum of tan(δ). Slightly biased low, because the full relaxation spectrum is not measured.',
    'rheology.relaxation': 'Relaxation time',
    'rheology.slopes': 'Terminal slopes',
    'rheology.slopesNote':
      "For a narrow-distribution linear melt the theory gives 2 for G' and 1 for G''. Values much lower mean the sweep did not reach the terminal regime, so the plateau modulus and zero-shear viscosity are not meaningful.",
    'rheology.zeroShear': 'Zero-shear viscosity',
    'rheology.gel': 'Gel point (Winter-Chambon)',
    'rheology.gelYes': 'tan(δ) is frequency independent — consistent with a critical gel',
    'rheology.gelNo': 'tan(δ) varies with frequency — no gel point in this window',
    'rheology.solidLike': "G' exceeds G'' at the lowest frequency",
    'rheology.liquidLike': "G'' exceeds G' at the lowest frequency",
    'rheology.masterCurve': "G' and G'' vs frequency",

    'structure.title': 'Structure',
    'structure.intro':
      'X-ray diffraction for crystallinity and crystallite size; infrared for functional groups.',
    'structure.xrd': 'XRD',
    'structure.ftir': 'FTIR',
    'structure.twoTheta': '2θ (degrees)',
    'structure.intensity': 'Intensity',
    'structure.wavelength': 'Wavelength (Å)',
    'structure.instrumentFwhm': 'Instrumental broadening (FWHM, °)',
    'structure.instrumentFwhmHint':
      'Measure it on a standard such as LaB6 or silicon. Leaving it at zero makes every crystallite size an underestimate.',
    'structure.peaks': 'Peaks',
    'structure.peak': '2θ',
    'structure.dSpacing': 'd (Å)',
    'structure.size': 'Size (nm)',
    'structure.fwhm': 'FWHM (°)',
    'structure.crystallinity': 'Crystallinity index',
    'structure.crystallinityNote':
      'NOT the absolute degree of crystallinity. Comparable only between samples measured with the same range, baseline and slits.',
    'structure.wavenumber': 'Wavenumber (cm⁻¹)',
    'structure.absorbance': 'Absorbance',
    'structure.bands': 'Detected bands',
    'structure.band': 'Band',
    'structure.assignments': 'Candidate assignments',
    'structure.pattern': 'Pattern',
    'structure.spectrum': 'Spectrum',
    'structure.kFactor': 'Scherrer constant K',
    'structure.kFactorHint':
      'Shape factor in the Scherrer equation, typically 0.9 for spherical crystallites. Change it only if you know the crystallite habit.',
    'structure.tolerance': 'Match tolerance (cm⁻¹)',
    'structure.toleranceHint':
      'How far a detected band may sit from a reference value and still be reported as a candidate. Zero means exact position only.',
    'structure.ftirWarning':
      'This is a functional-group lookup, not an identification. Many polymers share the same groups, and additives and moisture contribute their own bands. Confirm against a reference spectrum measured on the same instrument.',

    'structure.f.bragg.name': 'Bragg condition (d-spacing)',
    'structure.f.bragg.d': 'interplanar spacing (Å)',
    'structure.f.bragg.lambda': 'X-ray wavelength, Cu Kα = 1.5406 Å unless you set otherwise',
    'structure.f.bragg.theta': 'half the scattering angle',
    'structure.f.bragg.note': "The wavelength is taken from what you enter, not guessed. A pattern collected with synchrotron or Mo radiation will give d-spacings wrong by the ratio of the wavelengths if the default is left in place.",
    'structure.f.scherrer.name': 'Scherrer equation (crystallite size)',
    'structure.f.scherrer.D': 'apparent crystallite size, normal to the reflecting plane (nm)',
    'structure.f.scherrer.K': 'shape factor, 0.9 for near-spherical crystallites',
    'structure.f.scherrer.lambda': 'X-ray wavelength (Å)',
    'structure.f.scherrer.beta': 'FWHM of the reflection, in radians, corrected for instrumental broadening',
    'structure.f.scherrer.theta': 'Bragg angle',
    'structure.f.scherrer.note': "D is a volume-weighted mean size along one direction, not a particle size, and not a grain size. It is a lower bound: any strain or size distribution broadens the peak further and makes D smaller. Values below a few nanometres are not physical.",
    'structure.f.fwhm.name': 'Peak width',
    'structure.f.fwhm.note': 'Measured at half of the peak height above the local baseline. Peaks too close to a neighbour, or too weak to separate from noise, are reported as unmeasurable rather than given an invented width.',
    'structure.f.xc.name': 'Crystallinity index (XRD)',
    'structure.f.xc.note': 'The area above a straight chord between the pattern endpoints, over the total area. This is an index, not a mass fraction: it depends on the angular range, the slit widths and the baseline. It cannot be compared with a DSC crystallinity, and it is reported as unavailable when the chord does not cut the pattern at all, because then every point counts as crystalline.',
    'mech.f.young.name': "Young's modulus",
    'mech.f.young.E': 'tensile modulus (MPa)',
    'mech.f.young.sigma': 'engineering stress (MPa), force over the original cross-section',
    'mech.f.young.epsilon': 'engineering strain (%)',
    'mech.f.young.note': 'The modulus is only comparable between samples fitted over the same strain range. A modulus fitted over 0-5 % is systematically lower than one fitted over 0-0.5 %, because the curve bends as it yields. The range used is reported with the result.',
    'mech.f.fit.name': 'Linear fit',
    'mech.f.fit.note': 'Least squares over the strain window, either detected by the largest local slope or supplied by you. A window that starts after the toe region is corrected for must be chosen by eye; the automatic detection can land on the yield shoulder in a ductile sample.',
    'mech.f.sigma.name': 'Stress and strain',
    'mech.f.sigma.F': 'applied force (N)',
    'mech.f.sigma.A0': 'cross-sectional area before the test (mm2)',
    'mech.f.sigma.L0': 'gauge length before the test (mm)',
    'mech.f.sigma.note': 'These are engineering values throughout: the original area is used and never updated during the test. True stress is higher in a necking sample, so the tensile strength reported here is conservative.',
    'mech.f.toughness.name': 'Toughness',
    'mech.f.toughness.note': 'The trapezoidal area under the curve as supplied. If the test was stopped before break, the value is a lower bound and the tool reports it without knowing the difference.',
    'rheo.f.moduli.name': 'Storage and loss moduli',
    'rheo.f.moduli.Gp': 'storage modulus (Pa), the elastic response',
    'rheo.f.moduli.Gpp': 'loss modulus (Pa), the viscous response',
    'rheo.f.moduli.delta': 'phase lag between stress and strain (rad)',
    'rheo.f.moduli.note': 'Valid only inside the linear viscoelastic region, where the moduli do not depend on strain amplitude. A sweep run outside it reports a lower G-prime that looks like a material change and is not.',
    'rheo.f.tan.name': 'Loss tangent',
    'rheo.f.tan.note': 'Above 1 the sample dissipates more than it stores. In a melt this is normal; in a crosslinked network it indicates the test is above the gel point or that the network is not fully formed.',
    'rheo.f.gel.name': 'Gel point',
    'rheo.f.gel.note': 'Reported only when the two moduli stay within the tolerance of each other while G-prime exceeds G-double-prime. The tolerance matters: a fixed crossing test fires on noise in a noisy sweep, so the two moduli must agree over several consecutive points.',
    'rheo.f.cross.name': 'Cross-over frequency',
    'rheo.f.cross.note': 'The frequency where the melt stops behaving elastically. It shifts with temperature, so a cross-over quoted without its temperature is not reproducible.',
    'mol.f.mn.name': 'Number and weight averages',
    'mol.f.mn.Ni': 'number of chains of molar mass Mi',
    'mol.f.mn.Mi': 'molar mass of the i-th species (g/mol)',
    'mol.f.mn.note': 'Mn is the simple mean over chains, Mw weights each chain by its mass. Mw is always greater than or equal to Mn; if a result violates that, the data or the arithmetic is wrong, not the polymer.',
    'mol.f.pdi.name': 'Dispersity',
    'mol.f.pdi.note': 'A dispersity of 1.0 means every chain has the same length, which no real polymerisation achieves: the theoretical minimum for a living anionic polymerisation is about 1.02. Values near 2 indicate a step-growth or chain-transfer-dominated mechanism.',
    'mol.f.mz.name': 'z-average',
    'mol.f.mz.note': 'The z-average is used by light scattering and by viscometry, so comparing it with Mw from the same trace checks the shape of the distribution rather than just its position.',
    'mol.f.mh.name': 'Mark-Houwink-Sakurada',
    'mol.f.mh.Mv': 'viscosity-average molar mass (g/mol)',
    'mol.f.mh.K': 'polymer-, solvent- and temperature-specific constant',
    'mol.f.mh.a': 'exponent, 0.5 in a theta solvent and up to about 0.8 in a good solvent',
    'mol.f.mh.note': 'Mv sits between Mn and Mw and is closest to Mw when a is near 1. Using K and a from a different solvent or temperature gives a systematically wrong molar mass that looks perfectly reasonable.',
    'mol.f.gpc.name': 'SEC calibration',
    'mol.f.gpc.note': 'The calibration curve converts elution volume to molar mass using standards of a different polymer unless the standards match the sample. This is why a result from a conventional SEC is a relative molar mass, and why the calibration standard must be reported.',
    'mol.f.log.name': 'Log-normal distribution',
    'mol.f.log.note': 'A model, not a measurement. It is shown to compare the shape of a measured distribution against an idealised one, and it assumes the trace is free of column broadening, which broadens every real trace.',
    'error.needData': 'Provide a file or enter the values directly.',
    'error.needFile': 'Choose a file first.',

    'file.choose': 'Choose a data file',
    'file.chooseOrDrop': 'Choose a file or drop it here',
    'file.accepted': 'Accepted: {list}',
    'file.clear': 'Remove file',
    'file.unsupported':
      'The extension {ext} is not a text data format this tool can read. Export the trace as CSV or TXT.',
    'file.tooLarge':
      'The file is larger than {mb} MB and will not be parsed in the browser. Export a coarser trace.',
    'file.readFailed': 'The file {name} could not be read.',
    'file.loaded': 'Loaded {name}: {n} points.',
    'file.noPoints':
      'No numeric pair could be read from {name}. It may be a binary instrument format; export it as CSV or TXT.',
    'file.pickColumns':
      'The file has more than two columns. Pair {a} and {b} are used; change the columns below if that is wrong.',
    'file.columnA': 'X column',
    'file.columnB': 'Y column',
    'error.tooFewPoints': 'At least {n} points are needed.',
    'error.mismatched': 'The two columns must have the same number of values.',
    'error.badNumbers': 'Some values could not be read as numbers.',
  },

  pt: {
    'mech.f.fit.E': 'Modulo de elasticidade, a inclinacao da reta ajustada, em MPa.',
    'mech.f.fit.eps': 'Deformacao do ponto i dentro da janela ajustada.',
    'mech.f.fit.sig': 'Tensao do ponto i dentro da janela ajustada, em MPa.',
    'mech.f.toughness.U': 'Energia na ruptura por unidade de volume, a area sob a curva, em MJ/m3.',
    'mech.f.toughness.sig': 'Tensao de engenharia, em MPa.',
    'mech.f.toughness.eps': 'Deformacao de engenharia, adimensional.',
    'mol.f.pdi.D': 'Dispersidade, Mw dividido por Mn. 1,0 significa que todas as cadeias tem o mesmo tamanho.',
    'mol.f.pdi.Mw': 'Massa molar media em massa.',
    'mol.f.pdi.Mn': 'Massa molar media em numero.',
    'mol.f.mz.Ni': 'Numero de cadeias de massa molar Mi.',
    'mol.f.mz.Mi': 'Massa molar da especie i.',
    'mol.f.gpc.M': 'Massa molar lida na curva de calibracao no volume de eluicao dado.',
    'mol.f.log.w': 'Fracao em massa na fatia da distribuicao centrada em M.',
    'mol.f.log.sigma': 'Largura da distribuicao log-normal em ln M.',
    'mol.f.log.mu': 'Media de ln M da distribuicao.',
    'rheo.f.tan.Gpp': 'Modulo de perda, a resposta viscosa (dissipadora de energia).',
    'rheo.f.tan.Gp': 'Modulo de armazenamento, a resposta elastica (acumuladora de energia).',
    'rheo.f.gel.Gp': 'Modulo de armazenamento no ponto de gel.',
    'rheo.f.gel.Gpp': 'Modulo de perda no ponto de gel.',
    'rheo.f.cross.Gp': 'Modulo de armazenamento, em Pa.',
    'rheo.f.cross.Gpp': 'Modulo de perda, em Pa.',
    "rheo.f.cross.tan": "Tangente de perda, G'' / G'. Vale exatamente 1 no cruzamento.",
    'structure.f.fwhm.beta': 'Largura a meia altura da reflexao, em radianos.',
    'structure.f.fwhm.tt': 'Angulo de difracao, o dobro do angulo de Bragg, em graus.',
    'structure.f.xc.A': 'Area das reflexoes cristalinas acima do fundo amorfo.',
    'structure.f.xc.At': 'Area total do padrao na mesma faixa angular.',
    'thermal.f.res.mf': 'Massa no fim do ensaio, como porcentagem da massa inicial.',
    'thermal.f.uniform.dtg': 'Taxa de perda de massa, em porcento por grau Celsius.',

    'app.title': 'Polymer Analysis Toolkit',
    'app.subtitle': 'Ferramentas abertas de caracterização para cientistas de polímeros',
    'app.tagline':
      'Todo resultado informa o método, as unidades e as hipóteses. Nada aqui é caixa-preta.',
    'app.footer.developed': 'Desenvolvido por',
    'app.footer.repo': 'Código-fonte',
    'app.footer.docs': 'Documentação da API',

    'nav.molecular': 'Massa molar',
    'nav.thermal': 'Térmica',
    'nav.mechanical': 'Mecânica',
    'nav.rheology': 'Reologia',
    'nav.structure': 'Estrutura',

    'common.calculate': 'Calcular',
    'common.calculating': 'Calculando…',
    'common.reset': 'Limpar',
    'common.loading': 'Carregando…',
    'common.results': 'Resultados',
    'common.error': 'Erro',
    'common.optional': 'opcional',
    'common.required': 'obrigatório',
    'common.upload': 'Enviar arquivo',
    'common.chooseFile': 'Escolher arquivo',
    'common.downloadPng': 'Baixar gráfico (PNG)',
    'common.downloadPngFailed': 'Não foi possível gerar a imagem do gráfico.',
    'common.downloadBundle': 'Baixar resultados + gráfico (.zip)',
    'common.downloadBundleFailed': 'Não foi possível preparar o download.',
    'common.noFile': 'Nenhum arquivo selecionado',
    'common.exportJson': 'Exportar JSON',
    'common.importDecisions': 'Como o arquivo foi lido',
    'common.showDetails': 'Ver detalhes',
    'common.hideDetails': 'Ocultar detalhes',
    'common.formulasAndModels': 'Fórmulas, modelos e referências',
    'common.slices': 'fatias',
    'common.apiUrl': 'API',
    'common.apiUnreachable': 'API inacessível',
    'common.apiOk': 'API no ar',
    'common.language': 'Idioma',

    'molecular.title': 'Distribuição de massa molar',
    'molecular.intro':
      'Calcule as médias de massa molar a partir de uma distribuição, enviando a exportação do equipamento ou digitando os valores.',
    'molecular.uploadLabel': 'Exportação do equipamento (CSV ou texto delimitado)',
    'molecular.uploadHint':
      'São aceitos: massa/fração em g/mol, porcentagens, intensidade bruta do detector, eixo logM, separador por vírgula ou ponto e vírgula, vírgula decimal, cabeçalho em português ou inglês.',
    'molecular.preview': 'Inspecionar arquivo',
    'molecular.previewHint':
      'Mostra como o importador interpretou o arquivo antes de qualquer cálculo.',
    'molecular.normalise': 'Normalizar as frações pela soma',
    'molecular.normaliseHint':
      'Use quando os valores são porcentagens ou intensidades brutas, e não frações que somam um.',
    'molecular.markHouwink': 'Expoente de Mark-Houwink a',
    'molecular.markHouwinkHint':
      'Opcional. Informar um valor também calcula Mv, a massa molar média viscosimétrica. O expoente é específico do polímero, solvente e temperatura, e deve vir de um handbook ou artigo.',
    'molecular.manualEntry': 'Digitar a distribuição diretamente',
    'molecular.masses': 'Massas molares (g/mol)',
    'molecular.fractions': 'Frações em massa',
    'molecular.pairHint': 'Um valor por linha, na mesma ordem.',
    'molecular.Mn': 'Média numérica',
    'molecular.Mw': 'Média ponderal',
    'molecular.Mz': 'Média Z',
    'molecular.Mz1': 'Média Z+1',
    'molecular.Mv': 'Média viscosimétrica',
    'molecular.dispersity': 'Dispersividade (Đ)',
    'molecular.dispersityNote':
      'Đ = Mw/Mn. Próximo de 1,0 em polimerização controlada, acima de 1,5 em radicalar não controlada.',
    'molecular.MnNote': 'Ponderada pelo número de cadeias.',
    'molecular.MwNote': 'Ponderada pela massa. É o valor que o espalhamento de luz fornece.',
    'molecular.MzNote': 'Sensível à cauda de alta massa.',
    'molecular.Mz1Note': 'Muito sensível à cauda de alta massa.',
    'molecular.distribution': 'Distribuição em massa',
    'molecular.crossCheck': 'Conferência com o arquivo',
    'molecular.crossCheckNote':
      'O equipamento informou as próprias médias. Diferença grande significa que o arquivo foi mal lido.',
    'molecular.fileMn': 'Mn no arquivo',
    'molecular.fileMw': 'Mw no arquivo',
    'molecular.calcMn': 'Mn calculado',
    'molecular.calcMw': 'Mw calculado',
    'molecular.reference': 'Caso de referência',
    'molecular.referenceNote':
      'A distribuição log-normal é a forma que uma polimerização radicalar bem controlada se aproxima. Suas propriedades são conhecidas analiticamente, o que a torna uma boa conferência.',
    'molecular.referenceDispersity': 'Dispersividade alvo',
    'molecular.generate': 'Gerar',

    'thermal.title': 'Análise térmica',
    'thermal.intro':
      'TGA fornece temperaturas de degradação e resíduo; DSC fornece transição vítrea, fusão e cristalinidade.',
    'thermal.tga': 'TGA',
    'thermal.dsc': 'DSC',
    'thermal.f.dtg.name': 'DTG (termogravimetria derivada)',
    'thermal.f.dtg.m': 'massa da amostra, em porcentagem da massa inicial',
    'thermal.f.dtg.T': 'temperatura do forno (°C)',
    'thermal.f.dtg.note': 'O sinal é escolhido para que uma perda de massa seja positiva. Reporta-se apenas a temperatura do máximo, não a sua altura, porque a altura escala com a taxa de aquecimento e não é comparável entre ensaios a taxas diferentes.',
    'thermal.f.td.name': 'Temperatura de decomposição Td',
    'thermal.f.td.x': 'a perda de massa que define o início, aqui 5 % e 10 %',
    'thermal.f.td.m': 'porcentagem de massa restante, suavizada',
    'thermal.f.td.note': 'A Td(5 %) é o início convencional. Valores abaixo de ~150 °C costumam ser água ou solvente residual, não quebra de cadeia, então uma Td(5 %) perto de 100 °C não significa que o polímero seja instável.',
    'thermal.f.res.name': 'Resíduo',
    'thermal.f.res.note': 'Lido na última temperatura do ensaio, e portanto depende da faixa do instrumento. Um ensaio que termina a 600 °C e outro a 800 °C podem dar resíduos diferentes para o mesmo material.',
    'thermal.f.smooth.name': 'Suavização',
    'thermal.f.smooth.w': 'comprimento da janela em pontos; um valor par é reduzido em um para a janela ficar centrada',
    'thermal.f.smooth.note': 'A derivada amplifica o ruído, então a curva de massa é suavizada antes. A janela padrão de 11 pontos é um compromisso: mais larga é mais estável, mas funde passos próximos.',
    'thermal.f.uniform.name': 'Eixo de temperatura irregular',
    'thermal.f.uniform.note': 'Exportações de instrumento não estão ordenadas nem igualmente espaçadas: o mesmo set-point é registrado muitas vezes e o espaçamento varia dentro do ensaio. Derivar nesse eixo faz o np.gradient dividir por um intervalo de largura zero e devolver NaN, e a busca de pico passa a reportar o fim da varredura. Por isso o traço é ordenado, as amostras que partilham temperatura são promediadas, e a derivada é tomada numa grelha uniforme.',
    'thermal.f.dscpeak.name': 'Entalpia de fusão',
    'thermal.f.dscpeak.Hm': 'entalpia específica da transição de fusão (J/g)',
    'thermal.f.dscpeak.q': 'fluxo de calor por unidade de massa (W/g), endotérmico para cima',
    'thermal.f.dscpeak.beta': 'taxa de aquecimento (K/s); dividir por ela converte a integral no tempo em entalpia',
    'thermal.f.dscpeak.note': 'O resultado depende muito da linha de base. Esta ferramenta ajusta a linha de base nos flancos, fora do pico, porque uma reta ligando as duas pontas da varredura acompanha a mudança de capacidade térmica e infla a entalpia.',
    'thermal.f.xc.name': 'Grau de cristalinidade',
    'thermal.f.xc.Hm': 'entalpia de fusão medida (J/g)',
    'thermal.f.xc.Hm0': 'entalpia de fusão do polímero totalmente cristalino, fornecida por você (ex.: 139,5 J/g para PCL, 93 J/g para PLLA)',
    'thermal.f.xc.note': 'Xc só faz sentido se ΔHm° corresponder ao seu polímero e à sua forma cristalina. É uma fração mássica, ignora material amorfo rígido, e não pode passar de 100 %: um valor acima disso significa que a linha de base está errada, não que a amostra seja excepcional.',
    'thermal.shortTraceWarning':
      'Um traço curto dá um DTG pouco confiável; exporte o ensaio completo se puder.',
    'thermal.temperature': 'Temperatura (°C)',
    'thermal.massPct': 'Massa restante (%)',
    'thermal.heatFlow': 'Fluxo de calor (W/g)',
    'thermal.heatingRate': 'Taxa de aquecimento (K/min)',
    'thermal.heatingRateHint':
      'Necessária para entalpias: o sinal é integrado em temperatura, então a taxa é necessária para obter J/g.',
    'thermal.refEnthalpy': 'Entalpia de fusão de referência (J/g)',
    'thermal.refEnthalpyHint':
      'A entalpia de fusão do mesmo polímero totalmente cristalino. Necessária para cristalinidade, e precisa ser a forma polimórfica correta.',
    'thermal.Td5': 'Td com 5 % de perda',
    'thermal.Td10': 'Td com 10 % de perda',
    'thermal.TmaxRate': 'Pico de taxa de decomposição',
    'thermal.TmaxRateNote':
      'A etapa que perde massa mais rápido. Havendo várias etapas, não é necessariamente a primeira.',
    'thermal.residue': 'Resíduo',
    'thermal.steps': 'Etapas de decomposição',
    'thermal.Tg': 'Transição vítrea',
    'confidence.read': 'lido',
    'confidence.read.hint':
      'Propriedade do arquivo de entrada, ou transformação determinística dele. Nada aqui é inferência.',
    'confidence.formula': 'fórmula',
    'confidence.formula.hint':
      'Fórmula publicada aplicada a uma entrada declarada. Cite a fórmula e seus limites e o número se reproduz.',
    'confidence.suggested': 'sugerido',
    'confidence.suggested.hint':
      'Inferência a partir da forma do traço. Pode estar errada: em dados reais de instrumento a identificação de transição não é confiável o bastante para ser chamada de medição.',
    'confidence.why': 'Por que este valor?',
    'thermal.reliable': 'estável ao reamostrar',
    'thermal.notReliable': 'INSTÁVEL - não cite sem repetições',
    'thermal.TgNote':
      'Ponto médio ASTM D3418. Uma única varredura carrega a história térmica; o ciclo aquece-resfria-aquece lido no segundo aquecimento é mais confiável.',
    'thermal.Tm': 'Ponto de fusão',
    'thermal.deltaHm': 'Entalpia de fusão',
    'thermal.deltaCp': 'Degrau de capacidade térmica',
    'thermal.crystallinity': 'Cristalinidade',
    'thermal.crystallinityNote':
      'Usa a entalpia de referência informada acima. Valor acima de 100 % significa que a referência não corresponde à amostra.',
    'thermal.trace': 'Curva',
    'thermal.dtg': 'Derivada',
    'thermal.modeQuestion': 'Qual análise será executada?',
    'thermal.modeTgaWhat':
      'Perda de massa em função da temperatura. Fornece Td, o pico de DTG e o resíduo.',
    'thermal.modeDscWhat':
      'Fluxo de calor em função da temperatura. Fornece Tg, Tm, entalpia de fusão e cristalinidade.',
    'thermal.activeMode': 'Ativo: {mode}',
    'thermal.runsAs': 'Seus dados serão analisados como uma curva {mode}.',
    'thermal.runsAsTga':
      'Seus dados serão analisados como uma curva TGA: a segunda coluna é lida como massa restante (%).',
    'thermal.runsAsDsc':
      'Seus dados serão analisados como uma curva DSC: a segunda coluna é lida como fluxo de calor (W/g).',
    'thermal.switchWarn':
      'Você tem dados carregados para {from}. Trocar para {to} não os analisará.',
    'thermal.clear': 'Limpar',
    'thermal.clearHint': 'Esvazia a curva atual e qualquer resultado.',
    'thermal.cleared': 'Limpo.',

    'mechanical.title': 'Propriedades de tração',
    'mechanical.intro':
      'Descritores padrão a partir de uma curva tensão-deformação de engenharia, conforme ISO 527-1.',
    'mechanical.strain': 'Deformação (%)',
    'mechanical.stress': 'Tensão (MPa)',
    'mechanical.modulus': 'Módulo de Young',
    'mechanical.modulusNote':
      'Inclinação da região linear inicial. A faixa de deformação usada é informada para permitir conferência.',
    'mechanical.window': 'Faixa de deformação usada',
    'mechanical.stressMax': 'Resistência à tração',
    'mechanical.strainMax': 'Deformação no máximo',
    'mechanical.stressBreak': 'Tensão na ruptura',
    'mechanical.strainBreak': 'Deformação na ruptura',
    'mechanical.stressYield': 'Tensão de escoamento',
    'mechanical.strainYield': 'Deformação de escoamento',
    'mechanical.toughness': 'Tenacidade',
    'mechanical.toughnessNote': 'Área sob a curva. O número menos preciso daqui.',
    'mechanical.yielded': 'Apresenta escoamento',
    'mechanical.brittle': 'Rompe na tensão máxima',
    'mechanical.curve': 'Curva tensão-deformação',

    'rheology.title': 'Cisalhamento oscilatório',
    'rheology.intro': 'Descritores de uma varredura de frequência de pequena amplitude.',
    'rheology.omega': 'Frequência angular (rad/s)',
    'rheology.gPrime': "Módulo de armazenamento G' (Pa)",
    'rheology.gDoublePrime': "Módulo de perda G'' (Pa)",
    'rheology.crossover': 'Cruzamento',
    'rheology.crossoverNote': "Frequência onde G' = G''. Seu inverso é o tempo de relaxação terminal.",
    'rheology.plateau': 'Módulo de platô',
    'rheology.plateauNote':
      'Estimado pelo mínimo de tan(δ). Tende a subestimar, porque o espectro completo de relaxação não é medido.',
    'rheology.relaxation': 'Tempo de relaxação',
    'rheology.slopes': 'Inclinações terminais',
    'rheology.slopesNote':
      "Para um fundido linear de distribuição estreita a teoria dá 2 para G' e 1 para G''. Valores bem menores indicam que a varredura não atingiu o regime terminal, então o módulo de platô e a viscosidade de cisalhamento zero não têm significado.",
    'rheology.zeroShear': 'Viscosidade de cisalhamento zero',
    'rheology.gel': 'Ponto de gel (Winter-Chambon)',
    'rheology.gelYes': 'tan(δ) independe da frequência — consistente com gel crítico',
    'rheology.gelNo': 'tan(δ) varia com a frequência — sem ponto de gel nesta janela',
    'rheology.solidLike': "G' supera G'' na menor frequência",
    'rheology.liquidLike': "G'' supera G' na menor frequência",
    'rheology.masterCurve': "G' e G'' em função da frequência",

    'structure.title': 'Estrutura',
    'structure.intro':
      'Difração de raios X para cristalinidade e tamanho de cristalito; infravermelho para grupos funcionais.',
    'structure.xrd': 'DRX',
    'structure.ftir': 'FTIR',
    'structure.twoTheta': '2θ (graus)',
    'structure.intensity': 'Intensidade',
    'structure.wavelength': 'Comprimento de onda (Å)',
    'structure.instrumentFwhm': 'Alargamento instrumental (FWHM, °)',
    'structure.instrumentFwhmHint':
      'Meça em um padrão como LaB6 ou silício. Deixar em zero faz todo tamanho de cristalito sair subestimado.',
    'structure.peaks': 'Picos',
    'structure.peak': '2θ',
    'structure.dSpacing': 'd (Å)',
    'structure.size': 'Tamanho (nm)',
    'structure.fwhm': 'FWHM (°)',
    'structure.crystallinity': 'Índice de cristalinidade',
    'structure.crystallinityNote':
      'NÃO é o grau absoluto de cristalinidade. Comparável apenas entre amostras medidas com a mesma faixa, linha de base e fendas.',
    'structure.wavenumber': 'Número de onda (cm⁻¹)',
    'structure.absorbance': 'Absorbância',
    'structure.bands': 'Bandas detectadas',
    'structure.band': 'Banda',
    'structure.assignments': 'Atribuições candidatas',
    'structure.pattern': 'Difratograma',
    'structure.spectrum': 'Espectro',
    'structure.kFactor': 'Constante de Scherrer K',
    'structure.kFactorHint':
      'Fator de forma na equação de Scherrer, tipicamente 0,9 para cristalitos esféricos. Altere apenas se conhecer o hábito do cristalito.',
    'structure.tolerance': 'Tolerância de casamento (cm⁻¹)',
    'structure.toleranceHint':
      'O quanto uma banda detectada pode se afastar de um valor de referência e ainda ser relatada como candidata. Zero exige posição exata.',
    'structure.ftirWarning':
      'Isto é uma consulta de grupos funcionais, não uma identificação. Muitos polímeros compartilham os mesmos grupos, e aditivos e umidade contribuem com bandas próprias. Confirme contra um espectro de referência medido no mesmo instrumento.',

    'structure.f.bragg.name': 'Lei de Bragg (distância interplanar)',
    'structure.f.bragg.d': 'distância entre planos (Å)',
    'structure.f.bragg.lambda': 'comprimento de onda dos raios X, Cu Kα = 1,5406 Å se você não alterar',
    'structure.f.bragg.theta': 'metade do ângulo de espalhamento',
    'structure.f.bragg.note': 'O comprimento de onda vem do valor que você informa, não é adivinhado. Um padrão coletado com radiação sincrotron ou de Mo dará distâncias erradas pela razão entre os comprimentos de onda se o padrão for mantido.',
    'structure.f.scherrer.name': 'Equação de Scherrer (tamanho de cristalito)',
    'structure.f.scherrer.D': 'tamanho aparente do cristalito, normal ao plano refletor (nm)',
    'structure.f.scherrer.K': 'fator de forma, 0,9 para cristalitos aproximadamente esféricos',
    'structure.f.scherrer.lambda': 'comprimento de onda dos raios X (Å)',
    'structure.f.scherrer.beta': 'FWHM da reflexão, em radianos, corrigida do alargamento instrumental',
    'structure.f.scherrer.theta': 'ângulo de Bragg',
    'structure.f.scherrer.note': 'D é um tamanho médio ponderado por volume em uma direção, não um tamanho de partícula nem de grão. É um limite inferior: qualquer deformação ou distribuição de tamanhos alarga o pico ainda mais e reduz D. Valores abaixo de poucos nanômetros não são físicos.',
    'structure.f.fwhm.name': 'Largura do pico',
    'structure.f.fwhm.note': 'Medida na metade da altura do pico acima da linha de base local. Picos muito próximos de um vizinho, ou fracos demais para se separar do ruído, são reportados como não mensuráveis em vez de receberem uma largura inventada.',
    'structure.f.xc.name': 'Índice de cristalinidade (DRX)',
    'structure.f.xc.note': 'A área acima de uma corda reta entre as extremidades do padrão, sobre a área total. É um índice, não uma fração mássica: depende da faixa angular, da fenda e da linha de base. Não é comparável com a cristalinidade do DSC, e é reportado como indisponível quando a corda não corta o padrão, porque aí todos os pontos contariam como cristalinos.',
    'mech.f.young.name': 'Modulo de Young',
    'mech.f.young.E': 'modulo de tracao (MPa)',
    'mech.f.young.sigma': 'tensao de engenharia (MPa), forca sobre a seccao original',
    'mech.f.young.epsilon': 'deformacao de engenharia (%)',
    'mech.f.young.note': 'O modulo so e comparavel entre amostras ajustadas na mesma faixa de deformacao. Um modulo ajustado de 0 a 5 % e sistematicamente menor que um ajustado de 0 a 0,5 %, porque a curva encurva ao escoar. A faixa usada e reportada junto com o resultado.',
    'mech.f.fit.name': 'Ajuste linear',
    'mech.f.fit.note': 'Minimos quadrados na janela de deformacao, detectada pela maior inclinacao local ou informada por voce. Uma janela que comece depois da regiao de acomodacao deve ser escolhida a olho; a deteccao automatica pode cair no ombro de escoamento numa amostra ductil.',
    'mech.f.sigma.name': 'Tensao e deformacao',
    'mech.f.sigma.F': 'forca aplicada (N)',
    'mech.f.sigma.A0': 'area da seccao antes do ensaio (mm2)',
    'mech.f.sigma.L0': 'comprimento util antes do ensaio (mm)',
    'mech.f.sigma.note': 'Sao valores de engenharia do inicio ao fim: a area original e usada e nunca atualizada durante o ensaio. A tensao real e maior numa amostra que estrica, entao a resistencia a tracao reportada aqui e conservadora.',
    'mech.f.toughness.name': 'Tenacidade',
    'mech.f.toughness.note': 'Area trapezoidal sob a curva fornecida. Se o ensaio foi interrompido antes da ruptura, o valor e um limite inferior e a ferramenta o reporta sem saber a diferenca.',
    'rheo.f.moduli.name': 'Modulos de armazenamento e de perda',
    'rheo.f.moduli.Gp': 'modulo de armazenamento (Pa), a resposta elastica',
    'rheo.f.moduli.Gpp': 'modulo de perda (Pa), a resposta viscosa',
    'rheo.f.moduli.delta': 'defasagem entre tensao e deformacao (rad)',
    'rheo.f.moduli.note': 'Valido apenas dentro da regiao viscoelastica linear, onde os modulos nao dependem da amplitude de deformacao. Uma varredura fora dela reporta um modulo de armazenamento menor que parece mudanca de material e nao e.',
    'rheo.f.tan.name': 'Tangente de perda',
    'rheo.f.tan.note': 'Acima de 1 a amostra dissipa mais do que armazena. Num fundido isso e normal; numa rede reticulada indica que o ensaio esta acima do ponto de gel ou que a rede nao esta totalmente formada.',
    'rheo.f.gel.name': 'Ponto de gel',
    'rheo.f.gel.note': 'Reportado apenas quando os dois modulos permanecem dentro da tolerancia um do outro enquanto o modulo de armazenamento excede o de perda. A tolerancia importa: um teste de cruzamento simples dispara com ruido numa varredura ruidosa, entao os dois modulos precisam concordar em varios pontos consecutivos.',
    'rheo.f.cross.name': 'Frequencia de cruzamento',
    'rheo.f.cross.note': 'A frequencia onde o fundido deixa de se comportar elasticamente. Ela desloca com a temperatura, entao um cruzamento citado sem a temperatura nao e reproduzivel.',
    'mol.f.mn.name': 'Medias numerica e ponderal',
    'mol.f.mn.Ni': 'numero de cadeias de massa molar Mi',
    'mol.f.mn.Mi': 'massa molar da especie i (g/mol)',
    'mol.f.mn.note': 'Mn e a media simples entre cadeias, Mw pondera cada cadeia pela sua massa. Mw e sempre maior ou igual a Mn; se um resultado violar isso, o erro esta nos dados ou na aritmetica, nao no polimero.',
    'mol.f.pdi.name': 'Dispersidade',
    'mol.f.pdi.note': 'Uma dispersidade de 1,0 significa que todas as cadeias tem o mesmo comprimento, o que nenhuma polimerizacao real atinge: o minimo teorico para uma polimerizacao anionica viva e cerca de 1,02. Valores proximos de 2 indicam mecanismo de etapas ou dominado por transferencia de cadeia.',
    'mol.f.mz.name': 'Media z',
    'mol.f.mz.note': 'A media z e a usada em espalhamento de luz e em viscosimetria, entao compara-la com o Mw do mesmo traco verifica a forma da distribuicao, nao apenas a sua posicao.',
    'mol.f.mh.name': 'Mark-Houwink-Sakurada',
    'mol.f.mh.Mv': 'massa molar media viscosimetrica (g/mol)',
    'mol.f.mh.K': 'constante especifica do polimero, solvente e temperatura',
    'mol.f.mh.a': 'expoente, 0,5 num solvente teta e ate cerca de 0,8 num bom solvente',
    'mol.f.mh.note': 'Mv fica entre Mn e Mw e se aproxima de Mw quando a esta perto de 1. Usar K e a de outro solvente ou temperatura da uma massa molar sistematicamente errada que parece perfeitamente razoavel.',
    'mol.f.gpc.name': 'Calibracao em SEC',
    'mol.f.gpc.note': 'A curva de calibracao converte volume de eluicao em massa molar usando padroes de outro polimero, a menos que os padroes sejam do mesmo material da amostra. Por isso um resultado de SEC convencional e uma massa molar relativa, e por isso o padrao de calibracao precisa ser reportado.',
    'mol.f.log.name': 'Distribuicao log-normal',
    'mol.f.log.note': 'Um modelo, nao uma medida. E mostrada para comparar a forma de uma distribuicao medida com uma idealizada, e presume que o traco nao tem alargamento de coluna, que alarga todo traco real.',
    'error.needData': 'Informe um arquivo ou digite os valores.',
    'error.needFile': 'Escolha um arquivo primeiro.',

    'file.choose': 'Escolher um arquivo de dados',
    'file.chooseOrDrop': 'Escolha um arquivo ou arraste até aqui',
    'file.accepted': 'Aceitos: {list}',
    'file.clear': 'Remover arquivo',
    'file.unsupported':
      'A extensão {ext} não é um formato de texto que esta ferramenta leia. Exporte o traço como CSV ou TXT.',
    'file.tooLarge':
      'O arquivo tem mais de {mb} MB e não será lido no navegador. Exporte um traço mais grosseiro.',
    'file.readFailed': 'Não foi possível ler o arquivo {name}.',
    'file.loaded': '{name} carregado: {n} pontos.',
    'file.noPoints':
      'Não foi possível ler nenhum par numérico de {name}. Pode ser um formato binário do instrumento; exporte como CSV ou TXT.',
    'file.pickColumns':
      'O arquivo tem mais de duas colunas. Está sendo usado o par {a} e {b}; mude as colunas abaixo se estiver errado.',
    'file.columnA': 'Coluna X',
    'file.columnB': 'Coluna Y',
    'error.tooFewPoints': 'São necessários ao menos {n} pontos.',
    'error.mismatched': 'As duas colunas precisam ter o mesmo número de valores.',
    'error.badNumbers': 'Alguns valores não puderam ser lidos como números.',
  },

  es: {
    'mech.f.fit.E': 'Modulo de traccion, la pendiente de la recta ajustada, en MPa.',
    'mech.f.fit.eps': 'Deformacion del punto i dentro de la ventana ajustada.',
    'mech.f.fit.sig': 'Tension del punto i dentro de la ventana ajustada, en MPa.',
    'mech.f.toughness.U': 'Energia en la ruptura por unidad de volumen, el area bajo la curva, en MJ/m3.',
    'mech.f.toughness.sig': 'Tension de ingenieria, en MPa.',
    'mech.f.toughness.eps': 'Deformacion de ingenieria, adimensional.',
    'mol.f.pdi.D': 'Dispersidad, Mw dividido por Mn. 1,0 significa que todas las cadenas tienen la misma longitud.',
    'mol.f.pdi.Mw': 'Masa molar media en peso.',
    'mol.f.pdi.Mn': 'Masa molar media en numero.',
    'mol.f.mz.Ni': 'Numero de cadenas de masa molar Mi.',
    'mol.f.mz.Mi': 'Masa molar de la especie i.',
    'mol.f.gpc.M': 'Masa molar leida en la curva de calibracion en el volumen de elucion dado.',
    'mol.f.log.w': 'Fraccion en peso en la porcion de la distribucion centrada en M.',
    'mol.f.log.sigma': 'Ancho de la distribucion log-normal en ln M.',
    'mol.f.log.mu': 'Media de ln M de la distribucion.',
    'rheo.f.tan.Gpp': 'Modulo de perdida, la respuesta viscosa (disipadora de energia).',
    'rheo.f.tan.Gp': 'Modulo de almacenamiento, la respuesta elastica (acumuladora de energia).',
    'rheo.f.gel.Gp': 'Modulo de almacenamiento en el punto de gel.',
    'rheo.f.gel.Gpp': 'Modulo de perdida en el punto de gel.',
    'rheo.f.cross.Gp': 'Modulo de almacenamiento, en Pa.',
    'rheo.f.cross.Gpp': 'Modulo de perdida, en Pa.',
    "rheo.f.cross.tan": "Tangente de perdida, G'' / G'. Vale exactamente 1 en el cruce.",
    'structure.f.fwhm.beta': 'Anchura a mitad de altura de la reflexion, en radianes.',
    'structure.f.fwhm.tt': 'Angulo de difraccion, el doble del angulo de Bragg, en grados.',
    'structure.f.xc.A': 'Area de las reflexiones cristalinas sobre el fondo amorfo.',
    'structure.f.xc.At': 'Area total del patron en el mismo rango angular.',
    'thermal.f.res.mf': 'Masa al final del ensayo, como porcentaje de la masa inicial.',
    'thermal.f.uniform.dtg': 'Velocidad de perdida de masa, en porcentaje por grado Celsius.',

    'app.title': 'Polymer Analysis Toolkit',
    'app.subtitle': 'Herramientas abiertas de caracterización para científicos de polímeros',
    'app.tagline':
      'Cada resultado indica su método, sus unidades y sus hipótesis. Nada aquí es una caja negra.',
    'app.footer.developed': 'Desarrollado por',
    'app.footer.repo': 'Código fuente',
    'app.footer.docs': 'Documentación de la API',

    'nav.molecular': 'Masa molar',
    'nav.thermal': 'Térmica',
    'nav.mechanical': 'Mecánica',
    'nav.rheology': 'Reología',
    'nav.structure': 'Estructura',

    'common.calculate': 'Calcular',
    'common.calculating': 'Calculando…',
    'common.reset': 'Limpiar',
    'common.loading': 'Cargando…',
    'common.results': 'Resultados',
    'common.error': 'Error',
    'common.optional': 'opcional',
    'common.required': 'obligatorio',
    'common.upload': 'Subir un archivo',
    'common.chooseFile': 'Elegir archivo',
    'common.downloadPng': 'Descargar gráfico (PNG)',
    'common.downloadPngFailed': 'No se pudo generar la imagen del gráfico.',
    'common.downloadBundle': 'Descargar resultados + gráfico (.zip)',
    'common.downloadBundleFailed': 'No se pudo preparar la descarga.',
    'common.noFile': 'Ningún archivo seleccionado',
    'common.exportJson': 'Exportar JSON',
    'common.importDecisions': 'Cómo se leyó el archivo',
    'common.showDetails': 'Ver detalles',
    'common.hideDetails': 'Ocultar detalles',
    'common.formulasAndModels': 'Fórmulas, modelos y referencias',
    'common.slices': 'fracciones',
    'common.apiUrl': 'API',
    'common.apiUnreachable': 'API inaccesible',
    'common.apiOk': 'API en línea',
    'common.language': 'Idioma',

    'molecular.title': 'Distribución de masa molar',
    'molecular.intro':
      'Calcule los promedios de masa molar a partir de una distribución, subiendo la exportación del equipo o introduciendo los valores.',
    'molecular.uploadLabel': 'Exportación del equipo (CSV o texto delimitado)',
    'molecular.uploadHint':
      'Se aceptan: masa/fracción en g/mol, porcentajes, intensidad bruta del detector, eje logM, delimitador por coma o punto y coma, coma decimal, cabecera en español, inglés o portugués.',
    'molecular.preview': 'Inspeccionar archivo',
    'molecular.previewHint':
      'Muestra cómo interpretó el importador el archivo antes de calcular nada.',
    'molecular.normalise': 'Normalizar las fracciones por su suma',
    'molecular.normaliseHint':
      'Úselo cuando los valores son porcentajes o intensidades brutas en lugar de fracciones que suman uno.',
    'molecular.markHouwink': 'Exponente de Mark-Houwink a',
    'molecular.markHouwinkHint':
      'Opcional. Al indicar un valor también se calcula Mv, la masa molar promedio viscosimétrica. El exponente es específico del polímero, disolvente y temperatura, y debe provenir de un handbook o artículo.',
    'molecular.manualEntry': 'Introducir la distribución directamente',
    'molecular.masses': 'Masas molares (g/mol)',
    'molecular.fractions': 'Fracciones en peso',
    'molecular.pairHint': 'Un valor por línea, en el mismo orden.',
    'molecular.Mn': 'Promedio numérico',
    'molecular.Mw': 'Promedio ponderal',
    'molecular.Mz': 'Promedio Z',
    'molecular.Mz1': 'Promedio Z+1',
    'molecular.Mv': 'Promedio viscosimétrico',
    'molecular.dispersity': 'Dispersidad (Đ)',
    'molecular.dispersityNote':
      'Đ = Mw/Mn. Cerca de 1,0 en polimerización controlada, por encima de 1,5 en radicalaria no controlada.',
    'molecular.MnNote': 'Ponderado por el número de cadenas.',
    'molecular.MwNote': 'Ponderado por masa. Es el valor que da la dispersión de luz.',
    'molecular.MzNote': 'Sensible a la cola de alta masa.',
    'molecular.Mz1Note': 'Muy sensible a la cola de alta masa.',
    'molecular.distribution': 'Distribución en peso',
    'molecular.crossCheck': 'Contraste con el archivo',
    'molecular.crossCheckNote':
      'El equipo informó sus propios promedios. Una diferencia grande significa que el archivo se leyó mal.',
    'molecular.fileMn': 'Mn en el archivo',
    'molecular.fileMw': 'Mw en el archivo',
    'molecular.calcMn': 'Mn calculado',
    'molecular.calcMw': 'Mw calculado',
    'molecular.reference': 'Caso de referencia',
    'molecular.referenceNote':
      'La distribución log-normal es la forma a la que se aproxima una polimerización radicalaria bien controlada. Sus propiedades se conocen analíticamente, lo que la hace útil como comprobación.',
    'molecular.referenceDispersity': 'Dispersidad objetivo',
    'molecular.generate': 'Generar',

    'thermal.title': 'Análisis térmico',
    'thermal.intro':
      'TGA da temperaturas de degradación y residuo; DSC da la transición vítrea, la fusión y la cristalinidad.',
    'thermal.tga': 'TGA',
    'thermal.dsc': 'DSC',
    'thermal.f.dtg.name': 'DTG (termogravimetría derivada)',
    'thermal.f.dtg.m': 'masa de la muestra, en porcentaje de la masa inicial',
    'thermal.f.dtg.T': 'temperatura del horno (°C)',
    'thermal.f.dtg.note': 'El signo se elige para que una pérdida de masa sea positiva. Solo se informa la temperatura del máximo, no su altura, porque la altura escala con la velocidad de calentamiento y no es comparable entre ensayos a velocidades distintas.',
    'thermal.f.td.name': 'Temperatura de descomposición Td',
    'thermal.f.td.x': 'la pérdida de masa que define el inicio, aquí 5 % y 10 %',
    'thermal.f.td.m': 'porcentaje de masa restante, suavizado',
    'thermal.f.td.note': 'La Td(5 %) es el inicio convencional. Valores por debajo de ~150 °C suelen ser agua o disolvente residual, no ruptura de cadena, así que una Td(5 %) cerca de 100 °C no significa que el polímero sea inestable.',
    'thermal.f.res.name': 'Residuo',
    'thermal.f.res.note': 'Se lee en la última temperatura del ensayo, por lo que depende del rango del instrumento. Un ensayo que termina a 600 °C y otro a 800 °C pueden dar residuos distintos para el mismo material.',
    'thermal.f.smooth.name': 'Suavizado',
    'thermal.f.smooth.w': 'longitud de la ventana en puntos; un valor par se reduce en uno para que la ventana quede centrada',
    'thermal.f.smooth.note': 'La derivada amplifica el ruido, así que la curva de masa se suaviza antes. La ventana estándar de 11 puntos es un compromiso: más ancha es más estable, pero fusiona pasos próximos.',
    'thermal.f.uniform.name': 'Eje de temperatura irregular',
    'thermal.f.uniform.note': 'Las exportaciones del instrumento no están ordenadas ni igualmente espaciadas: el mismo punto de consigna se registra muchas veces y el espaciado varía dentro del ensayo. Derivar en ese eje hace que np.gradient divida por un intervalo de ancho cero y devuelva NaN, y la búsqueda del pico pasa a informar el final del barrido. Por eso la traza se ordena, las muestras que comparten temperatura se promedian y la derivada se toma en una rejilla uniforme.',
    'thermal.f.dscpeak.name': 'Entalpía de fusión',
    'thermal.f.dscpeak.Hm': 'entalpía específica de la transición de fusión (J/g)',
    'thermal.f.dscpeak.q': 'flujo de calor por unidad de masa (W/g), endotérmico hacia arriba',
    'thermal.f.dscpeak.beta': 'velocidad de calentamiento (K/s); dividir por ella convierte la integral en el tiempo en entalpía',
    'thermal.f.dscpeak.note': 'El resultado depende mucho de la línea base. Esta herramienta ajusta la línea base en los flancos, fuera del pico, porque una recta que une los dos extremos del barrido sigue el cambio de capacidad calorífica e infla la entalpía.',
    'thermal.f.xc.name': 'Grado de cristalinidad',
    'thermal.f.xc.Hm': 'entalpía de fusión medida (J/g)',
    'thermal.f.xc.Hm0': 'entalpía de fusión del polímero totalmente cristalino, proporcionada por usted (p. ej. 139,5 J/g para PCL, 93 J/g para PLLA)',
    'thermal.f.xc.note': 'Xc solo tiene sentido si ΔHm° corresponde a su polímero y a su forma cristalina. Es una fracción másica, ignora el material amorfo rígido y no puede superar 100 %: un valor por encima significa que la línea base está mal, no que la muestra sea excepcional.',
    'thermal.shortTraceWarning':
      'Una traza corta da un DTG poco fiable; exporte el ensayo completo si puede.',
    'thermal.temperature': 'Temperatura (°C)',
    'thermal.massPct': 'Masa restante (%)',
    'thermal.heatFlow': 'Flujo de calor (W/g)',
    'thermal.heatingRate': 'Velocidad de calentamiento (K/min)',
    'thermal.heatingRateHint':
      'Necesaria para entalpías: la señal se integra en temperatura, así que la velocidad es necesaria para obtener J/g.',
    'thermal.refEnthalpy': 'Entalpía de fusión de referencia (J/g)',
    'thermal.refEnthalpyHint':
      'La entalpía de fusión del mismo polímero totalmente cristalino. Necesaria para la cristalinidad, y debe ser el polimorfo correcto.',
    'thermal.Td5': 'Td con 5 % de pérdida',
    'thermal.Td10': 'Td con 10 % de pérdida',
    'thermal.TmaxRate': 'Pico de velocidad de descomposición',
    'thermal.TmaxRateNote':
      'La etapa que pierde masa más rápido. Con varias etapas no es necesariamente la primera.',
    'thermal.residue': 'Residuo',
    'thermal.steps': 'Etapas de descomposición',
    'thermal.Tg': 'Transición vítrea',
    'confidence.read': 'leído',
    'confidence.read.hint':
      'Propiedad del archivo de entrada, o una transformación determinista del mismo. Nada aquí es una inferencia.',
    'confidence.formula': 'fórmula',
    'confidence.formula.hint':
      'Fórmula publicada aplicada a una entrada declarada. Cite la fórmula y sus límites y el número se reproduce.',
    'confidence.suggested': 'sugerido',
    'confidence.suggested.hint':
      'Inferencia a partir de la forma de la traza. Puede estar equivocada: en datos reales de instrumento la identificación de transiciones no es lo bastante fiable para llamarla medición.',
    'confidence.why': '¿Por qué este valor?',
    'thermal.reliable': 'estable al remuestrear',
    'thermal.notReliable': 'INESTABLE - no citar sin repeticiones',
    'thermal.TgNote':
      'Punto medio ASTM D3418. Un único calentamiento arrastra la historia térmica; el ciclo calienta-enfría-calienta leído en el segundo calentamiento es más fiable.',
    'thermal.Tm': 'Punto de fusión',
    'thermal.deltaHm': 'Entalpía de fusión',
    'thermal.deltaCp': 'Salto de capacidad calorífica',
    'thermal.crystallinity': 'Cristalinidad',
    'thermal.crystallinityNote':
      'Usa la entalpía de referencia indicada arriba. Un valor por encima de 100 % significa que la referencia no corresponde a la muestra.',
    'thermal.trace': 'Curva',
    'thermal.dtg': 'Derivada',
    'thermal.modeQuestion': '¿Qué análisis se ejecutará?',
    'thermal.modeTgaWhat':
      'Pérdida de masa frente a temperatura. Proporciona Td, el pico de DTG y el residuo.',
    'thermal.modeDscWhat':
      'Flujo de calor frente a temperatura. Proporciona Tg, Tm, entalpía de fusión y cristalinidad.',
    'thermal.activeMode': 'Activo: {mode}',
    'thermal.runsAs': 'Sus datos se analizarán como una curva {mode}.',
    'thermal.runsAsTga':
      'Sus datos se analizarán como una curva TGA: la segunda columna se lee como masa restante (%).',
    'thermal.runsAsDsc':
      'Sus datos se analizarán como una curva DSC: la segunda columna se lee como flujo de calor (W/g).',
    'thermal.switchWarn':
      'Tiene datos cargados para {from}. Cambiar a {to} no los analizará.',
    'thermal.clear': 'Limpiar',
    'thermal.clearHint': 'Vacía la curva actual y cualquier resultado.',
    'thermal.cleared': 'Limpiado.',

    'mechanical.title': 'Propiedades de tracción',
    'mechanical.intro':
      'Descriptores estándar de una curva tensión-deformación de ingeniería, según ISO 527-1.',
    'mechanical.strain': 'Deformación (%)',
    'mechanical.stress': 'Tensión (MPa)',
    'mechanical.modulus': 'Módulo de Young',
    'mechanical.modulusNote':
      'Pendiente de la región lineal inicial. Se informa el intervalo de deformación usado para poder verificarlo.',
    'mechanical.window': 'Intervalo de deformación usado',
    'mechanical.stressMax': 'Resistencia a la tracción',
    'mechanical.strainMax': 'Deformación en el máximo',
    'mechanical.stressBreak': 'Tensión de rotura',
    'mechanical.strainBreak': 'Deformación de rotura',
    'mechanical.stressYield': 'Tensión de fluencia',
    'mechanical.strainYield': 'Deformación de fluencia',
    'mechanical.toughness': 'Tenacidad',
    'mechanical.toughnessNote': 'Área bajo la curva. El número menos preciso de aquí.',
    'mechanical.yielded': 'Presenta fluencia',
    'mechanical.brittle': 'Rompe en la tensión máxima',
    'mechanical.curve': 'Curva tensión-deformación',

    'rheology.title': 'Cizalla oscilatoria',
    'rheology.intro': 'Descriptores de un barrido de frecuencia de pequeña amplitud.',
    'rheology.omega': 'Frecuencia angular (rad/s)',
    'rheology.gPrime': "Módulo de almacenamiento G' (Pa)",
    'rheology.gDoublePrime': "Módulo de pérdida G'' (Pa)",
    'rheology.crossover': 'Cruce',
    'rheology.crossoverNote': "Frecuencia donde G' = G''. Su inversa es el tiempo de relajación terminal.",
    'rheology.plateau': 'Módulo de plateau',
    'rheology.plateauNote':
      'Estimado del mínimo de tan(δ). Tiende a subestimar, porque no se mide el espectro completo de relajación.',
    'rheology.relaxation': 'Tiempo de relajación',
    'rheology.slopes': 'Pendientes terminales',
    'rheology.slopesNote':
      "Para un fundido lineal de distribución estrecha la teoría da 2 para G' y 1 para G''. Valores mucho menores indican que el barrido no alcanzó el régimen terminal, así que el módulo de plateau y la viscosidad de cizalla cero no son significativos.",
    'rheology.zeroShear': 'Viscosidad de cizalla cero',
    'rheology.gel': 'Punto de gel (Winter-Chambon)',
    'rheology.gelYes': 'tan(δ) no depende de la frecuencia — consistente con gel crítico',
    'rheology.gelNo': 'tan(δ) varía con la frecuencia — sin punto de gel en esta ventana',
    'rheology.solidLike': "G' supera a G'' en la frecuencia más baja",
    'rheology.liquidLike': "G'' supera a G' en la frecuencia más baja",
    'rheology.masterCurve': "G' y G'' frente a la frecuencia",

    'structure.title': 'Estructura',
    'structure.intro':
      'Difracción de rayos X para cristalinidad y tamaño de cristalito; infrarrojo para grupos funcionales.',
    'structure.xrd': 'DRX',
    'structure.ftir': 'FTIR',
    'structure.twoTheta': '2θ (grados)',
    'structure.intensity': 'Intensidad',
    'structure.wavelength': 'Longitud de onda (Å)',
    'structure.instrumentFwhm': 'Ensanchamiento instrumental (FWHM, °)',
    'structure.instrumentFwhmHint':
      'Mídalo en un estándar como LaB6 o silicio. Dejarlo en cero hace que todo tamaño de cristalito salga subestimado.',
    'structure.peaks': 'Picos',
    'structure.peak': '2θ',
    'structure.dSpacing': 'd (Å)',
    'structure.size': 'Tamaño (nm)',
    'structure.fwhm': 'FWHM (°)',
    'structure.crystallinity': 'Índice de cristalinidad',
    'structure.crystallinityNote':
      'NO es el grado absoluto de cristalinidad. Comparable solo entre muestras medidas con el mismo rango, línea base y rendijas.',
    'structure.wavenumber': 'Número de onda (cm⁻¹)',
    'structure.absorbance': 'Absorbancia',
    'structure.bands': 'Bandas detectadas',
    'structure.band': 'Banda',
    'structure.assignments': 'Asignaciones candidatas',
    'structure.pattern': 'Difractograma',
    'structure.spectrum': 'Espectro',
    'structure.kFactor': 'Constante de Scherrer K',
    'structure.kFactorHint':
      'Factor de forma en la ecuación de Scherrer, típicamente 0,9 para cristalitos esféricos. Cámbielo solo si conoce el hábito del cristalito.',
    'structure.tolerance': 'Tolerancia de coincidencia (cm⁻¹)',
    'structure.toleranceHint':
      'Cuánto puede alejarse una banda detectada de un valor de referencia y seguir reportándose como candidata. Cero exige posición exacta.',
    'structure.ftirWarning':
      'Esto es una consulta de grupos funcionales, no una identificación. Muchos polímeros comparten los mismos grupos, y los aditivos y la humedad aportan sus propias bandas. Confirme contra un espectro de referencia medido en el mismo instrumento.',

    'structure.f.bragg.name': 'Ley de Bragg (distancia interplanar)',
    'structure.f.bragg.d': 'distancia entre planos (Å)',
    'structure.f.bragg.lambda': 'longitud de onda de los rayos X, Cu Kα = 1,5406 Å si no la cambia',
    'structure.f.bragg.theta': 'la mitad del ángulo de dispersión',
    'structure.f.bragg.note': 'La longitud de onda se toma del valor que usted introduce, no se adivina. Un patrón recogido con radiación de sincrotrón o de Mo dará distancias erróneas por la razón entre las longitudes de onda si se deja el valor por defecto.',
    'structure.f.scherrer.name': 'Ecuación de Scherrer (tamaño de cristalito)',
    'structure.f.scherrer.D': 'tamaño aparente del cristalito, normal al plano reflector (nm)',
    'structure.f.scherrer.K': 'factor de forma, 0,9 para cristalitos casi esféricos',
    'structure.f.scherrer.lambda': 'longitud de onda de los rayos X (Å)',
    'structure.f.scherrer.beta': 'FWHM de la reflexión, en radianes, corregida del ensanchamiento instrumental',
    'structure.f.scherrer.theta': 'ángulo de Bragg',
    'structure.f.scherrer.note': 'D es un tamaño medio ponderado por volumen en una dirección, no un tamaño de partícula ni de grano. Es un límite inferior: cualquier deformación o distribución de tamaños ensancha aún más el pico y reduce D. Valores por debajo de unos pocos nanómetros no son físicos.',
    'structure.f.fwhm.name': 'Anchura del pico',
    'structure.f.fwhm.note': 'Medida a la mitad de la altura del pico sobre la línea base local. Los picos demasiado próximos a un vecino, o demasiado débiles para separarse del ruido, se informan como no medibles en vez de recibir una anchura inventada.',
    'structure.f.xc.name': 'Índice de cristalinidad (DRX)',
    'structure.f.xc.note': 'El área por encima de una cuerda recta entre los extremos del patrón, sobre el área total. Es un índice, no una fracción másica: depende del rango angular, de las rendijas y de la línea base. No es comparable con la cristalinidad de DSC, y se informa como no disponible cuando la cuerda no corta el patrón, porque entonces todos los puntos contarían como cristalinos.',
    'mech.f.young.name': 'Modulo de Young',
    'mech.f.young.E': 'modulo de traccion (MPa)',
    'mech.f.young.sigma': 'tension de ingenieria (MPa), fuerza sobre la seccion original',
    'mech.f.young.epsilon': 'deformacion de ingenieria (%)',
    'mech.f.young.note': 'El modulo solo es comparable entre muestras ajustadas en el mismo rango de deformacion. Un modulo ajustado de 0 a 5 % es sistematicamente menor que uno ajustado de 0 a 0,5 %, porque la curva se dobla al ceder. El rango usado se informa junto con el resultado.',
    'mech.f.fit.name': 'Ajuste lineal',
    'mech.f.fit.note': 'Minimos cuadrados en la ventana de deformacion, detectada por la mayor pendiente local o proporcionada por usted. Una ventana que empiece despues de la region de acomodo debe elegirse a ojo; la deteccion automatica puede caer en el hombro de cedencia en una muestra ductil.',
    'mech.f.sigma.name': 'Tension y deformacion',
    'mech.f.sigma.F': 'fuerza aplicada (N)',
    'mech.f.sigma.A0': 'area de la seccion antes del ensayo (mm2)',
    'mech.f.sigma.L0': 'longitud de referencia antes del ensayo (mm)',
    'mech.f.sigma.note': 'Son valores de ingenieria de principio a fin: se usa el area original y nunca se actualiza durante el ensayo. La tension real es mayor en una muestra que estricciona, asi que la resistencia a traccion informada aqui es conservadora.',
    'mech.f.toughness.name': 'Tenacidad',
    'mech.f.toughness.note': 'Area trapezoidal bajo la curva suministrada. Si el ensayo se detuvo antes de la rotura, el valor es un limite inferior y la herramienta lo informa sin conocer la diferencia.',
    'rheo.f.moduli.name': 'Modulos de almacenamiento y de perdida',
    'rheo.f.moduli.Gp': 'modulo de almacenamiento (Pa), la respuesta elastica',
    'rheo.f.moduli.Gpp': 'modulo de perdida (Pa), la respuesta viscosa',
    'rheo.f.moduli.delta': 'desfase entre tension y deformacion (rad)',
    'rheo.f.moduli.note': 'Valido solo dentro de la region viscoelastica lineal, donde los modulos no dependen de la amplitud de deformacion. Un barrido fuera de ella informa un modulo de almacenamiento menor que parece un cambio de material y no lo es.',
    'rheo.f.tan.name': 'Tangente de perdida',
    'rheo.f.tan.note': 'Por encima de 1 la muestra disipa mas de lo que almacena. En un fundido esto es normal; en una red reticulada indica que el ensayo esta por encima del punto de gel o que la red no esta totalmente formada.',
    'rheo.f.gel.name': 'Punto de gel',
    'rheo.f.gel.note': 'Se informa solo cuando los dos modulos permanecen dentro de la tolerancia entre si mientras el modulo de almacenamiento supera al de perdida. La tolerancia importa: un test de cruce simple se dispara con ruido en un barrido ruidoso, asi que los dos modulos deben coincidir en varios puntos consecutivos.',
    'rheo.f.cross.name': 'Frecuencia de cruce',
    'rheo.f.cross.note': 'La frecuencia donde el fundido deja de comportarse elasticamente. Se desplaza con la temperatura, asi que un cruce citado sin su temperatura no es reproducible.',
    'mol.f.mn.name': 'Medias numerica y ponderal',
    'mol.f.mn.Ni': 'numero de cadenas de masa molar Mi',
    'mol.f.mn.Mi': 'masa molar de la especie i (g/mol)',
    'mol.f.mn.note': 'Mn es la media simple entre cadenas, Mw pondera cada cadena por su masa. Mw es siempre mayor o igual que Mn; si un resultado lo viola, el error esta en los datos o en la aritmetica, no en el polimero.',
    'mol.f.pdi.name': 'Dispersidad',
    'mol.f.pdi.note': 'Una dispersidad de 1,0 significa que todas las cadenas tienen la misma longitud, lo que ninguna polimerizacion real alcanza: el minimo teorico para una polimerizacion anionica viva es de unos 1,02. Valores cercanos a 2 indican un mecanismo por etapas o dominado por transferencia de cadena.',
    'mol.f.mz.name': 'Media z',
    'mol.f.mz.note': 'La media z es la que usan la dispersion de luz y la viscosimetria, asi que compararla con el Mw de la misma traza verifica la forma de la distribucion, no solo su posicion.',
    'mol.f.mh.name': 'Mark-Houwink-Sakurada',
    'mol.f.mh.Mv': 'masa molar media viscosimetrica (g/mol)',
    'mol.f.mh.K': 'constante especifica del polimero, disolvente y temperatura',
    'mol.f.mh.a': 'exponente, 0,5 en un disolvente teta y hasta unos 0,8 en un buen disolvente',
    'mol.f.mh.note': 'Mv queda entre Mn y Mw y se acerca a Mw cuando a esta cerca de 1. Usar K y a de otro disolvente o temperatura da una masa molar sistematicamente erronea que parece perfectamente razonable.',
    'mol.f.gpc.name': 'Calibracion en SEC',
    'mol.f.gpc.note': 'La curva de calibracion convierte el volumen de elucion en masa molar usando estandares de otro polimero, salvo que los estandares sean del mismo material que la muestra. Por eso un resultado de SEC convencional es una masa molar relativa, y por eso debe informarse el estandar de calibracion.',
    'mol.f.log.name': 'Distribucion log-normal',
    'mol.f.log.note': 'Un modelo, no una medicion. Se muestra para comparar la forma de una distribucion medida con una idealizada, y supone que la traza no tiene ensanchamiento de columna, que ensancha toda traza real.',
    'error.needData': 'Indique un archivo o introduzca los valores.',
    'error.needFile': 'Elija un archivo primero.',

    'file.choose': 'Elegir un archivo de datos',
    'file.chooseOrDrop': 'Elija un archivo o arrástrelo hasta aquí',
    'file.accepted': 'Aceptados: {list}',
    'file.clear': 'Quitar archivo',
    'file.unsupported':
      'La extensión {ext} no es un formato de texto que esta herramienta lea. Exporte la traza como CSV o TXT.',
    'file.tooLarge':
      'El archivo supera los {mb} MB y no se procesará en el navegador. Exporte una traza más gruesa.',
    'file.readFailed': 'No se pudo leer el archivo {name}.',
    'file.loaded': '{name} cargado: {n} puntos.',
    'file.noPoints':
      'No se pudo leer ningún par numérico de {name}. Puede ser un formato binario del instrumento; expórtelo como CSV o TXT.',
    'file.pickColumns':
      'El archivo tiene más de dos columnas. Se usa el par {a} y {b}; cambie las columnas abajo si es incorrecto.',
    'file.columnA': 'Columna X',
    'file.columnB': 'Columna Y',
    'error.tooFewPoints': 'Se necesitan al menos {n} puntos.',
    'error.mismatched': 'Las dos columnas deben tener el mismo número de valores.',
    'error.badNumbers': 'Algunos valores no pudieron leerse como números.',
  },
};

const STORAGE_KEY = 'pat.language';

function detectInitialLanguage() {
  if (typeof window === 'undefined') return 'en';
  const stored = window.localStorage?.getItem(STORAGE_KEY);
  if (stored && MESSAGES[stored]) return stored;
  const nav = window.navigator?.language?.slice(0, 2)?.toLowerCase();
  if (nav && MESSAGES[nav]) return nav;
  return 'en';
}

const I18nContext = createContext({
  language: 'en',
  setLanguage: () => {},
  t: (key) => key,
});

export function I18nProvider({ children }) {
  const [language, setLanguage] = useState(detectInitialLanguage);

  useEffect(() => {
    try {
      window.localStorage?.setItem(STORAGE_KEY, language);
    } catch {
      // Storage can be unavailable (private mode); the language still applies
      // for this session.
    }
    document.documentElement.lang = language;
  }, [language]);

  const value = useMemo(() => {
    const translate = (key, vars) => {
      const table = MESSAGES[language] || MESSAGES.en;
      let text = table[key];
      if (text === undefined) {
        text = MESSAGES.en[key];
        if (text === undefined) {
          if (process.env.NODE_ENV !== 'production') {
            // eslint-disable-next-line no-console
            console.warn(`[i18n] missing key: ${key}`);
          }
          return key;
        }
      }
      if (vars) {
        Object.entries(vars).forEach(([k, v]) => {
          text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
        });
      }
      return text;
    };
    return { language, setLanguage, t: translate };
  }, [language]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}

/** Format a number for display with a sensible precision for the magnitude. */
export function formatNumber(value, digits) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  if (typeof value !== 'number') return String(value);
  const abs = Math.abs(value);
  let d = digits;
  if (d === undefined) {
    if (abs === 0) d = 3;
    else if (abs >= 1e6) d = 0;
    else if (abs >= 1e3) d = 1;
    else if (abs >= 1) d = 3;
    else if (abs >= 1e-3) d = 4;
    else d = 6;
  }
  return value.toLocaleString(undefined, {
    minimumFractionDigits: d,
    maximumFractionDigits: d,
  });
}

export default I18nProvider;
