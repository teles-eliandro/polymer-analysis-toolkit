# Polymer Analysis Toolkit: characterisation analysis that states its own limits

**Eliandro P. Teles**

---

## Abstract

The Polymer Analysis Toolkit (PAT) is an open-source web application that
computes molecular, thermal, mechanical, rheological and structural properties
of polymers from data that laboratories already produce. This paper describes
what the tool computes, how each result was verified, and — in more detail than
is customary — what could not be verified.

Two findings from the verification work are general enough to be worth
reporting independently of the tool. First, running a **real** instrument trace
through the analysis endpoint returned an HTTP 500, while 149 tests built on
synthetic data all passed; the cause was unmeasurable peaks serialised as NaN.
Second, a crystallinity index computed against a straight-line baseline
saturates at 100 % on patterns whose amorphous halo decays steeply, and did so
on all five real diffraction patterns tested. Both defects were invisible to
internally consistent test data and only appeared under external data.

A third round of verification, against four raw datasets published on figshare
by a single laboratory, established a pattern that the first two defects only
hinted at. In every module tested the analysis accepted an input that was not
physically what the code assumed — a transmittance spectrum where absorbance
was expected, a heat-flow trace whose endotherm pointed down, a thermogravimetric
trace ending at negative mass — and returned a confident number rather than
refusing. Two of those inputs inverted and corrupted the result across whole
families of samples; the third produced an impossible quantity that was reported
without comment. The failures were not arithmetic. They were the absence of a
check on the *input*.

All reference values used here were downloaded by a script in the repository.
None was transcribed by hand.

---

## 1. Scope

PAT implements five modules. Each takes data as exported by common instruments,
either pasted or uploaded, and returns numbers with their method, units and
assumptions attached.

| Module | Input | Output |
|---|---|---|
| Molar mass | GPC/SEC export or distribution table | Mn, Mw, Mz, Mz+1, Đ, Mv |
| Thermal | TGA or DSC trace | Td, residue, DTG peak; Tg, Tm, ΔHm, Xc |
| Mechanical | Tensile stress–strain curve | E, yield, tensile strength, elongation, toughness |
| Rheology | Frequency sweep (ω, G′, G″) | Crossover, plateau modulus, terminal slopes, gel test |
| Structure | XRD pattern, FTIR spectrum | Peak indexing, d-spacing, crystallite size; band assignments |

The interface is trilingual (English, Portuguese, Spanish) and the backend
exposes an OpenAPI schema; the frontend consumes response field names from
that schema rather than assuming them.

### 1.1 Molar-mass averages

Weight fractions are assumed, since that is the convention in GPC/SEC raw data:

$$M_n = \frac{1}{\sum_i (w_i/M_i)}, \qquad M_w = \sum_i w_i M_i, \qquad Đ = \frac{M_w}{M_n}$$

with $M_z = \sum w_iM_i^2 / \sum w_iM_i$ and
$M_{z+1} = \sum w_iM_i^3 / \sum w_iM_i^2$.

The viscosity average $M_v$ requires the Mark–Houwink exponent $a$ for the
specific polymer–solvent pair. It is reported **only** when that exponent is
supplied, because a default would silently produce a wrong number that looks
like a measurement.

---

## 2. Verification against published values

Internal consistency tests — $M_n \le M_w$, unit-exponent identities, analytic
solutions — show that the code does what it was intended to do. They carry no
information about agreement with reality. The verification described here is
of the second kind.

### 2.1 Reference sources

