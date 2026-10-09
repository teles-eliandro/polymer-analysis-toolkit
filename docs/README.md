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

A fourth round, on 116 raw DSC traces from that same laboratory, drew a
boundary the earlier work had left implicit. The tool reads and plots those
files correctly — the decoder recovers all fourteen channels and reconstructs
the programmed method — but **identifying which transition is which is not
reliable**: the glass transition lands in its published window about 30 % of
the time, and the melting detector reported a melting temperature for
amorphous polystyrene, which cannot melt. Four independent shape
discriminators were tested against the real set; none separates a melting
endotherm from a glass transition, because the two events can have arbitrary
and overlapping sizes. Since that boundary cannot be moved by tuning, the tool
was changed to state it instead of crossing it: every reported value now
carries a confidence rung — *read*, *formula*, or *suggested* — and transition
temperatures are never presented as anything but suggested. The general
finding is that a tool whose inference cannot be made reliable should be built
to say so per field, rather than to be trusted or distrusted as a whole.

All reference values used here were downloaded by a script in the repository.
None was transcribed by hand.

A fifth round inverted the question. The four rounds above all found inputs that
were not what the method assumed. The fifth found a valid input, correctly read,
interpreted wrongly: the sample-name resolver matched any alias that *prefixed*
a name, so a polyetherketoneketone sample (`PEKK`) resolved as **polyethylene**,
and `PEI`, `PES`, `PESU`, `PEN` resolved the same way, while three unrelated
nylons resolved as nylon-6. The tool then reported a number that was
arithmetically correct for the wrong material. Unlike the earlier defects, this
one returned a wrong *identity* rather than a wrong number — a coherent,
defensible-looking statement about the wrong substance. It was found by typing
a name into the running application; all 332 tests passed while it was present,
because the resolver had no test asserting a name it should **refuse**.

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

### 1.1 Two kinds of result, and why they are separated

Each returned number carries a confidence rung, because the modules do not all
do the same kind of work:

| Rung | Meaning | Examples |
|---|---|---|
| `read` | A property of the input file, or a deterministic transform of it | time and temperature axes, sample mass, programmed method, the plotted curve |
| `formula` | A published formula applied to a declared input; reproducible from the formula and its bounds | molar-mass averages, Mark–Houwink, Scherrer, enthalpy integration, crystallinity from a reference enthalpy |
| `suggested` | An inference from the shape of the trace; can be wrong | **which transition is which** — Tg, Tm, Tc |

The distinction is not cosmetic and the third rung is not a hedge. On the 116
real DSC traces of §3.6 and item 4 of §4 the transition identification is wrong often
enough that presenting it as a measurement would be misleading, while reading
the file and plotting it are correct in every file tested. A `formula` result
built on a `suggested` input (an enthalpy integrated over a suggested peak)
states that dependency, because it inherits the peak's uncertainty rather than
escaping it. Every `suggested` value is returned with the observations that
produced it, so the inference can be judged instead of trusted.

The interface is trilingual (English, Portuguese, Spanish) and the backend
exposes an OpenAPI schema; the frontend consumes response field names from
that schema rather than assuming them.

### 1.2 What a comparison may say

A measured value is compared against the published range of the polymer the
sample is named as. That comparison has **three** outcomes, not two:

| Verdict | Meaning |
|---|---|
| `within` | The measured value lies inside the published range |
| `outside` | It lies outside a range that is known for this polymer |
| `not_comparable` | No comparison was made, with the reason stated |

The third outcome is the one that matters. A two-state comparison forces a
"outside range" verdict whenever the tool cannot compare, which reports a
disagreement where there is only an absence of information. `not_comparable`
carries a machine-readable reason, so the interface can say *why*: the polymer
was not identified, no range is on file for the property, or the sample name
does not correspond to any entry. The reason is translated, so a reader in
another language sees the same explanation.

The repertoire holds **37 polymers** with cited ranges, reached through 65
aliases. An entry whose range cannot be cited does not belong in it.

### 1.3 Molar-mass averages

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

### 3.6 A melting temperature read from the end of the programmed ramp

The melting detector located its peak with `argmax(y − chord)`, where the chord
joins the first and last sample of the scan. That construction is degenerate
whenever the curve lies entirely below the chord: the residual's maximum is
then exactly `0.0` and occurs at index 0 **by definition**, because the chord
touches the curve at both ends. On the figshare 24462004 traces this is the
rule rather than the exception — the heat flow at the start of a ramp is the
global maximum of the series (the sample is coldest there, and the instrument
stores exothermic-up) — so the degeneracy fired on PLA, EVA, PET, PBT and ABS
alike:

| File | Reported Tm | What it actually was |
|---|---|---|
| `PLA1-AR` | **−90.06 °C** | the first sample of the ramp |
| `EVA2-AR` | **−90.06 °C** | the first sample of the ramp |
| `PET2-AR` | **−0.06 °C** | the first sample of the ramp |
| `PE-NEW-AR` | **159.43 °C** | the last sample of the ramp |

Because the melting window is what the glass-transition search then excludes, a
wrong Tm poisoned the Tg as well — which is why the reliability flag never once
fired `True` across the 116 traces.

Two things are worth separating, because only the first was fixed. The initial
defect was in the *locator*; the second was in the *refinement*, which then
re-entered the same bug through a different door. After the locator was
rewritten to find a peak by shape — a point that is the maximum of its own
neighbourhood, a definition that cannot degenerate because it never references
the scan's ends — the refinement still called `nanargmax(abs(excess))` over the
*whole* trace, which returns index 0 wherever the fitted baseline is furthest
from the curve, typically at an extrapolated end. On `PET2-AR` that returned
index 0 and the reported Tm went back to `−0.06` even though the shape search
had already found the real endotherm at 254.0 °C. Confining the refinement to
the candidate's neighbourhood is what actually closed the defect.

Measured on the full 116-file sweep:

| | Before | After |
|---|---|---|
| Tm reporting the end of the ramp | ~13 files | **0** |
| Tm outside the published window | 13/116 | 10/116 |
| Newly reporting a Tm that is not there | — | 4 files |

The absurd mode is gone; the overall hit rate is not fixed, and four traces
(EVA at 234.9 °C against an expected 60–100, PP2 at 233.1 against 150–175) now
report a melting temperature that is not present. This is recorded as a
regression in the account, not hidden in the diff.

### 3.7 An input read correctly and interpreted wrongly

The defects above share a shape: the input was not what the method assumed, and
the arithmetic returned a confident number anyway. This one is the inverse, and
it is the more dangerous of the two families. The input was a valid sample name.
The file was read and plotted correctly. The defect was in deciding **which
polymer the name denoted**.

The sample-name resolver accepted any alias that *prefixed* the name, on the
reasonable-seeming principle that instrument files add qualifiers (`PLA1-AR`,
`ABS2`, `PE-NEW`). The consequence was not a near miss. Because `pe` prefixes
`pekk`, a polyetherketoneketone sample was resolved as **polyethylene**; `pei`
(polyetherimide), `pes` and `pesu` (polysulfones) and `pen` (polyethylene
naphthalate) resolved the same way. `ppo` and `ppe` became polypropylene;
`pa46`, `pa610` and `pa1010` — three distinct nylons with melting points
unrelated to nylon-6 — all became **PA6**.

| Sample name | Resolved as | Is actually | Would have been reported |
|---|---|---|---|
| `PEKK` | PE | polyetherketoneketone | Tm compared against polyethylene's range |
| `PEI` | PE | polyetherimide (Tg ≈ 217 °C) | outside range, confidently |
| `PESU` | PE | polysulfone (Tg ≈ 190 °C) | outside range, confidently |
| `PEN` | PE | polyethylene naphthalate (Tm ≈ 265 °C) | outside range, confidently |
| `PPO` | PP | polyphenylene oxide (Tg ≈ 210 °C) | outside range, confidently |
| `PA46` | PA6 | nylon-4,6 (Tm ≈ 295 °C) | outside range, confidently |

The failure is worse than the earlier ones in one respect: those returned a
wrong *number*, which a researcher can sanity-check against known values. This
returned a wrong *identity*, and then a number that was arithmetically correct
for that identity. A Tg of 210 °C reported as "outside the polyethylene range"
is a coherent, defensible-looking statement about the wrong material.

The defect was found by typing `PEKK` into the running application, not by any
test. Every one of the 332 tests passed while it was present; the resolver had
no test that asserted a name it should *refuse*.

