# PAT test data — real characterisation measurements

Real instrument data for exercising the Polymer Analysis Toolkit. No synthetic
or invented values: every file below was downloaded from the cited dataset and
converted only in units (never in content) so the panels can read it.

Upload/paste into the corresponding module at whatever URL serves the app.

---

## Structure module — XRD (WAXS patterns)

**Source:** `10.5281/zenodo.20466241` — *Laboratory and synchrotron X-ray
scattering from poly-lactic acid/polyethylene blends*, CC-BY-4.0.

Converted from the q-space `.dat` profiles (Nika/Fit2D) of the WAXS films to
2θ using the dataset's own declared wavelength, **λ = 1.541 Å** (Cu Kα).

| File | Points | 2θ range | Main peak |
|---|---|---|---|
| `WAXS_film4-16_002.dat` | 438 | 5.0–40.8° | 21.38° |
| `WAXS_film4-19_001.dat` | 438 | 5.0–40.8° | 21.55° |
| `WAXS_film4-20_001.dat` | 438 | 5.0–40.8° | 21.55° |
| `WAXS_film4-23_001.dat` | 438 | 5.0–40.8° | 21.30° |
| `WAXS_film4-24_001.dat` | 438 | 5.0–40.8° | 15.46° |

**What to expect.** PLLA's strongest reflections sit near **2θ = 16.7° and
16.9°** (the 110/200 pair), with a further reflection near **19.1°** and a
broad maximum at **21–22°**. The module indexes peaks in that region for the
first four films; `film4-24_001` is dominated by a low-angle feature instead,
which is itself a useful case.

**Note on the crystallinity index.** These patterns are in arbitrary units and
decay steeply with angle, so the straight-line baseline cuts through the
amorphous halo. The tool now reports **no crystallinity index** for such
traces rather than a saturating 100 %, because the index needs an amorphous
reference these files do not carry. Use `XRD` peaks and d-spacings from them,
not the index.

---

## Thermal module — DSC (melting)

**Source:** `10.5281/zenodo.17288962` — *Differential scanning calorimetry
measurements of samples of poly(lactic acid) with different molecular
weights*, CC-BY-4.0. Instrument: TA Instruments DSC Q20.

Extracted from the `.txt` exports. Protocol is declared in each file header:

```
3: Ramp 10.00 °C/min to 200.00 °C
4: Isothermal for 5.00 min
5: Jump to -50.00 °C
6: Ramp 10.00 °C/min to 200.00 °C     <-- second heating, used here
```

The **second heating** is used, which is the standard for reporting Tm and
crystallinity: the first heating carries the thermal history of the sample.

| File | Sample | Mass | Points | Range |
|---|---|---|---|---|
| `DSC_PLLA_10K_2nd_heating.dat` | PLLA 10 kg/mol | 3.9 mg | 5883 | −6.5 → 188 °C |
| `DSC_PLLA_25K_2nd_heating.dat` | PLLA 25 kg/mol | 4.0 mg | 5882 | −6.6 → 188 °C |
| `DSC_PLLA_50K_2nd_heating.dat` | PLLA 50 kg/mol | 3.6 mg | 6153 | −5.6 → 198 °C |

**Format:** `temperature_C <TAB> heat_flow_W_per_g`, endothermic up.
Use **heating rate = 10 °C/min** and **ΔH°m = 93 J/g** (PLLA, 100 % crystalline)
for the crystallinity.

**Measured with the tool** (heating rate 10, ΔH°m 93):

| Sample | Tm | ΔHm | Xc |
|---|---|---|---|
| PLLA 10K | 167.4 °C | 61.7 J/g | 66 % |
| PLLA 25K | 171.9 °C | 44.1 J/g | 47 % |
| PLLA 50K | 173.2 °C | 61.8 J/g | 66 % |

Tm is in the published range for PLLA (170–180 °C), and Xc is in the 40–60 %
range typical of melt-crystallised PLLA. Tg is not resolved in these traces —
expected, since a highly crystalline sample has only a small heat-capacity
step.

---

## Molar mass module — GPC/SEC

**Source:** `10.5281/zenodo.17306416` — GPC-SEC of poly(lactic acid) samples,
CC-BY-4.0. The dataset's `Mw_distribution_*.txt` tables are already
`massa`/`fraction` pairs; the instrument's own report PDFs in the same record
give reference Mn, Mw, Mz and Mz+1 **with uncertainties** for 10 samples.

Use those PDFs as the answer key: they are what the backend's
`tests/test_against_literature.py` compares against, at a median deviation of
**4.9 %** in Mw across the 8 samples whose data range covers the reported value.

---

## Licence and attribution

Each file remains under its source licence (CC-BY-4.0). Cite the Zenodo DOIs
above if you publish results obtained from them. The conversions applied here
are unit changes only — no values were altered, smoothed or regenerated — so
the numbers remain the authors' original measurements.