| Source | Licence | Provides |
|---|---|---|
| NIST IR 6091 (`10.6028/nist.ir.6091`) | open access | Certified Mw of SRM 706a polystyrene with uncertainty |
| Zenodo `10.5281/zenodo.17306416` | CC-BY-4.0 | GPC/SEC of PLA in THF: 10 samples with Mn, Mw, Mz, Mz+1 and the instrument's own uncertainties |
| Zenodo `10.5281/zenodo.17288962` | CC-BY-4.0 | DSC of PLLA at three molecular weights, declared protocol |
| Zenodo `10.5281/zenodo.17293641` | CC-BY-4.0 | DSC of commercial polycaprolactone, declared protocol |
| Zenodo `10.5281/zenodo.20466241` | CC-BY-4.0 | WAXS of PLA/PE films, λ = 1.541 Å declared in the file header |
| figshare `10.6084/m9.figshare.24462004` | CC-BY-4.0 | 116 raw DSC `.tri` files, 21 polymer families |
| figshare `10.6084/m9.figshare.24593022` | CC-BY-4.0 | 59 raw FTIR spectra plus 28 TGA–FTIR, instrument export format |
| figshare `10.6084/m9.figshare.24595695` | CC-BY-4.0 | 27 TGA–FTIR with EGA: TGA trace and evolved-gas FTIR per mass-loss event |

The three figshare sets come from one laboratory and one instrument family, so
they share an export convention. That turned out to matter more than the
individual values: it is what makes a defect visible as a *pattern* rather than
as an outlier to be excused.

`scripts/fetch_reference_data.py` downloads and extracts all of them. Values
are parsed from the source documents, never typed in; a value recalled from
memory is not a citation.

### 2.2 A gate on the reference itself

Before published values are used to judge the implementation, they are tested
against the relations the theory imposes on them. For molar-mass moments:
$M_n \le M_w \le M_z \le M_{z+1}$, and the published $M_w/M_n$ and $M_z/M_n$
must recompute from the published moments.

**Result: 10 of 10 instrument reports passed all three checks.** Only then were
they used as a yardstick. A reference that fails this gate can only produce
confident nonsense.

### 2.3 Coverage, decided before the numbers were seen

When comparing against a dataset that is a *subset* of what the original
analysis used, a disagreement may indicate that the data does not reach the
reported value — not that the implementation is wrong.

The rule, fixed in advance: compare only samples whose tabulated range
demonstrably contains the reported value.

- **8 samples** met the rule: **median deviation in Mw = 4.94 %**, **maximum
  35.0 %**
- **2 samples excluded**: their reconstructed mass range does not contain the
  reported Mw (`[8829, 19377]` against a reported 8541; `[7.3×10⁵, 2.2×10⁷]`
  against a reported 1.7×10⁵). The table holds a different peak.

The median alone would flatter the result, so the distribution is shown:

| Sample | Reported Mw | Computed Mw | Deviation |
|---|---|---|---|
| PDLA_25k_THF | 8 909 | 12 031 | 35.0 % |
| LL50_THF | 26 350 | 24 200 | 8.2 % |
| DL50_THF | 15 010 | 13 805 | 8.0 % |
| PDLA_50k_THF | 10 510 | 9 967 | 5.2 % |
| DL15_THF | 7 229 | 7 571 | 4.7 % |
| DL25_THF | 15 440 | 14 759 | 4.4 % |
| LL10_THF | 13 190 | 13 557 | 2.8 % |
| LL25_THF | 20 860 | 20 312 | 2.6 % |

Six of the eight agree within 8.2 %; one is an outlier at 35 %. The
disagreement is in the direction of the reconstruction, and reflects the fact
that the tabulated `(dRI, M)` pairs are not the full slice distribution the
instrument integrated — they are a coarser export of it. The test tolerance is
set at 15 %, loose relative to the median, and exists to catch a gross
regression rather than to claim precision.

Applied after the fact, the exclusions would be worthless. The inclusion
criterion is recorded in the assertion messages so a reviewer can see it was
not fitted.

### 2.4 Thermal module against a real scan

The polycaprolactone dataset declares its protocol (10 K/min, heat–cool–heat)
and its file header states the sample mass, so both the heating rate and the
mass are read from the source rather than assumed.

| Quantity | Measured | Literature |
|---|---|---|
| Tm | 56.41 °C | 56–60 °C |
| ΔHm | 86.2 J/g | ≤ 139.5 J/g (100 % crystalline) |
| Xc | 61.8 % | 40–55 % |