The fix removes open-ended prefix matching entirely, since the string shape
alone cannot distinguish the cases: `ABS2` and `PA46` are both letters followed
by digits. Names now resolve in exactly three shapes an instrument produces —
an exact alias, a trailing run index, or a separator-delimited qualifier — and
everything else resolves to nothing, producing `not_comparable` with the reason
`polymer_unidentified`. Two rules separate the cases the shapes cannot:
a digit fragment after a separator is a run index (`GPPS-1` resolves), while a
**letter** fragment continues the name (`PVC-C` is refused, since PVC-C is
chlorinated PVC, not a labelled PVC). The bare `pa` alias was removed because
it named "polyamide" generally while being matched as nylon-6 — it was the
mechanism that turned `PA46` into `PA6`.

The test file now asserts **48 real instrument names that must resolve and 31
wrong identifications that must be refused**, by name, so that adding an alias
cannot silently reopen the shadowing it was added to prevent. The general
lesson is narrower than "add more tests": a resolver needs tests for the inputs
it should reject, and a passing suite says nothing about a class of input it
never states.

### 3.8 A glass transition reported above the temperature that destroys it

The defects in §3.1–§3.3 were inputs the analysis accepted without checking.
This one is a *constraint* the analysis did not know it had.

A DSC scan of an amorphous or quenched polymer passes through a fixed sequence
of events: the glass transition, then — if the sample is crystallisable —
cold crystallisation (exothermic), and only then melting. D. Dean,
*Differential Scanning Calorimetry* (University of Alabama at Birmingham),
slide 29 gives this sequence, and slide 28 defines the middle event. The
sequence is not a convention; it is a consequence of the free-energy landscape.
And it imposes an ordering the analysis can enforce: **a glass transition lies
below the cold-crystallisation peak**, because after crystallisation the
amorphous phase that produces the step no longer exists.

The tool violated this. On the three literature PLLA traces of Zenodo
10.5281/zenodo.17288962 (Tg of PLLA is about 60–65 °C):

| Trace | Tg reported | Cold-crystallisation peak | Physically possible? |
|---|---|---|---|
| `PLLA_10K` | 87.6 °C | 85.3 °C | no |
| `PLLA_25K` | 94.2 °C | 90.8 °C | no |
| `PLLA_50K` | 94.7 °C | 91.8 °C | no |

In all three the reported glass transition sat **above** the exothermic
minimum. The cause is measurable: on the `PLLA_50K` trace the descending limb
of the cold-crystallisation peak reaches a gradient of **−0.332 W/g/K** at
90 °C, twenty times the +0.017 W/g/K of the actual glass-transition step at
55 °C. Both the window-mean search and the classical `|dhf/dT|` construction
rank by magnitude, so the crystallisation event won every time, and the real
step was never a contender.

The fix adds one rule: candidates at or above the cold-crystallisation peak are
not glass transitions. The cold-crystallisation temperature is *found* rather
than assumed — a narrow, significant downward excursion before the melting
peak — and when a trace has no such event the rule is inert, so it can only
remove an impossible answer and never invent one. Three guards keep the finder
from firing on traces that have no cold crystallisation, and each was added
after it fired wrongly: the excursion must be detrended (a merely sloping
baseline made the lowest point look like an event), must return on **both**
sides (the descending wall of a melting ramp satisfied a one-sided test), and
must be **narrow** at half height (real events measured 3.5–4.3 °C, a melting
ramp 39.2 °C).

Two things this did and did not do, stated separately because the difference
matters:

* **It removed the impossibility.** No PLLA trace now reports a Tg above its
  cold-crystallisation peak, and the 332-test suite is unchanged — the rule
  broke nothing.
* **It did not produce the right number.** Tg is still ~87 °C, not 60–65 °C.
  The real step at 55 °C is rejected by the symmetry gate
  (`_MIN_TG_SYMMETRY`), which exists to reject melting flanks and is what stops
  a melting peak being reported as a Tg. Its measuring window reaches down into
  the cold-crystallisation descent, so the post-transition slope is 12 times
  the pre-transition one and the gate refuses a real transition. Fixing that
  means changing the gate, which is the same class of change that broke
  detection on Tg-only traces in two earlier attempts (see item 4 above).

So the honest summary is that this defect is **half fixed**: the analysis no
longer states something physically impossible, and it still does not state the
right value. Those are different claims, and only the first is supported.

### 3.9 A file the analysis could not accept at all

Sections 3.1–3.8 concern analyses that ran and returned something wrong. This
one concerns files that could not be run: the trace modules took JSON with two
clean lists in the right units, and a researcher holding the instrument's own
export had nothing to put in them.

A NETZSCH DSC 204F1 Phoenix export shows why that is a real gap rather than an
inconvenience. The file is:

```
#SEPARATOR:SEMICOLON
#DECIMAL:POINT
#EXO:-1
#RANGE:-30°C/10,0(K/min)/200°C
#SAMPLE MASS /mg:4.98
#SAMPLE:1-90
##Temp./°C;Time/min;DSC/(mW/mg);Sensit./(uV/mW)
  9.33910; 91.00083;-8.719357e-02;3.42446
```

Four columns, and the **second is time, not the signal**. The signal is in
mW/mg, not W/g. The delimiter and the decimal mark are declared in the header.
The degree sign is latin-1, so `numpy.loadtxt` raises `UnicodeDecodeError` on
the file outright. `#EXO:-1` gives the sign convention. And the heating rate —
without which an enthalpy cannot be expressed in J/g — is inside `#RANGE`, as
`10,0(K/min)` with a **decimal comma**.

Reading this file as "first column x, second column y" does not fail. It
analyses the time axis, which runs from 91 to 114, as though it were a heat
flow in W/g, and returns numbers. The column's own amplitude is the give-away:
23 units of range against less than 2 for the real signal.

The tool now reads the file. It identifies each column's role from its label
and unit, converts to the canonical unit, and surfaces the header's metadata —
sample name, mass, heating rate, exothermic direction. Where a conversion
cannot be made honestly, it says so; an absolute signal in mW with no sample
mass on file is refused rather than divided by a guess. Two shapes of failure
that a naive reader produces were caught by the tests rather than by review:

* A column matcher that accepted short substrings (`"s"` for seconds) matched
  `DSC/(mW/mg)` and `Sensit./(uV/mW)` as *time*, because both contain an `s`.
  The y-axis came from the wrong column and nothing indicated it. Every token
  is now three characters or more, on the principle that in an instrument
  header a short abbreviation is always ambiguous, and not recognising is
  better than recognising wrongly.
* The cold-crystallisation finder from §3.8 and the melting-ramp detector both
  needed the sample density stated. A file sampling one point per degree cannot
  support a glass transition, because the step is narrower than the spacing.

That last point produced the decision worth recording. On the real LDPE file
the analysis returns Tm = 105.3 °C, inside the 105–115 °C range for LDPE, and a
crystallinity of 39.6 %. It also *wanted* to return Tg = 22.9 °C, which is
nonsense: LDPE's glass transition is near −110 °C and the scan begins at
−30 °C, so the transition is not in the file at all. The value was baseline
curvature from a 1-point-per-degree trace.

The first version of the endpoint returned that number and a warning beside it.
That is the failure mode this project keeps rediscovering: **a number travels,
a warning does not.** A caller reading `Tg` from the JSON sees a value; the
prose in a `notes` array is not part of the field. The field is now omitted
with the reason in `refusals`, which is the same rule already applied to a
crystallinity with no reference enthalpy. The rule generalises: when the tool
states that a quantity cannot be determined, it must not also report it.

### 3.10 A second door into the same analysis, and the three defects it opened

§3.9 added a reader for the instrument's text export. That left the tool with
two entrances to the same analysis: `read_trace_file` for delimited text, which
resolved column roles, converted units and checked coherence, and `read_tri`,
which decoded the TA Instruments binary container and did none of those things.
A researcher holding a `.tri` — the format the instrument actually writes, with
the text export being a secondary artefact — could decode the numbers but not
feed them to the analysis on the same terms.

Reducing the binary reader to the same `TraceFile` the text path produces
removes the distinction: one dispatch on file content chooses the reader, and
the analysis no longer knows which format it was handed. The work was small.
The defects it exposed were not, and all three were found by running the
unified path against the 116 real files of figshare 24462004 rather than by
review.

**The wrong channel, chosen silently.** Channel names were matched by substring
in file order. The file writes `Heat Flow A`, `Heat Flow B` and then `Heat
Flow`; the substring `heat flow` matches all three, so the reader elected
`Heat Flow A` — an auxiliary sensor — at index 11 instead of the instrument's
normalised `Heat Flow` at index 13. Temperature had the same shape, with six
channels (`Tzero`, `Reference`, `Junction`, `Flange`, `A`, `B`, `C`) eligible
under one spelling. Nothing in the output would have indicated that the
analysis ran on an auxiliary reading: the units are identical and the curve
looks plausible. Exact equality now precedes substring matching, and the
auxiliary channels are listed with no role at all, so they are visible in the
preview and ineligible for the analysis.

