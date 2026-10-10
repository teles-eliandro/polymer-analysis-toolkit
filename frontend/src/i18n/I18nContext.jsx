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
    'common.ref': 'Ref.',
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
    'thermal.f.dtg.referenceNote': 'The DTG is the first derivative of the mass loss curve; its maximum is the temperature of greatest decomposition rate.',
    'thermal.f.td.name': 'Decomposition temperature Td',
    'thermal.f.td.x': 'the mass loss defining the onset, 5 % and 10 % here',
    'thermal.f.td.m': 'smoothed mass percent remaining',
    'thermal.f.td.note': "Td(5 %) is the conventional onset. Values below about 150 °C are usually residual water or solvent, not chain scission, so a Td(5 %) near 100 °C does not mean the polymer is unstable.",
    'thermal.f.td.expressionNote': '(linear interpolation)',
    'thermal.f.td.referenceNote': 'Defines the onset temperature by the mass-loss criterion and the extrapolated tangent.',
    'thermal.f.res.name': 'Residue',
    'thermal.f.res.note': 'Read at the last temperature of the run, so it is instrument-range dependent. A run that ends at 600 °C and one that ends at 800 °C can report different residues for the same material.',
    'thermal.f.res.referenceNote': 'The residue includes any inorganic filler, ash or char, so it is an upper bound on the filler content, not a measurement of it.',
    'thermal.f.smooth.name': 'Smoothing',
    'thermal.f.smooth.w':
      'window length in points; a larger w means more smoothing, and an even value is reduced by one so the window stays centred',
    'thermal.f.smooth.note': 'Differentiation amplifies noise, so the mass curve is smoothed first. The default window of 11 points is a compromise: wider is steadier but merges closely spaced steps.',
    'thermal.f.smooth.expressionNote': '(over a window of w points, edge-padded)',
    'thermal.f.smooth.referenceNote': 'A moving-average filter is the usual pre-treatment for a DTG curve (ISO 11358-1:2022, which permits smoothing provided its parameters are reported). It is a low-pass filter, so it suppresses sharp features along with the noise: widening w flattens a narrow decomposition step, and the smoothed curve must never be the one the residue is read from.',
    'thermal.f.uniform.name': 'Uneven temperature axis',
    'thermal.f.uniform.note': "Instrument exports are neither sorted nor evenly spaced: the same set-point is logged many times and the spacing varies within a run. Taking the derivative on that axis makes np.gradient divide by a zero-width interval and return NaN, and the peak search then reports the end of the scan. The trace is therefore sorted, samples sharing a temperature are averaged, and the derivative is taken on a uniform grid.",
    'thermal.f.uniform.expressionNote': '(DTG computed on a uniform 1 °C grid after interpolation)',
    'thermal.f.uniform.referenceNote': 'ISO 11358-1:2022 requires the rate of mass loss to be reported against temperature on a defined basis. A finite difference taken on the raw, unevenly spaced axis is dominated by the shortest intervals — one noisy pair a hundredth of a degree apart yields a gradient of tens of percent per degree — so the trace is resampled onto a uniform grid first. The choice of grid step is then reported, because it sets the resolution of every DTG peak that follows.',
    'thermal.f.dscpeak.name': 'Heat of fusion',
    'thermal.f.dscpeak.Hm': 'specific enthalpy of the melting transition (J/g)',
    'thermal.f.dscpeak.q': 'heat flow per unit mass (W/g), endothermic up',
    'thermal.f.dscpeak.beta': 'heating rate (K/s); dividing by it converts the integral over time into an enthalpy',
    'thermal.f.dscpeak.note': 'The result depends strongly on the baseline. This tool fits the baseline on the flanks outside the peak, because a straight line joining the two ends of the scan follows the change in heat capacity and inflates the enthalpy.',
    'thermal.f.dscpeak.referenceNote': 'The peak area is bounded by a baseline drawn between the flanks of the transition.',
    'thermal.f.xc.name': 'Degree of crystallinity',
    'thermal.f.xc.Hm': 'measured enthalpy of fusion (J/g)',
    'thermal.f.xc.Hm0': 'enthalpy of fusion of the fully crystalline polymer, supplied by you (e.g. 139.5 J/g for PCL, 93 J/g for PLLA)',
    'thermal.f.xc.note': 'Xc is only meaningful if ΔHm° matches your polymer and your crystal form. It is a mass fraction, ignores rigid amorphous material, and cannot exceed 100 %: a value above it means the baseline is wrong, not that the sample is exceptional.',
    'thermal.f.xc.referenceNote': 'Xc from DSC is a mass fraction, and is only as good as ΔHm°.',
    'thermal.shortTraceWarning':
      'A short trace gives an unreliable DTG; export the full run if you can.',
    'thermal.temperature': 'Temperature (°C)',
    'thermal.massPct': 'Mass remaining (%)',
    'thermal.heatFlow': 'Heat flow (W/g)',
    'thermal.points': 'points read from the file',
    'thermal.xAxis': 'X axis',
    'thermal.yAxis': 'Y axis',
    'thermal.sample': 'Sample',
    'thermal.mass': 'Sample mass',
    'thermal.heatingRate': 'Heating rate (K/min)',
    'thermal.heatingRateHint':
      'Required for enthalpies: the signal is integrated over temperature, so the scan rate is needed to get J/g.',
    'thermal.refEnthalpy': 'Reference melting enthalpy (J/g)',
    'thermal.refEnthalpyPick': 'Choose a polymer…',
    'thermal.refEnthalpyAmorphous': 'amorphous, not applicable',
    'thermal.refEnthalpySource': 'Source',
    'thermal.refEnthalpyAlternatives': 'Other values in the literature',
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
    'comparison.title': 'Compared against published values',
    'comparison.intro':
      'Your measured values next to the ranges published for this polymer. The ranges are data from the cited sources, not an inference from this tool.',
    'comparison.within': 'within range',
    'comparison.outside': 'outside range',
    'comparison.not_comparable': 'not comparable',
    'comparison.publishedRange': 'published',
    'comparison.notReported': 'not reported',
    'comparison.source': 'Source',
    'comparison.polymer': 'Polymer',
    'comparison.reason.polymer_unidentified':
      'The polymer was not identified, so there is no published range to compare against. Enter the polymer name to enable the comparison.',
    'comparison.reason.value_not_reported':
      'This trace did not yield a value for the property, so there is nothing to compare.',
    'comparison.reason.value_unstable':
      'This value is an inference that did not survive the stability check: it moves with the sampling of the trace. Comparing it would present an unstable value as a measurement. Repeat the run before comparing.',
    'comparison.reason.no_range_for_property':
      'The reference repertoire holds no published range for this property of this polymer. The absence is deliberate: the polymer may not exhibit this transition at all.',
    'comparison.reason.unit_mismatch':
      'The measured value and the published range are in different units, and no conversion is applied silently.',
    'thermal.sampleName': 'Sample name',
    'thermal.sampleNameHint':
      'Used to identify the polymer and compare against published values. Matching is tolerant of instrument naming (PLA1-AR, Nylon66). Left empty, no comparison is made.',
    'thermal.hint.tga':
      'One row per point: temperature mass_percent. Comma, tab or space separated.',
    'thermal.hint.dsc':
      'One row per point: temperature heat_flow_w_per_g. Endothermic up.',
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
    'structure.f.scherrer.referenceNote': 'Instrumental broadening is subtracted in quadrature before β is used.',
    'structure.f.fwhm.name': 'Peak width',
    'structure.f.fwhm.note': 'Measured at half of the peak height above the local baseline. Peaks too close to a neighbour, or too weak to separate from noise, are reported as unmeasurable rather than given an invented width.',
    'structure.f.fwhm.expressionNote': '(half-width at half maximum, in radians)',
    'structure.f.fwhm.referenceNote': 'The FWHM is the β that the Scherrer equation expects, and it must be corrected for instrumental broadening (β² = β_obs² − β_inst² for a Gaussian profile) before use. Without that correction the crystallite size is underestimated, and on a well-crystallised sample the instrumental contribution can be most of the observed width.',
    'structure.f.xc.name': 'Crystallinity index (XRD)',
    'structure.f.xc.note': 'The area above a straight chord between the pattern endpoints, over the total area. This is an index, not a mass fraction: it depends on the angular range, the slit widths and the baseline. It cannot be compared with a DSC crystallinity, and it is reported as unavailable when the chord does not cut the pattern at all, because then every point counts as crystalline.',
    'structure.f.xc.expressionNote': '(A_c: crystalline area; A_t: total area)',
    'structure.f.xc.referenceNote': 'Relative index only; it is not a mass fraction and is comparable only between patterns measured identically.',
    'mech.f.young.name': "Young's modulus",
    'mech.f.young.E': 'tensile modulus (MPa)',
    'mech.f.young.sigma': 'engineering stress (MPa), force over the original cross-section',
    'mech.f.young.epsilon': 'engineering strain (%)',
    'mech.f.young.note': 'The modulus is only comparable between samples fitted over the same strain range. A modulus fitted over 0-5 % is systematically lower than one fitted over 0-0.5 %, because the curve bends as it yields. The range used is reported with the result.',
    'mech.f.young.expressionNote': '(slope of the initial linear region)',
    'mech.f.young.referenceNote': 'Both require the modulus from the initial linear region, and neither permits a modulus quoted without the strain range it was fitted over.',
    'mech.f.fit.name': 'Linear fit',
    'mech.f.fit.note': 'Least squares over the strain window, either detected by the largest local slope or supplied by you. A window that starts after the toe region is corrected for must be chosen by eye; the automatic detection can land on the yield shoulder in a ductile sample.',
    'mech.f.fit.expressionNote': '(least squares)',
    'mech.f.fit.referenceNote': 'The standard fits the slope over a defined strain window (typically 0.05 % to 0.25 %) rather than the whole curve, because the toe region at the start of the test is seating compliance, not material stiffness.',
    'mech.f.sigma.name': 'Stress and strain',
    'mech.f.sigma.F': 'applied force (N)',
    'mech.f.sigma.A0': 'cross-sectional area before the test (mm2)',
    'mech.f.sigma.L0': 'gauge length before the test (mm)',
    'mech.f.sigma.note': 'These are engineering values throughout: the original area is used and never updated during the test. True stress is higher in a necking sample, so the tensile strength reported here is conservative.',
    'mech.f.sigma.referenceNote': 'The original cross-section is used throughout; engineering stress, not true stress.',
    'mech.f.toughness.name': 'Toughness',
    'mech.f.toughness.note': 'The trapezoidal area under the curve as supplied. If the test was stopped before break, the value is a lower bound and the tool reports it without knowing the difference.',
    'mech.f.toughness.expressionNote': '(area under the stress-strain curve)',
    'mech.f.toughness.referenceNote': 'The area is integrated over the strain range supplied, so a truncated curve underestimates toughness.',
    'rheo.f.moduli.name': 'Storage and loss moduli',
    'rheo.f.moduli.Gp': 'storage modulus (Pa), the elastic response',
    'rheo.f.moduli.Gpp': 'loss modulus (Pa), the viscous response',
    'rheo.f.moduli.delta': 'phase lag between stress and strain (rad)',
    'rheo.f.moduli.note': 'Valid only inside the linear viscoelastic region, where the moduli do not depend on strain amplitude. A sweep run outside it reports a lower G-prime that looks like a material change and is not.',
    'rheo.f.tan.name': 'Loss tangent',
    'rheo.f.tan.note': 'Above 1 the sample dissipates more than it stores. In a melt this is normal; in a crosslinked network it indicates the test is above the gel point or that the network is not fully formed.',
    'rheo.f.gel.name': 'Gel point',
    'rheo.f.gel.note': 'Reported only when the two moduli stay within the tolerance of each other while G-prime exceeds G-double-prime. The tolerance matters: a fixed crossing test fires on noise in a noisy sweep, so the two moduli must agree over several consecutive points.',
    'rheo.f.gel.expressionNote': '(gel point: the ω where the two moduli agree within tolerance, with G\' > G\'\')',
    'rheo.f.gel.referenceNote': 'The rigorous criterion is a power law in both moduli; crossing of the two is a practical approximation.',
    'rheo.f.cross.name': 'Cross-over frequency',
    'rheo.f.cross.note': 'The frequency where the melt stops behaving elastically. It shifts with temperature, so a cross-over quoted without its temperature is not reproducible.',
    'rheo.f.cross.expressionNote': '(cross-over)',
    'rheo.f.cross.referenceNote': 'The cross-over of the moduli is a practical marker of the terminal-to-plateau transition for a linear polymer; it shifts with frequency, so the value is only comparable between measurements made at the same angular frequency.',
    'mol.f.mn.name': 'Number and weight averages',
    'mol.f.mn.Ni': 'number of chains of molar mass Mi',
    'mol.f.mn.Mi': 'molar mass of the i-th species (g/mol)',
    'mol.f.mn.note': 'Mn is the simple mean over chains, Mw weights each chain by its mass. Mw is always greater than or equal to Mn; if a result violates that, the data or the arithmetic is wrong, not the polymer.',
    'mol.f.pdi.name': 'Dispersity',
    'mol.f.pdi.note': 'A dispersity of 1.0 means every chain has the same length, which no real polymerisation achieves: the theoretical minimum for a living anionic polymerisation is about 1.02. Values near 2 indicate a step-growth or chain-transfer-dominated mechanism.',
    'mol.f.pdi.expressionNote': '(dispersity, formerly polydispersity index)',
    'mol.f.pdi.referenceNote': 'IUPAC recommends the term dispersity and the symbol D. A value below 1 is not a narrow distribution but an error in the data or the calculation.',
    'mol.f.mz.name': 'z-average',
    'mol.f.mz.note': 'The z-average is used by light scattering and by viscometry, so comparing it with Mw from the same trace checks the shape of the distribution rather than just its position.',
    'mol.f.mz.referenceNote': 'The z-average is weighted towards the heaviest chains, so it responds to a high-mass tail that Mw barely registers.',
    'mol.f.mh.name': 'Mark-Houwink-Sakurada',
    'mol.f.mh.Mv': 'viscosity-average molar mass (g/mol)',
    'mol.f.mh.K': 'polymer-, solvent- and temperature-specific constant',
    'mol.f.mh.a': 'exponent, 0.5 in a theta solvent and up to about 0.8 in a good solvent',
    'mol.f.mh.note': 'Mv sits between Mn and Mw and is closest to Mw when a is near 1. Using K and a from a different solvent or temperature gives a systematically wrong molar mass that looks perfectly reasonable.',
    'mol.f.mh.referenceNote': 'Mark-Houwink-Sakurada relation; K and a are tabulated per polymer-solvent-temperature combination in the Polymer Handbook. They are not universal constants.',
    'mol.f.gpc.name': 'SEC calibration',
    'mol.f.gpc.note': 'The calibration curve converts elution volume to molar mass using standards of a different polymer unless the standards match the sample. This is why a result from a conventional SEC is a relative molar mass, and why the calibration standard must be reported.',
    'mol.f.gpc.expressionNote': '(calibrated against narrow standards)',
    'mol.f.gpc.referenceNote': 'Conventional GPC calibration assumes the sample and the standards have the same hydrodynamic volume at a given elution volume. Reporting the result as absolute molar mass without a light-scattering or viscometry detector overstates what the measurement supports.',
    'mol.f.log.name': 'Log-normal distribution',
    'mol.f.log.note': 'A model, not a measurement. It is shown to compare the shape of a measured distribution against an idealised one, and it assumes the trace is free of column broadening, which broadens every real trace.',
    'mol.f.log.referenceNote': 'Schulz-Zimm and log-normal distributions are the usual models for a SEC trace; the log-normal is used here because its Mw/Mn follows directly from sigma.',
    'error.needData': 'Provide a file or enter the values directly.',
    'error.needFile': 'Choose a file first.',

    'file.choose': 'Choose a data file',
    'file.chooseOrDrop': 'Choose a file or drop it here',
    'file.accepted': 'Accepted: {list}',
    'file.clear': 'Remove file',
    'file.unsupported':
      'The extension {ext} is not a format this reader accepts. Accepted here: {list}.',
    'file.tooLarge':
      'The file is larger than {mb} MB and will not be sent. Export a coarser trace.',
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
    'mech.f.fit.E': 'Módulo de elasticidade, a inclinação da reta ajustada, em MPa.',
    'mech.f.fit.eps': 'Deformação do ponto i dentro da janela ajustada.',
    'mech.f.fit.sig': 'Tensão do ponto i dentro da janela ajustada, em MPa.',
    'mech.f.toughness.U': 'Energia na ruptura por unidade de volume, a área sob a curva, em MJ/m3.',
    'mech.f.toughness.sig': 'Tensão de engenharia, em MPa.',
    'mech.f.toughness.eps': 'Deformação de engenharia, adimensional.',
    'mol.f.pdi.D': 'Dispersidade, Mw dividido por Mn. 1,0 significa que todas as cadeias tem o mesmo tamanho.',
    'mol.f.pdi.Mw': 'Massa molar média em massa.',
    'mol.f.pdi.Mn': 'Massa molar média em número.',
    'mol.f.mz.Ni': 'Número de cadeias de massa molar Mi.',
    'mol.f.mz.Mi': 'Massa molar da especie i.',
    'mol.f.gpc.M': 'Massa molar lida na curva de calibração no volume de eluição dado.',
    'mol.f.log.w': 'Fração em massa na fatia da distribuição centrada em M.',
    'mol.f.log.sigma': 'Largura da distribuição log-normal em ln M.',
    'mol.f.log.mu': 'Média de ln M da distribuição.',
    'rheo.f.tan.Gpp': 'Módulo de perda, a resposta viscosa (dissipadora de energia).',
    'rheo.f.tan.Gp': 'Módulo de armazenamento, a resposta elástica (acumuladora de energia).',
    'rheo.f.gel.Gp': 'Módulo de armazenamento no ponto de gel.',
    'rheo.f.gel.Gpp': 'Módulo de perda no ponto de gel.',
    'rheo.f.cross.Gp': 'Módulo de armazenamento, em Pa.',
    'rheo.f.cross.Gpp': 'Módulo de perda, em Pa.',
    "rheo.f.cross.tan": "Tangente de perda, G'' / G'. Vale exatamente 1 no cruzamento.",
    'structure.f.fwhm.beta': 'Largura a meia altura da reflexao, em radianos.',
    'structure.f.fwhm.tt': 'Angulo de difracao, o dobro do angulo de Bragg, em graus.',
    'structure.f.xc.A': 'Área das reflexões cristalinas acima do fundo amorfo.',
    'structure.f.xc.At': 'Área total do padrão na mesma faixa angular.',
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
    'common.ref': 'Ref.',
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
    'thermal.f.dtg.referenceNote': 'A DTG é a primeira derivada da curva de perda de massa; o seu máximo é a temperatura de maior velocidade de decomposição.',
    'thermal.f.td.name': 'Temperatura de decomposição Td',
    'thermal.f.td.x': 'a perda de massa que define o início, aqui 5 % e 10 %',
    'thermal.f.td.m': 'porcentagem de massa restante, suavizada',
    'thermal.f.td.note': 'A Td(5 %) é o início convencional. Valores abaixo de ~150 °C costumam ser água ou solvente residual, não quebra de cadeia, então uma Td(5 %) perto de 100 °C não significa que o polímero seja instável.',
    'thermal.f.td.expressionNote': '(interpolação linear)',
    'thermal.f.td.referenceNote': 'Define a temperatura de onset pelo critério de perda de massa e pela tangente extrapolada.',
    'thermal.f.res.name': 'Resíduo',
    'thermal.f.res.note': 'Lido na última temperatura do ensaio, e portanto depende da faixa do instrumento. Um ensaio que termina a 600 °C e outro a 800 °C podem dar resíduos diferentes para o mesmo material.',
    'thermal.f.res.referenceNote': 'O resíduo inclui qualquer carga inorgânica, cinza ou resíduo carbonoso, então é um limite superior do teor de carga, não uma medição dele.',
    'thermal.f.smooth.name': 'Suavização',
    'thermal.f.smooth.w': 'comprimento da janela em pontos; um valor par é reduzido em um para a janela ficar centrada',
    'thermal.f.smooth.note': 'A derivada amplifica o ruído, então a curva de massa é suavizada antes. A janela padrão de 11 pontos é um compromisso: mais larga é mais estável, mas funde passos próximos.',
    'thermal.f.smooth.expressionNote': '(sobre uma janela de w pontos, com preenchimento nas bordas)',
    'thermal.f.smooth.referenceNote': 'Um filtro de média móvel é o pré-tratamento usual para uma curva de DTG (ISO 11358-1:2022, que permite suavizar desde que os parâmetros sejam reportados). É um filtro passa-baixa, então suprime traços agudos junto com o ruído: aumentar w achata um degrau estreito de decomposição, e a curva suavizada nunca deve ser aquela de onde se lê o resíduo.',
    'thermal.f.uniform.name': 'Eixo de temperatura irregular',
    'thermal.f.uniform.note': 'Exportações de instrumento não estão ordenadas nem igualmente espaçadas: o mesmo set-point é registrado muitas vezes e o espaçamento varia dentro do ensaio. Derivar nesse eixo faz o np.gradient dividir por um intervalo de largura zero e devolver NaN, e a busca de pico passa a reportar o fim da varredura. Por isso o traço é ordenado, as amostras que partilham temperatura são promediadas, e a derivada é tomada numa grelha uniforme.',
    'thermal.f.uniform.expressionNote': '(DTG calculada numa grade uniforme de 1 °C após interpolação)',
    'thermal.f.uniform.referenceNote': 'A ISO 11358-1:2022 exige que a velocidade de perda de massa seja reportada em função da temperatura numa base definida. Uma diferença finita tomada no eixo bruto, de espaçamento irregular, é dominada pelos intervalos mais curtos — um par ruidoso separado por um centésimo de grau produz um gradiente de dezenas de por cento por grau — então o traço é reamostrado numa grade uniforme antes. A escolha do passo da grade é então reportada, porque define a resolução de todos os picos de DTG que vêm depois.',
    'thermal.f.dscpeak.name': 'Entalpia de fusão',
    'thermal.f.dscpeak.Hm': 'entalpia específica da transição de fusão (J/g)',
    'thermal.f.dscpeak.q': 'fluxo de calor por unidade de massa (W/g), endotérmico para cima',
    'thermal.f.dscpeak.beta': 'taxa de aquecimento (K/s); dividir por ela converte a integral no tempo em entalpia',
    'thermal.f.dscpeak.note': 'O resultado depende muito da linha de base. Esta ferramenta ajusta a linha de base nos flancos, fora do pico, porque uma reta ligando as duas pontas da varredura acompanha a mudança de capacidade térmica e infla a entalpia.',
    'thermal.f.dscpeak.referenceNote': 'A área do pico é limitada por uma linha de base traçada entre os flancos da transição.',
    'thermal.f.xc.name': 'Grau de cristalinidade',
    'thermal.f.xc.Hm': 'entalpia de fusão medida (J/g)',
    'thermal.f.xc.Hm0': 'entalpia de fusão do polímero totalmente cristalino, fornecida por você (ex.: 139,5 J/g para PCL, 93 J/g para PLLA)',
    'thermal.f.xc.note': 'Xc só faz sentido se ΔHm° corresponder ao seu polímero e à sua forma cristalina. É uma fração mássica, ignora material amorfo rígido, e não pode passar de 100 %: um valor acima disso significa que a linha de base está errada, não que a amostra seja excepcional.',
    'thermal.f.xc.referenceNote': 'A Xc por DSC é uma fração mássica, e só é tão boa quanto o ΔHm°.',
    'thermal.shortTraceWarning':
      'Um traço curto dá um DTG pouco confiável; exporte o ensaio completo se puder.',
    'thermal.temperature': 'Temperatura (°C)',
    'thermal.massPct': 'Massa restante (%)',
    'thermal.heatFlow': 'Fluxo de calor (W/g)',
    'thermal.points': 'pontos lidos do arquivo',
    'thermal.xAxis': 'Eixo X',
    'thermal.yAxis': 'Eixo Y',
    'thermal.sample': 'Amostra',
    'thermal.mass': 'Massa da amostra',
    'thermal.heatingRate': 'Taxa de aquecimento (K/min)',
    'thermal.heatingRateHint':
      'Necessária para entalpias: o sinal é integrado em temperatura, então a taxa é necessária para obter J/g.',
    'thermal.refEnthalpy': 'Entalpia de fusão de referência (J/g)',
    'thermal.refEnthalpyPick': 'Escolha um polímero…',
    'thermal.refEnthalpyAmorphous': 'amorfo, não se aplica',
    'thermal.refEnthalpySource': 'Fonte',
    'thermal.refEnthalpyAlternatives': 'Outros valores na literatura',
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
    'comparison.title': 'Comparado com valores publicados',
    'comparison.intro':
      'Seus valores medidos ao lado das faixas publicadas para este polímero. As faixas são dados das fontes citadas, não uma inferência desta ferramenta.',
    'comparison.within': 'dentro da faixa',
    'comparison.outside': 'fora da faixa',
    'comparison.not_comparable': 'não comparável',
    'comparison.publishedRange': 'publicado',
    'comparison.notReported': 'não reportado',
    'comparison.source': 'Fonte',
    'comparison.polymer': 'Polímero',
    'comparison.reason.polymer_unidentified':
      'O polímero não foi identificado, então não há faixa publicada para comparar. Informe o nome do polímero para habilitar a comparação.',
    'comparison.reason.value_not_reported':
      'Esta curva não forneceu um valor para a propriedade, então não há o que comparar.',
    'comparison.reason.value_unstable':
      'Este valor é uma inferência que não passou na verificação de estabilidade: ele varia com a amostragem da curva. Compará-lo apresentaria um valor instável como se fosse uma medição. Repita a análise antes de comparar.',
    'comparison.reason.no_range_for_property':
      'O repertório de referência não contém faixa publicada para esta propriedade deste polímero. A ausência é intencional: o polímero pode não apresentar essa transição.',
    'comparison.reason.unit_mismatch':
      'O valor medido e a faixa publicada estão em unidades diferentes, e nenhuma conversão é aplicada silenciosamente.',
    'thermal.sampleName': 'Nome da amostra',
    'thermal.sampleNameHint':
      'Usado para identificar o polímero e comparar com valores publicados. A correspondência tolera a nomenclatura do instrumento (PLA1-AR, Nylon66). Se vazio, nenhuma comparação é feita.',
    'thermal.hint.tga':
      'Uma linha por ponto: temperatura massa_percentual. Separado por vírgula, tabulação ou espaço.',
    'thermal.hint.dsc':
      'Uma linha por ponto: temperatura fluxo_de_calor_w_por_g. Endotérmico para cima.',
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
    'structure.f.scherrer.referenceNote': 'O alargamento instrumental é subtraído em quadratura antes de usar β.',
    'structure.f.fwhm.name': 'Largura do pico',
    'structure.f.fwhm.note': 'Medida na metade da altura do pico acima da linha de base local. Picos muito próximos de um vizinho, ou fracos demais para se separar do ruído, são reportados como não mensuráveis em vez de receberem uma largura inventada.',
    'structure.f.fwhm.expressionNote': '(largura a meia altura, em radianos)',
    'structure.f.fwhm.referenceNote': 'A FWHM é o β que a equação de Scherrer espera, e precisa ser corrigida do alargamento instrumental (β² = β_obs² − β_inst² para um perfil gaussiano) antes do uso. Sem essa correção o tamanho do cristalito é subestimado, e numa amostra bem cristalizada a contribuição instrumental pode ser a maior parte da largura observada.',
    'structure.f.xc.name': 'Índice de cristalinidade (DRX)',
    'structure.f.xc.note': 'A área acima de uma corda reta entre as extremidades do padrão, sobre a área total. É um índice, não uma fração mássica: depende da faixa angular, da fenda e da linha de base. Não é comparável com a cristalinidade do DSC, e é reportado como indisponível quando a corda não corta o padrão, porque aí todos os pontos contariam como cristalinos.',
    'structure.f.xc.expressionNote': '(A_c: área cristalina; A_t: área total)',
    'structure.f.xc.referenceNote': 'Apenas um índice relativo; não é fração mássica e só é comparável entre padrões medidos de forma idêntica.',
    'mech.f.young.name': 'Módulo de Young',
    'mech.f.young.E': 'módulo de tração (MPa)',
    'mech.f.young.sigma': 'tensão de engenharia (MPa), força sobre a seção original',
    'mech.f.young.epsilon': 'deformação de engenharia (%)',
    'mech.f.young.note': 'O módulo só é comparável entre amostras ajustadas na mesma faixa de deformação. Um módulo ajustado de 0 a 5 % é sistematicamente menor que um ajustado de 0 a 0,5 %, porque a curva encurva ao escoar. A faixa usada é reportada junto com o resultado.',
    'mech.f.young.expressionNote': '(inclinação da região linear inicial)',
    'mech.f.young.referenceNote': 'Ambos exigem o módulo da região linear inicial, e nenhum dos dois permite citar um módulo sem o intervalo de deformação em que foi ajustado.',
    'mech.f.fit.name': 'Ajuste linear',
    'mech.f.fit.note': 'Mínimos quadrados na janela de deformação, detectada pela maior inclinação local ou informada por você. Uma janela que comece depois da região de acomodação deve ser escolhida a olho; a detecção automática pode cair no ombro de escoamento numa amostra dúctil.',
    'mech.f.fit.expressionNote': '(mínimos quadrados)',
    'mech.f.fit.referenceNote': 'A norma ajusta a inclinação sobre uma janela de deformação definida (tipicamente 0,05 % a 0,25 %) e não sobre a curva inteira, porque a região de acomodação no início do ensaio é folga de fixação, não rigidez do material.',
    'mech.f.sigma.name': 'Tensão e deformação',
    'mech.f.sigma.F': 'força aplicada (N)',
    'mech.f.sigma.A0': 'área da seção antes do ensaio (mm2)',
    'mech.f.sigma.L0': 'comprimento útil antes do ensaio (mm)',
    'mech.f.sigma.note': 'São valores de engenharia do início ao fim: a área original é usada e nunca atualizada durante o ensaio. A tensão real é maior numa amostra que estrica, então a resistência à tração reportada aqui é conservadora.',
    'mech.f.sigma.referenceNote': 'A seção original é usada do início ao fim; tensão de engenharia, não tensão real.',
    'mech.f.toughness.name': 'Tenacidade',
    'mech.f.toughness.note': 'Área trapezoidal sob a curva fornecida. Se o ensaio foi interrompido antes da ruptura, o valor é um limite inferior e a ferramenta o reporta sem saber a diferença.',
    'mech.f.toughness.expressionNote': '(área sob a curva tensão-deformação)',
    'mech.f.toughness.referenceNote': 'A área é integrada sobre o intervalo de deformação fornecido, então uma curva truncada subestima a tenacidade.',
    'rheo.f.moduli.name': 'Módulos de armazenamento e de perda',
    'rheo.f.moduli.Gp': 'módulo de armazenamento (Pa), a resposta elástica',
    'rheo.f.moduli.Gpp': 'módulo de perda (Pa), a resposta viscosa',
    'rheo.f.moduli.delta': 'defasagem entre tensão e deformação (rad)',
    'rheo.f.moduli.note': 'Válido apenas dentro da região viscoelástica linear, onde os módulos não dependem da amplitude de deformação. Uma varredura fora dela reporta um módulo de armazenamento menor que parece mudança de material e não é.',
    'rheo.f.tan.name': 'Tangente de perda',
    'rheo.f.tan.note': 'Acima de 1 a amostra dissipa mais do que armazena. Num fundido isso é normal; numa rede reticulada indica que o ensaio está acima do ponto de gel ou que a rede não está totalmente formada.',
    'rheo.f.gel.name': 'Ponto de gel',
    'rheo.f.gel.note': 'Reportado apenas quando os dois módulos permanecem dentro da tolerância um do outro enquanto o módulo de armazenamento excede o de perda. A tolerância importa: um teste de cruzamento simples dispara com ruído numa varredura ruidosa, então os dois módulos precisam concordar em vários pontos consecutivos.',
    'rheo.f.gel.expressionNote': '(ponto de gel: o ω em que os dois módulos concordam dentro da tolerância, com G\' > G\'\')',
    'rheo.f.gel.referenceNote': 'O critério rigoroso é uma lei de potência nos dois módulos; o cruzamento dos dois é uma aproximação prática.',
    'rheo.f.cross.name': 'Frequência de cruzamento',
    'rheo.f.cross.note': 'A frequência onde o fundido deixa de se comportar elasticamente. Ela desloca com a temperatura, então um cruzamento citado sem a temperatura não é reproduzível.',
    'rheo.f.cross.expressionNote': '(cruzamento)',
    'rheo.f.cross.referenceNote': 'O cruzamento dos módulos é um marcador prático da transição terminal-platô num polímero linear; ele desloca com a frequência, então o valor só é comparável entre medições feitas na mesma frequência angular.',
    'mol.f.mn.name': 'Médias numérica e ponderal',
    'mol.f.mn.Ni': 'número de cadeias de massa molar Mi',
    'mol.f.mn.Mi': 'massa molar da especie i (g/mol)',
    'mol.f.mn.note': 'Mn é a média simples entre cadeias, Mw pondera cada cadeia pela sua massa. Mw é sempre maior ou igual a Mn; se um resultado violar isso, o erro está nos dados ou na aritmética, não no polímero.',
    'mol.f.pdi.name': 'Dispersidade',
    'mol.f.pdi.note': 'Uma dispersidade de 1,0 significa que todas as cadeias têm o mesmo comprimento, o que nenhuma polimerização real atinge: o mínimo teórico para uma polimerização aniônica viva é cerca de 1,02. Valores próximos de 2 indicam mecanismo de etapas ou dominado por transferência de cadeia.',
    'mol.f.pdi.expressionNote': '(dispersidade, antigamente índice de polidispersão)',
    'mol.f.pdi.referenceNote': 'A IUPAC recomenda o termo dispersidade e o símbolo D. Um valor abaixo de 1 não é uma distribuição estreita, mas um erro nos dados ou no cálculo.',
    'mol.f.mz.name': 'Média z',
    'mol.f.mz.note': 'A média z é a usada em espalhamento de luz e em viscosimetria, então compará-la com o Mw do mesmo traço verifica a forma da distribuição, não apenas a sua posição.',
    'mol.f.mz.referenceNote': 'A média z é ponderada pelas cadeias mais pesadas, então responde a uma cauda de massa alta que o Mw quase não registra.',
    'mol.f.mh.name': 'Mark-Houwink-Sakurada',
    'mol.f.mh.Mv': 'massa molar média viscosimétrica (g/mol)',
    'mol.f.mh.K': 'constante específica do polímero, solvente e temperatura',
    'mol.f.mh.a': 'expoente, 0,5 num solvente teta e ate cerca de 0,8 num bom solvente',
    'mol.f.mh.note': 'Mv fica entre Mn e Mw e se aproxima de Mw quando a está perto de 1. Usar K e a de outro solvente ou temperatura dá uma massa molar sistematicamente errada que parece perfeitamente razoável.',
    'mol.f.mh.referenceNote': 'Relação de Mark-Houwink-Sakurada; K e a são tabelados por combinação polímero-solvente-temperatura no Polymer Handbook. Não são constantes universais.',
    'mol.f.gpc.name': 'Calibração em SEC',
    'mol.f.gpc.note': 'A curva de calibração converte volume de eluição em massa molar usando padrões de outro polímero, a menos que os padrões sejam do mesmo material da amostra. Por isso um resultado de SEC convencional é uma massa molar relativa, e por isso o padrão de calibração precisa ser reportado.',
    'mol.f.gpc.expressionNote': '(calibrada contra padrões estreitos)',
    'mol.f.gpc.referenceNote': 'A calibração convencional de GPC presume que a amostra e os padrões têm o mesmo volume hidrodinâmico num dado volume de eluição. Reportar o resultado como massa molar absoluta sem detector de espalhamento de luz ou viscosimetria superestima o que a medição sustenta.',
    'mol.f.log.name': 'Distribuição log-normal',
    'mol.f.log.note': 'Um modelo, não uma medida. É mostrada para comparar a forma de uma distribuição medida com uma idealizada, e presume que o traço não tem alargamento de coluna, que alarga todo traço real.',
    'mol.f.log.referenceNote': 'As distribuições de Schulz-Zimm e log-normal são os modelos usuais para um traço de SEC; a log-normal é usada aqui porque o seu Mw/Mn sai diretamente de sigma.',
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
    'mech.f.fit.E': 'Módulo de tracción, la pendiente de la recta ajustada, en MPa.',
    'mech.f.fit.eps': 'Deformación del punto i dentro de la ventana ajustada.',
    'mech.f.fit.sig': 'Tensión del punto i dentro de la ventana ajustada, en MPa.',
    'mech.f.toughness.U': 'Energía en la ruptura por unidad de volumen, el área bajo la curva, en MJ/m3.',
    'mech.f.toughness.sig': 'Tensión de ingeniería, en MPa.',
    'mech.f.toughness.eps': 'Deformación de ingeniería, adimensional.',
    'mol.f.pdi.D': 'Dispersidad, Mw dividido por Mn. 1,0 significa que todas las cadenas tienen la misma longitud.',
    'mol.f.pdi.Mw': 'Masa molar media en peso.',
    'mol.f.pdi.Mn': 'Masa molar media en número.',
    'mol.f.mz.Ni': 'Número de cadenas de masa molar Mi.',
    'mol.f.mz.Mi': 'Masa molar de la especie i.',
    'mol.f.gpc.M': 'Masa molar leída en la curva de calibración en el volumen de elución dado.',
    'mol.f.log.w': 'Fracción en peso en la porción de la distribución centrada en M.',
    'mol.f.log.sigma': 'Ancho de la distribución log-normal en ln M.',
    'mol.f.log.mu': 'Media de ln M de la distribución.',
    'rheo.f.tan.Gpp': 'Módulo de pérdida, la respuesta viscosa (disipadora de energía).',
    'rheo.f.tan.Gp': 'Módulo de almacenamiento, la respuesta elástica (acumuladora de energía).',
    'rheo.f.gel.Gp': 'Módulo de almacenamiento en el punto de gel.',
    'rheo.f.gel.Gpp': 'Módulo de pérdida en el punto de gel.',
    'rheo.f.cross.Gp': 'Módulo de almacenamiento, en Pa.',
    'rheo.f.cross.Gpp': 'Módulo de pérdida, en Pa.',
    "rheo.f.cross.tan": "Tangente de pérdida, G'' / G'. Vale exactamente 1 en el cruce.",
    'structure.f.fwhm.beta': 'Anchura a mitad de altura de la reflexion, en radianes.',
    'structure.f.fwhm.tt': 'Angulo de difraccion, el doble del angulo de Bragg, en grados.',
    'structure.f.xc.A': 'Area de las reflexiones cristalinas sobre el fondo amorfo.',
    'structure.f.xc.At': 'Area total del patron en el mismo rango angular.',
    'thermal.f.res.mf': 'Masa al final del ensayo, como porcentaje de la masa inicial.',
    'thermal.f.uniform.dtg': 'Velocidad de pérdida de masa, en porcentaje por grado Celsius.',

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
    'common.ref': 'Ref.',
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
    'thermal.f.dtg.referenceNote': 'La DTG es la primera derivada de la curva de pérdida de masa; su máximo es la temperatura de mayor velocidad de descomposición.',
    'thermal.f.td.name': 'Temperatura de descomposición Td',
    'thermal.f.td.x': 'la pérdida de masa que define el inicio, aquí 5 % y 10 %',
    'thermal.f.td.m': 'porcentaje de masa restante, suavizado',
    'thermal.f.td.note': 'La Td(5 %) es el inicio convencional. Valores por debajo de ~150 °C suelen ser agua o disolvente residual, no ruptura de cadena, así que una Td(5 %) cerca de 100 °C no significa que el polímero sea inestable.',
    'thermal.f.td.expressionNote': '(interpolación lineal)',
    'thermal.f.td.referenceNote': 'Define la temperatura de onset por el criterio de pérdida de masa y la tangente extrapolada.',
    'thermal.f.res.name': 'Residuo',
    'thermal.f.res.note': 'Se lee en la última temperatura del ensayo, por lo que depende del rango del instrumento. Un ensayo que termina a 600 °C y otro a 800 °C pueden dar residuos distintos para el mismo material.',
    'thermal.f.res.referenceNote': 'El residuo incluye cualquier carga inorgánica, ceniza o residuo carbonoso, así que es un límite superior del contenido de carga, no una medición de este.',
    'thermal.f.smooth.name': 'Suavizado',
    'thermal.f.smooth.w': 'longitud de la ventana en puntos; un valor par se reduce en uno para que la ventana quede centrada',
    'thermal.f.smooth.note': 'La derivada amplifica el ruido, así que la curva de masa se suaviza antes. La ventana estándar de 11 puntos es un compromiso: más ancha es más estable, pero fusiona pasos próximos.',
    'thermal.f.smooth.expressionNote': '(sobre una ventana de w puntos, con relleno en los bordes)',
    'thermal.f.smooth.referenceNote': 'Un filtro de media móvil es el pretratamiento habitual para una curva de DTG (ISO 11358-1:2022, que permite suavizar siempre que se informen sus parámetros). Es un filtro paso bajo, así que suprime los rasgos agudos junto con el ruido: aumentar w aplana un escalón estrecho de descomposición, y la curva suavizada nunca debe ser aquella de la que se lee el residuo.',
    'thermal.f.uniform.name': 'Eje de temperatura irregular',
    'thermal.f.uniform.note': 'Las exportaciones del instrumento no están ordenadas ni igualmente espaciadas: el mismo punto de consigna se registra muchas veces y el espaciado varía dentro del ensayo. Derivar en ese eje hace que np.gradient divida por un intervalo de ancho cero y devuelva NaN, y la búsqueda del pico pasa a informar el final del barrido. Por eso la traza se ordena, las muestras que comparten temperatura se promedian y la derivada se toma en una rejilla uniforme.',
    'thermal.f.uniform.expressionNote': '(DTG calculada en una malla uniforme de 1 °C tras la interpolación)',
    'thermal.f.uniform.referenceNote': 'La ISO 11358-1:2022 exige que la velocidad de pérdida de masa se informe frente a la temperatura sobre una base definida. Una diferencia finita tomada sobre el eje bruto, de espaciado irregular, está dominada por los intervalos más cortos — un par ruidoso separado por una centésima de grado produce un gradiente de decenas de por ciento por grado — así que la traza se remuestrea primero en una malla uniforme. La elección del paso de malla se informa después, porque fija la resolución de todos los picos de DTG que siguen.',
    'thermal.f.dscpeak.name': 'Entalpía de fusión',
    'thermal.f.dscpeak.Hm': 'entalpía específica de la transición de fusión (J/g)',
    'thermal.f.dscpeak.q': 'flujo de calor por unidad de masa (W/g), endotérmico hacia arriba',
    'thermal.f.dscpeak.beta': 'velocidad de calentamiento (K/s); dividir por ella convierte la integral en el tiempo en entalpía',
    'thermal.f.dscpeak.note': 'El resultado depende mucho de la línea base. Esta herramienta ajusta la línea base en los flancos, fuera del pico, porque una recta que une los dos extremos del barrido sigue el cambio de capacidad calorífica e infla la entalpía.',
    'thermal.f.dscpeak.referenceNote': 'El área del pico está delimitada por una línea base trazada entre los flancos de la transición.',
    'thermal.f.xc.name': 'Grado de cristalinidad',
    'thermal.f.xc.Hm': 'entalpía de fusión medida (J/g)',
    'thermal.f.xc.Hm0': 'entalpía de fusión del polímero totalmente cristalino, proporcionada por usted (p. ej. 139,5 J/g para PCL, 93 J/g para PLLA)',
    'thermal.f.xc.note': 'Xc solo tiene sentido si ΔHm° corresponde a su polímero y a su forma cristalina. Es una fracción másica, ignora el material amorfo rígido y no puede superar 100 %: un valor por encima significa que la línea base está mal, no que la muestra sea excepcional.',
    'thermal.f.xc.referenceNote': 'La Xc por DSC es una fracción másica, y solo es tan buena como el ΔHm°.',
    'thermal.shortTraceWarning':
      'Una traza corta da un DTG poco fiable; exporte el ensayo completo si puede.',
    'thermal.temperature': 'Temperatura (°C)',
    'thermal.massPct': 'Masa restante (%)',
    'thermal.heatFlow': 'Flujo de calor (W/g)',
    'thermal.points': 'puntos leídos del archivo',
    'thermal.xAxis': 'Eje X',
    'thermal.yAxis': 'Eje Y',
    'thermal.sample': 'Muestra',
    'thermal.mass': 'Masa de la muestra',
    'thermal.heatingRate': 'Velocidad de calentamiento (K/min)',
    'thermal.heatingRateHint':
      'Necesaria para entalpías: la señal se integra en temperatura, así que la velocidad es necesaria para obtener J/g.',
    'thermal.refEnthalpy': 'Entalpía de fusión de referencia (J/g)',
    'thermal.refEnthalpyPick': 'Elija un polímero…',
    'thermal.refEnthalpyAmorphous': 'amorfo, no aplicable',
    'thermal.refEnthalpySource': 'Fuente',
    'thermal.refEnthalpyAlternatives': 'Otros valores en la literatura',
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
    'comparison.title': 'Comparado con valores publicados',
    'comparison.intro':
      'Sus valores medidos junto a los rangos publicados para este polímero. Los rangos son datos de las fuentes citadas, no una inferencia de esta herramienta.',
    'comparison.within': 'dentro del rango',
    'comparison.outside': 'fuera del rango',
    'comparison.not_comparable': 'no comparable',
    'comparison.publishedRange': 'publicado',
    'comparison.notReported': 'no reportado',
    'comparison.source': 'Fuente',
    'comparison.polymer': 'Polímero',
    'comparison.reason.polymer_unidentified':
      'El polímero no fue identificado, así que no hay rango publicado con el que comparar. Indique el nombre del polímero para habilitar la comparación.',
    'comparison.reason.value_not_reported':
      'Esta curva no produjo un valor para la propiedad, así que no hay nada que comparar.',
    'comparison.reason.value_unstable':
      'Este valor es una inferencia que no superó la verificación de estabilidad: varía con el muestreo de la curva. Compararlo presentaría un valor inestable como si fuera una medición. Repita el análisis antes de comparar.',
    'comparison.reason.no_range_for_property':
      'El repertorio de referencia no contiene un rango publicado para esta propiedad de este polímero. La ausencia es deliberada: puede que el polímero no presente esa transición.',
    'comparison.reason.unit_mismatch':
      'El valor medido y el rango publicado están en unidades distintas, y ninguna conversión se aplica de forma silenciosa.',
    'thermal.sampleName': 'Nombre de la muestra',
    'thermal.sampleNameHint':
      'Se usa para identificar el polímero y comparar con valores publicados. La coincidencia tolera la nomenclatura del instrumento (PLA1-AR, Nylon66). Si está vacío, no se hace ninguna comparación.',
    'thermal.hint.tga':
      'Una fila por punto: temperatura masa_porcentual. Separado por coma, tabulación o espacio.',
    'thermal.hint.dsc':
      'Una fila por punto: temperatura flujo_de_calor_w_por_g. Endotérmico hacia arriba.',
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
    'structure.f.scherrer.referenceNote': 'El ensanchamiento instrumental se resta en cuadratura antes de usar β.',
    'structure.f.fwhm.name': 'Anchura del pico',
    'structure.f.fwhm.note': 'Medida a la mitad de la altura del pico sobre la línea base local. Los picos demasiado próximos a un vecino, o demasiado débiles para separarse del ruido, se informan como no medibles en vez de recibir una anchura inventada.',
    'structure.f.fwhm.expressionNote': '(anchura a media altura, en radianes)',
    'structure.f.fwhm.referenceNote': 'La FWHM es el β que espera la ecuación de Scherrer, y debe corregirse del ensanchamiento instrumental (β² = β_obs² − β_inst² para un perfil gaussiano) antes de usarla. Sin esa corrección el tamaño del cristalito se subestima, y en una muestra bien cristalizada la contribución instrumental puede ser la mayor parte del ancho observado.',
    'structure.f.xc.name': 'Índice de cristalinidad (DRX)',
    'structure.f.xc.note': 'El área por encima de una cuerda recta entre los extremos del patrón, sobre el área total. Es un índice, no una fracción másica: depende del rango angular, de las rendijas y de la línea base. No es comparable con la cristalinidad de DSC, y se informa como no disponible cuando la cuerda no corta el patrón, porque entonces todos los puntos contarían como cristalinos.',
    'structure.f.xc.expressionNote': '(A_c: área cristalina; A_t: área total)',
    'structure.f.xc.referenceNote': 'Solo un índice relativo; no es una fracción másica y solo es comparable entre patrones medidos de forma idéntica.',
    'mech.f.young.name': 'Módulo de Young',
    'mech.f.young.E': 'módulo de tracción (MPa)',
    'mech.f.young.sigma': 'tensión de ingeniería (MPa), fuerza sobre la sección original',
    'mech.f.young.epsilon': 'deformación de ingeniería (%)',
    'mech.f.young.note': 'El módulo solo es comparable entre muestras ajustadas en el mismo rango de deformación. Un módulo ajustado de 0 a 5 % es sistemáticamente menor que uno ajustado de 0 a 0,5 %, porque la curva se dobla al ceder. El rango usado se informa junto con el resultado.',
    'mech.f.young.expressionNote': '(pendiente de la región lineal inicial)',
    'mech.f.young.referenceNote': 'Ambos exigen el módulo de la región lineal inicial, y ninguno de los dos permite citar un módulo sin el rango de deformación en el que se ajustó.',
    'mech.f.fit.name': 'Ajuste lineal',
    'mech.f.fit.note': 'Mínimos cuadrados en la ventana de deformación, detectada por la mayor pendiente local o proporcionada por usted. Una ventana que empiece después de la región de acomodo debe elegirse a ojo; la detección automática puede caer en el hombro de cedencia en una muestra dúctil.',
    'mech.f.fit.expressionNote': '(mínimos cuadrados)',
    'mech.f.fit.referenceNote': 'La norma ajusta la pendiente sobre una ventana de deformación definida (típicamente 0,05 % a 0,25 %) y no sobre la curva completa, porque la región de acomodo al inicio del ensayo es holgura de fijación, no rigidez del material.',
    'mech.f.sigma.name': 'Tensión y deformación',
    'mech.f.sigma.F': 'fuerza aplicada (N)',
    'mech.f.sigma.A0': 'area de la seccion antes del ensayo (mm2)',
    'mech.f.sigma.L0': 'longitud de referencia antes del ensayo (mm)',
    'mech.f.sigma.note': 'Son valores de ingeniería de principio a fin: se usa el área original y nunca se actualiza durante el ensayo. La tensión real es mayor en una muestra que estricciona, así que la resistencia a tracción informada aquí es conservadora.',
    'mech.f.sigma.referenceNote': 'Se usa la sección original de principio a fin; tensión de ingeniería, no tensión real.',
    'mech.f.toughness.name': 'Tenacidad',
    'mech.f.toughness.note': 'Area trapezoidal bajo la curva suministrada. Si el ensayo se detuvo antes de la rotura, el valor es un limite inferior y la herramienta lo informa sin conocer la diferencia.',
    'mech.f.toughness.expressionNote': '(área bajo la curva tensión-deformación)',
    'mech.f.toughness.referenceNote': 'El área se integra sobre el rango de deformación suministrado, así que una curva truncada subestima la tenacidad.',
    'rheo.f.moduli.name': 'Módulos de almacenamiento y de pérdida',
    'rheo.f.moduli.Gp': 'módulo de almacenamiento (Pa), la respuesta elástica',
    'rheo.f.moduli.Gpp': 'módulo de pérdida (Pa), la respuesta viscosa',
    'rheo.f.moduli.delta': 'desfase entre tensión y deformación (rad)',
    'rheo.f.moduli.note': 'Válido solo dentro de la región viscoelástica lineal, donde los módulos no dependen de la amplitud de deformación. Un barrido fuera de ella informa un módulo de almacenamiento menor que parece un cambio de material y no lo es.',
    'rheo.f.tan.name': 'Tangente de pérdida',
    'rheo.f.tan.note': 'Por encima de 1 la muestra disipa mas de lo que almacena. En un fundido esto es normal; en una red reticulada indica que el ensayo esta por encima del punto de gel o que la red no esta totalmente formada.',
    'rheo.f.gel.name': 'Punto de gel',
    'rheo.f.gel.note': 'Se informa solo cuando los dos módulos permanecen dentro de la tolerancia entre sí mientras el módulo de almacenamiento supera al de pérdida. La tolerancia importa: un test de cruce simple se dispara con ruido en un barrido ruidoso, así que los dos módulos deben coincidir en varios puntos consecutivos.',
    'rheo.f.gel.expressionNote': '(punto de gel: el ω donde los dos módulos concuerdan dentro de la tolerancia, con G\' > G\'\')',
    'rheo.f.gel.referenceNote': 'El criterio riguroso es una ley de potencia en ambos módulos; el cruce de los dos es una aproximación práctica.',
    'rheo.f.cross.name': 'Frecuencia de cruce',
    'rheo.f.cross.note': 'La frecuencia donde el fundido deja de comportarse elásticamente. Se desplaza con la temperatura, así que un cruce citado sin su temperatura no es reproducible.',
    'rheo.f.cross.expressionNote': '(cruce)',
    'rheo.f.cross.referenceNote': 'El cruce de los módulos es un marcador práctico de la transición terminal-meseta en un polímero lineal; se desplaza con la frecuencia, así que el valor solo es comparable entre mediciones hechas a la misma frecuencia angular.',
    'mol.f.mn.name': 'Medias numérica y ponderal',
    'mol.f.mn.Ni': 'número de cadenas de masa molar Mi',
    'mol.f.mn.Mi': 'masa molar de la especie i (g/mol)',
    'mol.f.mn.note': 'Mn es la media simple entre cadenas, Mw pondera cada cadena por su masa. Mw es siempre mayor o igual que Mn; si un resultado lo viola, el error está en los datos o en la aritmética, no en el polímero.',
    'mol.f.pdi.name': 'Dispersidad',
    'mol.f.pdi.note': 'Una dispersidad de 1,0 significa que todas las cadenas tienen la misma longitud, lo que ninguna polimerización real alcanza: el mínimo teórico para una polimerización aniónica viva es de unos 1,02. Valores cercanos a 2 indican un mecanismo por etapas o dominado por transferencia de cadena.',
    'mol.f.pdi.expressionNote': '(dispersidad, antiguamente índice de polidispersidad)',
    'mol.f.pdi.referenceNote': 'La IUPAC recomienda el término dispersidad y el símbolo D. Un valor por debajo de 1 no es una distribución estrecha, sino un error en los datos o en el cálculo.',
    'mol.f.mz.name': 'Media z',
    'mol.f.mz.note': 'La media z es la que usan la dispersión de luz y la viscosimetría, así que compararla con el Mw de la misma traza verifica la forma de la distribución, no solo su posición.',
    'mol.f.mz.referenceNote': 'El promedio z está ponderado hacia las cadenas más pesadas, así que responde a una cola de masa alta que el Mw apenas registra.',
    'mol.f.mh.name': 'Mark-Houwink-Sakurada',
    'mol.f.mh.Mv': 'masa molar media viscosimetrica (g/mol)',
    'mol.f.mh.K': 'constante específica del polímero, disolvente y temperatura',
    'mol.f.mh.a': 'exponente, 0,5 en un disolvente teta y hasta unos 0,8 en un buen disolvente',
    'mol.f.mh.note': 'Mv queda entre Mn y Mw y se acerca a Mw cuando a está cerca de 1. Usar K y a de otro disolvente o temperatura da una masa molar sistemáticamente errónea que parece perfectamente razonable.',
    'mol.f.mh.referenceNote': 'Relación de Mark-Houwink-Sakurada; K y a están tabulados por combinación polímero-disolvente-temperatura en el Polymer Handbook. No son constantes universales.',
    'mol.f.gpc.name': 'Calibración en SEC',
    'mol.f.gpc.note': 'La curva de calibración convierte el volumen de elución en masa molar usando estándares de otro polímero, salvo que los estándares sean del mismo material que la muestra. Por eso un resultado de SEC convencional es una masa molar relativa, y por eso debe informarse el estándar de calibración.',
    'mol.f.gpc.expressionNote': '(calibrada contra estándares estrechos)',
    'mol.f.gpc.referenceNote': 'La calibración convencional de GPC supone que la muestra y los estándares tienen el mismo volumen hidrodinámico en un volumen de elución dado. Informar el resultado como masa molar absoluta sin detector de dispersión de luz o viscosimetría exagera lo que la medición sostiene.',
    'mol.f.log.name': 'Distribución log-normal',
    'mol.f.log.note': 'Un modelo, no una medición. Se muestra para comparar la forma de una distribución medida con una idealizada, y supone que la traza no tiene ensanchamiento de columna, que ensancha toda traza real.',
    'mol.f.log.referenceNote': 'Las distribuciones de Schulz-Zimm y log-normal son los modelos habituales para una traza de SEC; aquí se usa la log-normal porque su Mw/Mn se deduce directamente de sigma.',
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
    /**
     * Like `t`, but returns null when the key is unknown instead of echoing
     * the key. Use when the caller holds a server-supplied fallback string:
     * a missing translation must degrade to that text, not to a dotted key
     * shown to the user.
     */
    const tOrNull = (key) => {
      const table = MESSAGES[language] || MESSAGES.en;
      if (table[key] !== undefined) return table[key];
      if (MESSAGES.en[key] !== undefined) return MESSAGES.en[key];
      return null;
    };
    return { language, setLanguage, t: translate, tOrNull };
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