Tm agrees. ΔHm is stable across smoothing windows of 5 to 21. Xc lies above
the commonly quoted range, which is plausible for a slowly cooled commercial
sample but is stated as a deviation rather than rounded into agreement.

The PLLA dataset gives three molecular weights. From the second heating, with
heating rate 10 °C/min and ΔH°m = 93 J/g:

| Sample | Tm | ΔHm | Xc |
|---|---|---|---|
| PLLA 10 kg/mol | 167.4 °C | 61.7 J/g | 66 % |
| PLLA 25 kg/mol | 171.9 °C | 44.1 J/g | 47 % |
| PLLA 50 kg/mol | 173.2 °C | 61.8 J/g | 66 % |

Tm falls in the published range for PLLA (170–180 °C) and Xc in the 40–60 %
range typical of melt-crystallised PLLA. Glass transition is not resolved in
these traces, consistent with a high degree of crystallinity leaving only a
small heat-capacity step.

### 2.5 TGA against 27 raw instrument traces

The figshare `24595695` set carries a TGA trace and the evolved-gas FTIR
spectrum of each mass-loss event, for 27 samples across 13 polymer families.
Two CSV layouts ship inside the one dataset — 10 columns (two FTIR tables plus
the TGA pair) in 20 files, 6 columns (one FTIR table plus the pair) in the
other seven — so the TGA column is located by its header text rather than by
position.

The dataset does not state its heating rate or atmosphere, which rules out a
comparison of absolute decomposition temperatures: $T_d$ shifts 30–60 °C with
heating rate between 1 and 20 K/min. What *is* comparable, because it does not
depend on either, is the **residue** — the mass that survives at 700 °C.

| Sample | Residue measured | Literature | Note |
|---|---|---|---|
| PAN-1 | 34.8 % | 30–60 % | carbon ladder from nitrile cyclisation |
| PVC-1 / PVC-2 | 9.5 % / 16.8 % | 8–25 % | char after HCl loss; both show two stages |
| Nylon-6 | 2.7 % | 0–5 % | |
| SAN-1 | 0.8 % | 0–5 % | |
| PMMA-1 | 0.7 % | 0–3 % | |
| PS-2 | 0.3 % | 0–3 % | |
| PE-2 | 0.04 % | ~0 % | |

**18 of 26 files** land inside their family's residue window, and the strong
cases are the ones that discriminate: PVC is the sharpest test in the set,
because its residue is large, characteristic and replicated, and all three
conditions are met. One file, EVA-3, reports 19.9 % against 0.46 % and 6.26 %
for its own two replicates — a forty-fold spread inside one family. That is a
property of the dataset rather than of the analysis, and it is the reason a
single trace should not be quoted on its own.

Stage counts agree with expectation in 17 of 26 files. The disagreements are
concentrated where a weak event rides on a strong one: the analyser reports it
in a note rather than splitting it into a step it cannot resolve.

---

## 3. Defects found only by external data

### 3.1 Unmeasurable peaks serialised as NaN

A real WAXS trace from `10.5281/zenodo.20466241` was posted to
`/api/v1/structure/xrd`. **The endpoint returned HTTP 500.** The existing 149
tests all passed, because synthetic peaks are always wide enough to measure.

A peak whose half-maximum crossings fall outside the search window has no
measurable width. The implementation wrote `float("nan")` into `fwhm_deg` for
such peaks. NaN is not valid JSON, and Starlette serialises with
`allow_nan=False`, so the response could not be built. In one 110-point window
of the real trace, **nine local maxima** are of this kind — sub-sampling
ripples, not physical peaks.

The fix drops peaks that cannot be measured, leaving the parallel arrays
shorter and valid, and narrows the type of `crystallite_size_nm` from
`list[float | None]` to `list[float]`.

