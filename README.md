# Polymer Analysis Toolkit (PAT)

[![Démo en ligne](https://img.shields.io/badge/Démo-Vercel-000000?logo=vercel)](https://polymer-analysis-toolkit.vercel.app)
[![Licence](https://img.shields.io/badge/Licence-MIT-blue)](LICENSE)
[![CI](https://github.com/teles-eliandro/polymer-analysis-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/teles-eliandro/polymer-analysis-toolkit/actions/workflows/ci.yml)

**Polymer Analysis Toolkit (PAT)** is an open-source web application that helps
researchers, engineers and students in materials science analyse the
characterisation data they already collect — without writing any code.

Five modules share one interface:

| Module | Input | What it reports |
|---|---|---|
| **Molar mass** | GPC/SEC export or a distribution table | Mn, Mw, Mz, Mz+1, Đ, Mv |
| **Thermal** | TGA or DSC trace | Td, residue, DTG peak; Tg, Tm, ΔHm, crystallinity |
| **Mechanical** | Tensile stress–strain curve | E, yield, tensile strength, elongation, toughness |
| **Rheology** | Frequency sweep (ω, G′, G″) | Crossover, plateau modulus, terminal slopes, gel test |
| **Structure** | XRD pattern or FTIR spectrum | Peak indexing, d-spacings, crystallite size; band assignments |

The interface is available in **English, Portuguese and Spanish**; the language
is chosen in the header and remembered in the browser.

---

## 🔬 Theoretical basis

### Molecular averages

Weight fractions `w_i` are the experimental convention in GPC/SEC raw data, and
the module assumes them.

$$M_n = \frac{1}{\sum_i \left( w_i / M_i \right)} \qquad M_w = \sum_i w_i M_i \qquad Đ = \frac{M_w}{M_n}$$

Higher moments follow the same weighting: `Mz = Σw_iM_i² / Σw_iM_i` and
`Mz+1 = Σw_iM_i³ / Σw_iM_i²`. The viscosity average `Mv` needs the
Mark–Houwink exponent `a` of the polymer–solvent pair; it is reported only when
that exponent is supplied, because assuming one silently produces a wrong number.

### Method notes the interface states plainly

- **Crystallinity from DSC** requires a reference enthalpy ΔH°m for a 100 %
  crystalline sample. It is reported only when that value is given.
- **Crystallite size from XRD** uses the Scherrer equation. The peak width is
  converted to radians and instrumental broadening is removed in quadrature;
  the shape factor K (default 0.9) is an input, not a hidden constant.
- **The XRD crystallinity index is not an absolute degree of crystallinity.**
  It is comparable only between samples measured with the same range, baseline
  and slits. The interface says so next to the number.
- **FTIR assignment is a functional-group lookup, not an identification.**
  Many polymers share the same groups, and additives and moisture contribute
  their own bands.

---

## 📊 Verification against published values
The maths is checked against real, citable data — not only against internal
consistency. Sources are downloaded by `scripts/fetch_reference_data.py`:

| Source | Used for |
|---|---|
| [NIST IR 6091](https://doi.org/10.6028/nist.ir.6091) (open access) | Certified **Mw of SRM 706a** polystyrene, with its uncertainty |
| [Zenodo 10.5281/zenodo.17306416](https://doi.org/10.5281/zenodo.17306416) (CC-BY-4.0) | GPC/SEC of PLA in THF — 10 samples with Mn, Mw, Mz, Mz+1 and the instrument's own uncertainties |
| [Zenodo 10.5281/zenodo.17293641](https://doi.org/10.5281/zenodo.17293641) (CC-BY-4.0) | DSC of polycaprolactone, with its stated protocol |

Reference files live in `.reference-data/`, which is **not** versioned (some are
several MB and carry their own licences). Download them with:

```bash
python scripts/fetch_reference_data.py          # everything
python scripts/fetch_reference_data.py --dsc    # only the DSC set
```

Tests that need those files **skip** cleanly when they are absent, so a fresh
clone runs green without them.

**What the tests establish, and what they do not.** Values reported by the
instrument are checked against the module only after an internal-consistency
gate: the published Mn/Mw/Mz/Mz+1 must be correctly ordered, and the published
ratios Mw/Mn and Mz/Mn must reproduce from the published moments. Ten of ten
sources passed that gate. On the eight samples whose tabulated range actually
contains the reported value, the median deviation in Mw is **4.9 %**. Two
samples are excluded by an explicit coverage rule applied before the results
were inspected — their data range does not contain the reported value, so
comparing against it would be meaningless.

Cases that could not be verified are recorded as `xfail(strict=True)`: the
build fails if one of them ever starts passing, which forces the claim to be
revisited rather than quietly upgraded. Three are open — reproducing the
*certified* NIST Mw (the certificate publishes only Mw, not the slice
distribution), obtaining an independent Mv (needs a Mark–Houwink pair *and* a
measured intrinsic viscosity from the same sample), and resolving the Tg of the
semi-crystalline PCL sample (~55 % crystallinity leaves a small Cp step).

### Ready-to-use real data

`exemples/literature/` holds extracts of the real measurements, converted only
in units so the panels can read them — no values altered, smoothed or
regenerated:

| Files | Module | What it is |
|---|---|---|
| `WAXS_film4-*.dat` | Structure → XRD | 5 WAXS patterns of PLA/PE films, in 2θ with λ = 1.541 Å |
| `DSC_PLLA_*K_2nd_heating.dat` | Thermal → DSC | 3 PLLA second-heating scans at 10 °C/min |

Paste a file's contents into the matching panel and compare against the
documented expectations in `exemples/literature/README.md`. Two of these files
are what exposed both bugs described above, so they make a good first check
that a deployment is working.

---

## 🎯 What this tool is reliable for, and what it is not

PAT does two different kinds of work, and they do not deserve the same trust.
The interface says which is which, per number.

### Reliable — the tool does this and you can depend on it

| Capability | Why it is dependable |
|---|---|
| **Reading instrument files** | TA Instruments `.tri` binary is decoded channel-by-channel and verified: all 14 channels of a real trace agree with each other and the recovered temperature reproduces the programmed method (116/116 files on the figshare 24462004 set). |
| **Plotting the data** | A deterministic transform of the input. Nothing is smoothed, resampled or regenerated behind your back. |
| **Reporting what the file says** | Sample mass, pan type, operator, the programmed method, the acquisition rate — read from the file, not inferred. |
| **Published formulas over declared inputs** | Molar-mass averages, Mark–Houwink, Scherrer, enthalpy integration, crystallinity from a reference enthalpy. Cite the formula and the bounds and you reproduce the number. |

### Suggested — the tool infers this, and you should check it

**Identifying which transition is which** is an inference from the shape of the
trace, and on real data it is wrong often enough that it is never presented as
a measurement.

This is measured, not a hedge. On the 116 real DSC traces of the figshare
24462004 set, the reported glass transition lands inside the published window
for its polymer on roughly **30 %** of files. The detector has reported a
melting temperature for **amorphous polystyrene**, which has no melting
transition at all. Three independent shape discriminators were tested against
that set — peak prominence, return-to-baseline, and transition width — and
none separates a melting endotherm from a glass transition, because the two
events can have arbitrary and overlapping sizes.

### How the interface says so

Each reported value carries a confidence rung and the evidence behind it:

```
read       a property of the input file, or a deterministic transform
formula    a published formula over a declared input; reproducible
suggested  an inference from the trace shape; can be wrong
```

Transition temperatures are **always** `suggested`. An enthalpy is `formula`
over a `suggested` peak, which is what makes it only as good as the peak
identification — and the claim says so.

A suggested transition is shown with the observations that produced it, so you
can judge the inference rather than trust it:

```
Tm = 151.2 °C   [suggested]
  · endothermic excursion that returns to the local baseline
  · ΔHm = 34.2 J/g over the fitted baseline
  ⚠ Confirm against the expected Tm for this polymer before quoting it.
```

**A limitation worth knowing.** The `Tg_reliable` flag measures whether the
reported Tg is *stable* under resampling of the trace — not whether it is
*correct*. A consistently wrong answer is a stable one: on the PLA trace the
flag reports "moves 0.0 K" while the value sits in the melting region and the
polymer's real Tg is ~60 °C lower. Stability is not accuracy, and the flag is
labelled as what it is.

---

## 🚀 Running locally

### Backend

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

API documentation is served at `/docs`.

### Frontend

```bash
cd frontend
npm install
REACT_APP_API_URL=http://localhost:8000 npm start
```

`REACT_APP_API_URL` is read **at build time**. If it is not set in production
the app falls back to `http://localhost:8000` — the visitor's own machine — and
logs a warning to the console. Always set it in the hosting environment.

---

## ✅ Tests

```bash
cd backend  && .venv/bin/python -m pytest     # 332 passed, 3 xfailed
cd frontend && CI=true npx react-scripts test --watchAll=false   # 87 passed, 10 suites
```

Backend tests cover the API contract (JSON and multipart paths), each module's
maths against synthetic cases with known answers, and the published-data checks
described above. Frontend tests mount the real shell in jsdom, switch through
the modules, and confirm that a result renders.

Two suites are worth naming because they guard against failures a passing suite
otherwise hides. `test_reference_repertoire.py` asserts **48 real instrument
names that must resolve and 31 wrong identifications that must be refused**, so
adding an alias cannot silently shadow an existing one. `test_confidence_claims.py`
asserts that every reported field carries its confidence rung, so a value cannot
be added without stating what it is worth.

---

## 🛠️ Stack

- **Backend** — Python 3.11, FastAPI, Pydantic, NumPy, pandas. Deployed on Render
  (`render.yaml`; start command `cd backend && uvicorn app.main:app`).
- **Frontend** — React 18 (Create React App), Plotly via `react-plotly.js`,
  axios. Deployed on Vercel.
- **CI** — GitHub Actions: ruff, pytest on Python 3.11 and 3.12, frontend build.

### Vercel project settings

`package.json` lives in `frontend/`, so the Vercel project must be configured
with **Root Directory = `frontend`**. With the default (repository root) the
install step runs at the root, finds no `package.json`, and every deployment
fails before it produces a build — including preview builds, which is easy to
miss because the GitHub Actions checks still pass.

Two environment variables are needed:

| Variable | Value |
| --- | --- |
| `REACT_APP_API_URL` | The deployed API origin, e.g. `https://polymer-analysis-toolkit.onrender.com` |
| `CI` | `false` — Create React App treats warnings as errors when `CI=true` |

Check that the deployed bundle points at the right API:

```bash
curl -s https://<your-app>.vercel.app/static/js/main.*.js \
  | grep -o "https://[a-zA-Z0-9.-]*\.onrender\.com" | sort -u
```

---

## 📄 Licence

MIT.

Developed by **Eliandro P. Teles**.
