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
cd backend  && .venv/bin/python -m pytest     # 149 passed, 3 xfailed
cd frontend && CI=true npx react-scripts test --watchAll=false   # 7 passed
```

Backend tests cover the API contract (JSON and multipart paths), each module's
maths against synthetic cases with known answers, and the published-data checks
described above. Frontend tests mount the real shell in jsdom, switch through
the modules, and confirm that a result renders.

---

## 🛠️ Stack

- **Backend** — Python 3.11, FastAPI, Pydantic, NumPy, pandas. Deployed on Render
  (`render.yaml`; start command `cd backend && uvicorn app.main:app`).
- **Frontend** — React 18 (Create React App), Plotly via `react-plotly.js`,
  axios. Deployed on Vercel.
- **CI** — GitHub Actions: ruff, pytest on Python 3.11 and 3.12, frontend build.

---

## 📄 Licence

MIT.

Developed by **Eliandro P. Teles**.