Three regression tests use a recorded segment of the real trace. Each was
confirmed to **fail** when the fix is reverted. A synthetic Gaussian on a flat
background does not reproduce the fault, which is precisely why the original
suite missed it.

### 3.2 A crystallinity index that saturates

The crystallinity index divides peak area by total area. On a pattern from a
q-space profile in arbitrary units, the amorphous halo decays steeply — in the
files tested the intensity roughly halves across the range. A straight-line
baseline therefore sits below every measured point, the entire trace counts as
crystalline, and the index pins at **100 %**.

All five of the real films tested returned 100 %. The number was computed
correctly from a baseline that is inappropriate for this data; the index needs
an amorphous reference these files do not carry.

A saturated index is not a measurement, so it is now reported as **None**
rather than as 100 %. A test with a flat baseline confirms the index is still
reported when it is meaningful.

### 3.3 Three inputs the analysis accepted without checking

The figshare datasets exposed a family of defects that share one shape: the
analysis assumed a property of its **input** and never verified it. Each
produced a confident number that was not a measurement.

**A transmittance spectrum where absorbance was expected.** The structure
module's FTIR path expects absorbance, as its own docstring states. All 59
spectra in `24593022` export `%T`, as does the evolved-gas FTIR in `24595695` —
two datasets, one laboratory, the same convention. The module accepted them
without comment.

| Input units | Median peaks reported | Plausible as a spectrum |
|---|---|---|
| Transmittance (as exported) | 100 | 1 of 58 |
| Absorbance (converted) | 16 | 48 of 52 |

On a polyethylene spectrum the converted form recovers the four known
absorption bands at 2915, 2848, 1473 and 730 cm⁻¹. The unconverted form reports
103 peaks beginning at 3998 cm⁻¹, because a broad transmittance band reads as a
monotonic ramp. **57 of 58 spectra** returned meaningless output, and the one
that happened to fall in range did so by accident. Four files saturate near
`%T = 0`, where the conversion to absorbance diverges — a limit the detector
must treat as unusable rather than convert.

**A heat-flow trace whose endotherm pointed down.** The thermal module assumes
the endotherm points up, which is stated in its own docstring. The `24462004`
set records it pointing down: across the traces measured, $\mathrm{corr}(T,
\Delta H)$ runs from −0.6 to −0.98.

With the sign untreated, the melting-peak search looks for a maximum where the
melting peak is a minimum. It finds instead the cell's start-up transient,
which sits on the first sample of the scan, and reports it as the melting
temperature. Because `T[0]` is the temperature the run began at, the same
number then appeared as the melting point of six different polymer families —
**−90.06 °C** for PLA, PE-NEW and others, **−0.06 °C** for PET and PBT. Six
distinct polymers cannot share a melting point; that coincidence is what
identified the defect.

After the polarity is detected from the width of the dominant extremum (a real
melting event spans 10–325 °C; the start-up transient spans 0.1–0.4 °C and sits
on the scan edge), the melting temperature lands inside its literature window
for **52 of 58 files** that report one, against essentially none before.

**A thermogravimetric trace ending at negative mass.** Seven of the 27 files in
`24595695` end between −0.35 % and −1.41 %, and report that as the residue. The
values are in the raw CSV, so the reader is faithful; the defect is that
nothing said a negative mass is not a measurement. The number is now passed
through **unchanged** — it is what the instrument wrote, and clamping it to
zero would hide a balance fault the analyst needs to see — but it arrives with
a note stating that it cannot be quoted as a residue.

### 3.4 Why this matters beyond these bugs

The defects share a shape: **the code was internally consistent and externally
wrong.** In the first case the value was not representable in the output
format; in the second the value was representable, computed correctly, and
meaningless. The three in §3.3 are a further step back — the arithmetic is
right and the *input* is not what the code assumed, so the result is wrong at
the level of physical interpretation and no amount of correct computation
recovers it. None of the five was reachable from data generated by the same
assumptions as the implementation.

