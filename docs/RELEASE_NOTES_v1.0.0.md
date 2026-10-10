# v1.0.0 — characterisation analysis that states its own limits

## What this release is

The first tagged release of the Polymer Analysis Toolkit (PAT), together with the
technical write-up ([`docs/README.md`](README.md)) that documents how every
result was verified and — at more length than is customary — **what could not be
verified**. This is the version of record; Zenodo archives it and mints the DOI
on the release webhook.

The paper's central finding is a failure pattern rather than an arithmetic error:
in every module tested, the analysis accepted an input that was not physically
what the code assumed, and returned a confident number instead of refusing. Those
defects are structurally invisible to internally consistent test data, because a
test suite generates data with the code's own assumptions.

## The defects, with their measured evidence

Seventeen defect records (§3.1–§3.17 of the paper). Three of them are what the
release exists to make checkable, because each produced a number that looks like
a result:

| Input accepted as-is | What it produced | What it should be |
|---|---|---|
| A heat-flow trace whose endotherm points **down** | The same melting point (−90.06 °C) for six chemically distinct polymers | Melting temperatures inside the literature window in **52 of 58** files, once polarity is read from the file's own `#EXO` declaration |
| A **transmittance** spectrum handed to an absorbance reader | 103 peaks from 3998 cm⁻¹; 1 of 58 spectra plausible | Absorbance recovers the four known polyethylene bands (2915, 2848, 1473, 730 cm⁻¹); **48 of 52** plausible |
| A peak **area in W/g·°C** reported as an enthalpy in J/g | 10.19 J/g and 11 % crystallinity | 61.17 J/g and 65.8 %, against the 61.7 J/g published for that file |

The third is the most dangerous of the three: 11 % crystallinity is an entirely
ordinary value for a semi-crystalline polymer, and nothing about it invites a
second look.

A negative-mass TGA residue (seven of 27 files, between −0.35 % and −1.41 %) is
reported unchanged, with a note saying it cannot be cited as a residue — rather
than rounded to zero, which would hide an instrument fault the analyst needs to
see.

## Retracted claim

Section 4, item 5 of the paper previously asserted that inverted signal polarity
corrupted the melting enthalpy by two orders of magnitude, naming 0.229 J/g.
**Neither half reproduced** against a real trace: the inference had selected a
crystallisation event, and the enthalpy was omitted rather than mis-scaled. The
entry is struck through as retracted and the real defect in that function is
recorded separately (§3.16). A separate repair that "fixed" it by running the
integral on the peak search's curve produced ΔHm 36.09 J/g and 39 % crystallinity
— computed at a crystallisation peak. It was reverted.

## What is held open

Seven items in §4, recorded in the suite as `xfail(strict=True)` so an unexpected
pass **fails the build** and forces the claim to be revisited. The largest: of
107 traces, **71 report a glass transition outside its literature window**, and
four separate discriminators have failed to separate a melting endotherm from a
glass transition by shape alone. The conclusion recorded is that this is not a
threshold-calibration problem.

Agreement with a **certified** reference is not demonstrated and is not claimed.

## Suite

- **436 backend tests passing**, 3 xfailed (strict), lint clean
- **95 frontend tests passing** across 11 suites
- CI green on Python 3.11 and 3.12

## Contents

Five modules behind one interface: molar mass (GPC/SEC), thermal (DSC/TGA),
mechanical (tensile), rheology (frequency sweep), structure (XRD/FTIR). English,
Portuguese and Spanish. Backend Python 3.11 / FastAPI; frontend React 18.

Live: <https://polymer-analysis-toolkit.vercel.app> (free-tier API — the first
request after an idle period takes ~30–60 s to wake).

## Licence and authorship

**MIT** — see [`LICENSE`](../LICENSE). Copyright © 2026 Eliandro P. Teles.

Author: **Eliandro P. Teles**, with no institutional affiliation declared — the
work was produced outside any current appointment or enrolment.

AI assistance is **declared and credited, not listed as an author** (neither
arXiv nor COPE permits AI authorship). The implementation, the verification runs
and the drafting were carried out with Hermes Agent (Nous Research) used as a
tool under the author's direction and verification. Full statement, including the
one hypothesis of the assistant's that the data refuted, in
[`AUTHORSHIP.md`](../AUTHORSHIP.md).

## Citing

See [`CITATION.cff`](../CITATION.cff) (validates against CFF schema 1.2.0) or
[`.zenodo.json`](../.zenodo.json). Once Zenodo has archived this release, the
DOI is the identifier to cite; until then, cite the repository URL and the
`v1.0.0` tag.