**A truncated heating rate.** The metadata block is latin-1, so the degree sign
arrives as the two-byte sequence `Â°`. The rate regex looks for `°?C/min`,
which does not match `Â°C/min`. The heating rate came back `None` on all 116
files — and a missing heating rate is not a cosmetic loss, it disables the
enthalpy normalisation in silence, so ΔHm and crystallinity would have been
reported as absent for reasons the caller could not see. Repairing the sequence
at the point of reading lets the same regex serve both formats.

**Binary content accepted as text.** `_decode` tried UTF-8 and fell back to
latin-1, which decodes *every* byte. A PNG, or any proprietary container, was
therefore read as text and returned a `TraceFile` whose "columns" were
invented from whatever byte runs happened to look numeric. The analysis then
ran on that. This is the worst shape of failure in this document — no error, no
warning, and output that is entirely artefact. Content that looks binary is now
refused, with the likely cause named, before any parsing is attempted.

The first of the three is the one worth dwelling on. It is the same defect as
§3.1 and §3.8 in a different costume: a plausible number produced from the
wrong input, with nothing in the output marking it as wrong. The 116-file set
caught it because one file's channel order differs from another's; a single
file, inspected by eye, would not have.

Test coverage: 11 new tests against a 1.3 MB trimmed fixture of a real
polystyrene run (header plus all 14 channels), pinning the format detection by
content rather than extension, the metadata recovery including the corrupted
degree sign, the election of canonical channels over auxiliary ones, and the
refusal of binary input. Backend suite at 369 passing.

### 3.11 A reader that was correct and never called

§3.9 built the instrument-file reader and §3.10 let it accept both formats. A
user then uploaded a NETZSCH DSC export and reported that the tool would not
show the two columns that matter — temperature in °C and heat flow in W/g —
suspecting it was taking the first two columns and no more.

The suspicion was exactly right, and the reader was not at fault. The file read
correctly through the API: roles, units, metadata and the sparse-sampling
warning all came back as designed. The panel, however, never called it. The
thermal panel parsed the upload **in the browser** with a helper that strips
the header and takes the first two numbers on each line:

```js
.filter((l) => !l.startsWith('#') && !l.startsWith('//'));   // header, discarded
const a = toNum(parts[0]);   // column 1
const b = toNum(parts[1]);   // column 2 — always
```

On this file the columns are `Temp./°C; Time/min; DSC/(mW/mg); Sensit./(uV/mW)`.
The second is **time**. So the trace that reached the analysis was temperature
against time, with the time axis read as a heat flow in W/g — the precise
failure §3.9 was written to prevent, arriving through the one door that had not
been repaired. Nothing failed: the box filled, the plot drew, the numbers came
out, and all of them described the wrong quantity.

The lesson is the narrowest one in this document and the most easily missed:
**fixing the layer that reads the data does not fix the layer that calls it.**
The tests passed because every test exercised the reader directly. No test
asserted that the panel's file route reaches the reader at all, so the wire
between them was untested while both of its ends were covered. Two frontend
tests did exist for this route, and both asserted the old behaviour — that the
panel rebuilds a two-column text from the first two numbers — which made a
defect look like a specification.

The file now goes to the server, which returns the resolved columns, and the
panel displays what was decided: the axes, the sample, the mass and the heating
rate, so a mis-read column is visible rather than implied by a plausible plot.
The resolved axis labels are also written back into the trace box, because a
pair of unnamed columns cannot be checked by anyone reading them later.

