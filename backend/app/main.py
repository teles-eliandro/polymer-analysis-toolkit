"""Polymer Analysis Toolkit (PAT) API application."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.characterization import router as characterization_router
from app.api.v1.molecular import router as molecular_router
from app.api.v1.thermal import router as thermal_router

DESCRIPTION = """
Open-source toolkit for polymer characterisation. Every calculation states its
method, its units and its assumptions, and the API returns the intermediate
decisions it made so a result can be checked rather than trusted.

**Modules**

* **Molecular** - Mn, Mw, Mz, Mz+1, dispersity and viscosity-average molar mass
  from a molar-mass distribution, read from a JSON body or from a delimited
  file export in any of the conventions that SEC/GPC instruments produce.
* **Thermal** - TGA (Td at 5 % and 10 %, DTG peak, residue, decomposition
  steps) and DSC (Tg by ASTM D3418, Tm, enthalpies, crystallinity).
* **Mechanical** - Young's modulus, yield, tensile strength, elongation and
  toughness from an engineering stress-strain curve.
* **Rheology** - crossover, plateau modulus, terminal slopes, zero-shear
  viscosity and the Winter-Chambon gel test from a frequency sweep.
* **Structure** - XRD peak indexing, d-spacings and Scherrer crystallite size;
  FTIR band matching against a functional-group reference table.

**What this toolkit does not do**

It does not identify an unknown material, and it does not replace the
instrument software or the standards. Every endpoint documents which standard
or literature source its method comes from, and the limits of what the number
means. Where a method can only give a relative quantity - the crystallinity
index, the FTIR band assignments - the response says so explicitly.
"""

app = FastAPI(
    title="Polymer Analysis Toolkit (PAT) API",
    version="1.0.0",
    description=DESCRIPTION,
    contact={"name": "Polymer Analysis Toolkit", "url": "https://github.com/teles-eliandro/polymer-analysis-toolkit"},
    license_info={"name": "MIT", "url": "https://github.com/teles-eliandro/polymer-analysis-toolkit/blob/main/LICENSE"},
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# A production single-page app deployed on Vercel gets a *different* origin on
# every preview deployment, so a fixed allow-list breaks previews. The origins
# are read from the environment so the deployed frontend URL can be set
# without a code change, and a regex covers Vercel preview subdomains.
#
# allow_credentials is False on purpose: this API is stateless and
# unauthenticated, so no cookies are needed and turning credentials off
# removes the risk of reflecting an arbitrary Origin with credentials
# attached.
_default_origins = (
    "http://localhost:3000,http://127.0.0.1:3000,"
    "https://polymer-analysis-toolkit.vercel.app"
)
_origins = [
    o.strip()
    for o in os.getenv("PAT_ALLOWED_ORIGINS", _default_origins).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    # Vercel preview deployments: https://<project>-<hash>-<scope>.vercel.app
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(molecular_router, prefix="/api/v1")
app.include_router(thermal_router, prefix="/api/v1")
app.include_router(characterization_router, prefix="/api/v1")


@app.get("/", tags=["Health"], summary="Service banner")
def root() -> dict:
    return {
        "service": "Polymer Analysis Toolkit (PAT) API",
        "version": app.version,
        "docs": "/docs",
        "modules": ["molecular", "thermal", "mechanical", "rheology", "structure"],
    }


@app.get("/health", tags=["Health"], summary="Health check")
def health() -> dict:
    return {"status": "ok", "version": app.version}