The practical rule: an *impossible* value — crystallinity above 100 %,
dispersity below 1, an enthalpy exceeding that of a fully crystalline sample, a
non-finite number in a response, a negative mass, a transmittance spectrum
handed to an absorbance parser — is a signal about the input or the model, not
a rounding artefact to be tolerated. Such bounds deserve explicit assertions so
they cannot pass silently.

A second rule follows from the first, and cost more to learn: **a fix applied
at the point of failure is often the wrong fix.** The polarity defect was first
attacked by improving the melting-peak detector — three successive attempts,
each passing its synthetic test and each failing on the real traces — because
the detector was where the wrong number appeared. The defect was one level up,
in the sign of the input, and none of the detector work could have found it.

### 3.5 A performance defect that blocked its own diagnosis

`_find_step_temperature` recomputed the gradient of the entire trace inside its
candidate loop: 11 795 calls of 16 202 points each, for one file. Profiling put
**34 of 38 seconds** there. The cost was not merely inefficiency — a full sweep
of the 116 files took about ninety minutes, so each attempt at the polarity
defect cost an hour and a half to evaluate.

Hoisting the gradient out of the loop is arithmetically identical and takes a
single file from **38 s to 4.6 s**; the full sweep now runs in 10.6 minutes.
The optimisation was done *before* the correctness work that depended on it,
which is the reverse of the usual order and was the right call: the diagnosis
in §3.3 was not affordable until it was done.

A measurement worth recording: for the same input, the twelve-resample
confidence bootstrap and the single-pass analysis produce the **identical**
melting temperature to sixteen digits. The bootstrap computes an uncertainty
and does not change the answer, which is why it is now separable.

---

## 4. What is not established

Stated as open items rather than omitted. Each is recorded in the test suite as
`xfail(strict=True)`, so that an unexpected pass **fails the build** and forces
the claim to be revisited instead of decaying unnoticed.

1. **Agreement with a certified value.** The NIST certificate for SRM 706a
   publishes only Mw; the slice-by-slice distribution it derived from is not in
   an open repository. A certified reference is the strongest available
   standard and remains unmet.
2. **An independent Mv.** This requires a Mark–Houwink (K, a) pair for a
   specific polymer–solvent system *and* a measured intrinsic viscosity from
   the same sample. Neither alone is sufficient.
3. **Tg of the semi-crystalline PCL sample.** Not resolved in this measurement,
   as expected at ~55 % crystallinity.
4. **The glass transition of the semicrystalline samples in `24462004`.** Of
   107 traces, **71 report a Tg outside its literature window**, and the
   failures are systematic rather than scattered: PE, PP and Nylon report
   175–271 °C, which is the flank of the melting peak and not a glass
   transition at all. Three separate discriminators were attempted — a
   shape-symmetry gate, a width test, and a step-versus-peak test — each of
   which passed its synthetic case and each of which failed here. The
   detectors were then reverted rather than tuned further, because the
   attempts were degrading the amorphous cases that do work (PS, PVC, PC and
   ABS, all four within a few degrees of their published values). A defect
   that resists three attempts may be misdiagnosed rather than merely hard,
   and further patching was making the suite worse, not better.
5. **Melting enthalpy under inverted polarity.** With the sign corrected, Tm is
   right and `ΔHm` is wrong by two orders of magnitude — PLA reports 0.229 J/g
   against a plausible 20–40 J/g, and a fully crystalline reference of 93 J/g.
   The position of the peak is recovered by negating the signal; the enthalpy
   integral is not, because it accumulates `hf − baseline` and therefore has
   the sign carried into it. The polarity fix is a Tm fix, not an enthalpy
   fix, and the two must not be reported as though the same correction served
   both.
6. **Polarity assignment where no melting event exists.** The detector
   establishes the sign from the width of the dominant extremum, which is
   undefined when there is no such extremum — and is unstable in the handful
   of files where both extrema sit on the scan edge (PVAc1-AR and PVAc1-CRYO
   disagree with each other, as do PS3-AR and PS3-CRYO). The sign is a property
   of the instrument, not of the sample, so it belongs to the dataset; deriving
   it per file is the wrong unit of analysis and is why the instability appears.