On the reporting file (LDPE, 168 points, 10 K/min) the trace now reads
`Temp./°C` against `DSC/(mW/mg)` and returns Tm = 107.4 °C, inside the
105–115 °C window for LDPE, with ΔHm = 111.2 J/g. The previous route fed the
analysis the time axis.


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
   transition at all. Four separate discriminators have now been attempted —
   a shape-symmetry gate, a width test, a step-versus-peak test, and a
   prominence-over-the-transition-width test — each of which passed its
   synthetic case and each of which failed on this set. The failure is
   quantifiable and is the reason the tool no longer presents transition
   temperatures as measurements: on these 116 traces the glass transition
   lands in the published window about **30 %** of the time, and the melting
   detector has reported a melting temperature for **amorphous polystyrene**,
   which has no melting transition. The three shape metrics were measured
   against the real set and none separates a melting endotherm from a glass
   transition:

   | Discriminator | Melting polymers | Amorphous polymers | Separates |
   |---|---|---|---|
   | Peak prominence, as a fraction of the trace range | 0.155–0.354 | 0.018–**0.378** | no — PS scores highest |
   | Return to the pre-event level | 0.710–1.382 | 0.236–**3.354** | no — the amorphous range contains the melting range |
   | Transition width | 12.8 °C | 14.0 °C | no |

   Amplitude and shape cannot do this, because a melting endotherm and a
   glass transition can have arbitrary and overlapping sizes. The conclusion
   recorded here is that identifying which transition is which is **not a
   threshold-calibration problem**, and that a fourth parameter sweep would
   have produced a fourth failure.

   One defect in this area *was* found and fixed (see §3.6): the melting peak
   was being located with `argmax(y − chord)`, which is degenerate whenever
   the curve lies below the chord and returned the temperature at the end of
   the programmed ramp on PLA, EVA, PET and PBT. That mode is eliminated —
   no trace now reports the ramp end as a melting temperature — but the
   overall hit rate on semicrystalline polymers is unchanged, and four traces
   now report a melting temperature that is not there.

   A *second* defect was found later and fixed (§3.8), and it is worth stating
   what it did and did not change. The glass-transition search could return a
   temperature **above the cold-crystallisation peak**, which is impossible:
   once the sample has crystallised, the amorphous phase that produces the
   step no longer exists. Two of the three literature PLLA traces had this.
   The ordering constraint removed the impossibility, and the three traces now
   report a physically possible Tg — but the value is still about 87 °C against
   a literature 60–65 °C, because the real step is rejected by the symmetry
   gate that exists to reject melting flanks. So this item **remains open**: the
   constraint made the answer possible, not correct.
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
7. **Stability is not accuracy.** The `Tg_reliable` flag measures whether the
   reported Tg moves when the trace is resampled. It therefore certifies
   *reproducibility of the computation*, not *correctness of the answer*: on
   PLA1-AR it reports the value as stable to 0.0 K while that value (156 °C)
   lies in the melting region and the polymer's Tg is roughly 60 °C lower. A
   consistently wrong answer is a stable one. Until a certified thermal
   reference is available, no footing computed from the sample's own trace can
   distinguish the two, and the field is labelled accordingly rather than
   presented as a trust signal.

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
.venv/bin/python -m pytest                    # 332 passed, 3 xfailed

cd ../frontend && npm ci
CI=true npx react-scripts test --watchAll=false   # 87 passed, 10 suites
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

The verification described here found eight defects that no amount of internally
consistent testing would have surfaced, established that the three
input-checking failures share a single cause, and leaves seven questions open.
Both outcomes are the point of doing it.

The sixth defect is the one that argues most strongly for the practice. Five of
the six were found by running data the implementation did not generate through
the tool. The sixth was found by running the *interface* — typing a polymer name
and reading what came back — after every automated gate was green. A test suite
can only assert the inputs someone thought to write down, and the absence of a
test for a name that must be refused is invisible in a passing suite.

The clearest lesson is about the cost of the last three. They were found only
because the analysis was made fourteen times faster first; at ninety minutes
per sweep, the polarity defect would have been characterised by three attempts
instead of the eight it took, and the third would have looked like the last
possible one.

A second lesson is about which comparison the tool makes. Comparing a measured
value against a published range has three possible outcomes, and a two-state
comparison forces a "disagrees with the literature" verdict whenever the honest
answer is "no comparison was made". `not_comparable`, with its reason stated,
is what keeps a missing reference from being reported as a disagreement.

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
11. D. Dean, *Differential Scanning Calorimetry*, University of Alabama at
    Birmingham. Slides 28 (cold crystallisation) and 29 (the ordered sequence
    of events in a DSC trace) are the basis of §3.8. Slide 11 distinguishes the
    first-order melting transition from the second-order glass transition, and
    slide 55 gives the ASTM D3418 midpoint construction this tool implements.
12. LDPE DSC trace, NETZSCH DSC 204F1 Phoenix export. Used as the instrument-
    file fixture in `backend/tests/fixtures/netzsch_dsc_ldpe.txt`. It is the
    case that motivates §3.9: four columns whose second is time, a declared
    delimiter and decimal mark, a latin-1 degree sign, `#EXO:-1` and the
    heating rate in `#RANGE`.

## Licence

MIT. Source: <https://github.com/teles-eliandro/polymer-analysis-toolkit>
