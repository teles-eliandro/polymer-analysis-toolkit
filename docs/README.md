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

---

## 3. Two defects found only by external data

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

### 3.3 Why this matters beyond these two bugs

Both defects share a shape: **the code was internally consistent and
externally wrong.** In the first case the value was not representable in the
output format; in the second the value was representable, computed correctly,
and meaningless. Neither was reachable from data generated by the same
assumptions as the implementation.

The practical rule: an *impossible* value — crystallinity above 100 %,
dispersity below 1, an enthalpy exceeding that of a fully crystalline sample,
a non-finite number in a response — is a signal about the model or the
baseline, not a rounding artefact to be tolerated. Such bounds deserve explicit
assertions so they cannot pass silently.

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

Accordingly: the mathematics is verified against exact cases, and agreement
with instrument-reported values is **4.9 % median in Mw** over the samples
where comparison is meaningful. Agreement with a *certified* value is **not**
demonstrated, and is not claimed.

---

## 5. Reproduction

```bash
git clone https://github.com/teles-eliandro/polymer-analysis-toolkit
cd polymer-analysis-toolkit
python scripts/fetch_reference_data.py        # downloads the sources above

cd backend && python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest                    # 154 passed, 3 xfailed

cd ../frontend && npm ci
CI=true npx react-scripts test --watchAll=false   # 7 passed
```

The reference data is deliberately **not** committed: it carries its own
licence and runs to tens of megabytes. Tests that need it skip cleanly when it
is absent, naming the script that fetches it.

Ready-to-use extracts of the real data — five WAXS patterns converted to 2θ,
three PLLA second-heating DSC traces, with the conversions and the expected
results documented — are described in `pat-test-data/README.md`.

---

## 6. Conclusion

A characterisation tool earns its keep by being wrong in ways its user can
detect. Three choices follow from that: report a quantity only when its
inputs are available (Mv needs $a$; Xc needs ΔH°m; the crystallinity index
needs an amorphous reference); state the method and its limits beside every
number, including when the answer is "not determined"; and verify against data
the implementation did not generate.

The verification described here found two defects that no amount of internally
consistent testing would have surfaced, and it leaves three questions open.
Both outcomes are the point of doing it.

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

## Licence

MIT. Source: <https://github.com/teles-eliandro/polymer-analysis-toolkit>