Accordingly: the mathematics is verified against exact cases, agreement with
instrument-reported values is **4.9 % median in Mw** over the samples where
comparison is meaningful, and where a corrected thermal analysis was compared
against literature it agrees in **52 of 58** melting temperatures and **18 of
26** TGA residues. Agreement with a *certified* value is **not** demonstrated,
and is not claimed.

---

## 5. Reproduction

```bash
git clone https://github.com/teles-eliandro/polymer-analysis-toolkit
cd polymer-analysis-toolkit
python scripts/fetch_reference_data.py        # downloads the sources above

cd backend && python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest                    # 202 passed, 3 xfailed

cd ../frontend && npm ci
CI=true npx react-scripts test --watchAll=false   # 7 passed
```

The three figshare datasets are large (the DSC set alone is 3.1 GB) and are
fetched on demand; `scripts/run_all_116_polarity.py`, `run_all_ega_tga.py` and
`validate_ega_literature.py` regenerate every number quoted in §3.3 and §2.5
from the raw files. `scripts/results_116_polarity.txt` holds the recorded
output of the 116-file sweep.

The reference data is deliberately **not** committed: it carries its own
licence and runs to tens of megabytes. Tests that need it skip cleanly when it
is absent, naming the script that fetches it.

Ready-to-use extracts of the real data — five WAXS patterns converted to 2θ,
three PLLA second-heating DSC traces, with the conversions and the expected
results documented — are described in `pat-test-data/README.md`.

---

## 6. Conclusion

A characterisation tool earns its keep by being wrong in ways its user can
detect. Four choices follow from that: report a quantity only when its inputs
are available (Mv needs $a$; Xc needs ΔH°m; the crystallinity index needs an
amorphous reference); state the method and its limits beside every number,
including when the answer is "not determined"; **check that the input is what
the method assumes**, since a transmittance spectrum, an inverted heat-flow
trace and a negative mass are all accepted without complaint by arithmetic that
is otherwise correct; and verify against data the implementation did not
generate.

The verification described here found five defects that no amount of internally
consistent testing would have surfaced, established that the three
input-checking failures share a single cause, and leaves six questions open.
Both outcomes are the point of doing it.

The clearest lesson is about the cost of the last three. They were found only
because the analysis was made fourteen times faster first; at ninety minutes
per sweep, the polarity defect would have been characterised by three attempts
instead of the eight it took, and the third would have looked like the last
possible one.

---

## References

1. NIST, *Recertification of SRM 706a, a Polystyrene*, NIST IR 6091, 1998.
   `10.6028/nist.ir.6091`
2. GPC/SEC measurements of poly(lactic acid), Zenodo. `10.5281/zenodo.17306416`
3. DSC of poly(lactic acid) samples of differing molecular weight, Zenodo.
   `10.5281/zenodo.17288962`
4. DSC of commercial polycaprolactone, Zenodo. `10.5281/zenodo.17293641`
5. Laboratory and synchrotron X-ray scattering from poly-lactic acid/polyethylene
   blends, Zenodo. `10.5281/zenodo.20466241`
6. Raw DSC data files, figshare. `10.6084/m9.figshare.24462004`
7. FTIR raw data files, figshare. `10.6084/m9.figshare.24593022`
8. TGA-FTIR with EGA raw data files, figshare. `10.6084/m9.figshare.24595695`
9. ASTM D3418, *Standard Test Method for Transition Temperatures and Enthalpies
   of Fusion and Crystallization of Polymers by Differential Scanning
   Calorimetry*.
10. ASTM E2550, *Standard Test Method for Thermal Stability by Thermogravimetry*.

## Licence

MIT. Source: <https://github.com/teles-eliandro/polymer-analysis-toolkit>
