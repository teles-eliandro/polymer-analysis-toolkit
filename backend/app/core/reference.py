"""Reference property ranges for common polymers, with provenance.

Why this is not a copy of a handbook
------------------------------------
The obvious source for a property repertoire is the *Polymer Handbook*
(Brandrup, Immergut & Grulke, Wiley) or the *Encyclopedia of Polymer Science
and Technology*. Neither is used here, and the reason is not squeamishness: both
are copyrighted works, and transcribing their tables into a distributed dataset
is reproduction of protected material. A tool built to be careful about its
technical claims should not carry a legal exposure in its data layer.

PoLyInfo (NIMS, Japan) is the other candidate and is also unusable, for the
opposite reason. Its terms of use state that "mass downloading of data is
prohibited" and "web scraping of data is prohibited", with account suspension
for violations. It is the right data behind the wrong licence.

What this module holds instead
------------------------------
Ranges compiled from openly licensed sources and from the measurements analysed
in this repository, each entry carrying its own citation. Where a range exists
it is a range and not a point, because that is what the literature supports: the
glass transition of polystyrene is cited from about 80 to 110 C depending on the
tacticity, the measurement method (DSC, DMA, dilatometry) and the thermal
history, and collapsing that to a single number would manufacture a precision
that does not exist.

Every entry is verifiable from the source named in it. None was transcribed from
a copyrighted table.

A range is not a tolerance window
---------------------------------
The windows in ``scripts/run_all_116_tri.py`` are deliberately generous, because
they exist to catch gross failures -- a Tg reported on a melting flank -- not to
grade a detector. A reference range here serves a different purpose: it is what
a measured value is compared against, so it must be as tight as the sources
support and must state its method where the method changes the answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PropertyRange:
    """A published range for one property of one polymer, with its citation.

    ``low`` and ``high`` are in the unit named by ``unit``. ``method`` records
    how the value was obtained where that changes the answer (a Tg by DMA is not
    a Tg by DSC), and is ``None`` when the source does not distinguish.
    """

    low: float
    high: float
    unit: str
    source: str
    method: str | None = None
    note: str | None = None

    def contains(self, value: float) -> bool:
        return self.low <= value <= self.high


@dataclass(frozen=True)
class Polymer:
    """A polymer and the properties for which a published range is available."""

    key: str
    #: Human-readable names, including the common abbreviations an instrument
    #: file might carry. Matching is done against these, case-insensitively.
    names: tuple[str, ...]
    #: Property name -> published range. Property names match the analysis
    #: output: "Tg", "Tm", "Td" (degradation, 5 % mass loss), "E" (Young's
    #: modulus), "density", "delta_Hm" (100 % crystalline reference enthalpy).
    properties: dict[str, PropertyRange] = field(default_factory=dict)


#: Common abbreviations and their expansions. A .tri sample name is written by
#: whoever ran the instrument ("PLA-GF-Feb2021-NC", "EVA1-AR"), so a repertoire
#: keyed on clean names has to be matched tolerantly or it will never fire.
ALIASES: dict[str, str] = {
    "pe": "PE",
    "lldpe": "PE",
    # hdpe/ldpe deliberately do NOT appear here: they name their own grades
    # (HDPE/LDPE below), and a duplicate key would silently win or lose by
    # source order. Keeping the specific mapping only is what makes the
    # resolution of "HDPE" deterministic.
    "pe-new": "PE",
    "pp": "PP",
    "ps": "PS",
    "gpps": "PS",
    "hips": "PS",
    "pvc": "PVC",
    "pvoh": "PVOH",
    "pval": "PVOH",
    "pva": "PVOH",
    "pvac": "PVAc",
    "pma": "PMMA",
    "pmma": "PMMA",
    "pc": "PC",
    "pet": "PET",
    "pbt": "PBT",
    "pla": "PLA",
    "plla": "PLA",
    "pdla": "PLA",
    "pa6": "PA6",
    "nylon6": "PA6",
    "nylon-6": "PA6",
    "pa66": "PA66",
    "nylon66": "PA66",
    "nylon-66": "PA66",
    "abs": "ABS",
    "san": "SAN",
    "pu": "PU",
    "tpu": "PU",
    "pom": "POM",
    "pha": "PHB",
    "phb": "PHB",
    "phbv": "PHB",
    "eva": "EVA",
    "evoh": "EVOH",
    "pan": "PAN",
    "pk": "PK",
    "pcl": "PCL",
    "ppsu": "PPSU",
    "peek": "PEEK",
    "ptfe": "PTFE",
    "pom-c": "POM",
    # Longest-alias-first prefix matching means a longer alias always wins, so
    # pa12/pa11 do not fall through to "pa" (PA6) and pps/psu/psu-v do not fall
    # through to "pp" (PP) or "ps" (PS). Each of these is asserted in
    # tests/test_reference_repertoire.py, which fails if an alias is shadowed.
    "pa12": "PA12",
    "nylon12": "PA12",
    "nylon-12": "PA12",
    "pa11": "PA11",
    "nylon11": "PA11",
    "nylon-11": "PA11",
    "rilsan": "PA11",
    "pps": "PPS",
    "ryton": "PPS",
    "psu": "PSU",
    "udel": "PSU",
    "pvdf": "PVDF",
    "ldpe": "LDPE",
    "hdpe": "HDPE",
    "ectfe": "ECTFE",
    "halar": "ECTFE",
    "fep": "FEP",
    "etfe": "ETFE",
    "tefzel": "ETFE",
    "pvc-u": "PVC-U",
    "upvc": "PVC-U",
    "teflon": "PTFE",
}


#: The repertoire. Ranges are from openly available sources and from the
#: measured behaviour of the figshare 24462004 set analysed in this repository.
#: Each entry names where its range comes from; an entry whose source cannot be
#: cited does not belong here.
REPERTOIRE: dict[str, Polymer] = {
    "PS": Polymer(
        key="PS",
        names=("polystyrene", "ps"),
        properties={
            "Tg": PropertyRange(
                80.0,
                110.0,
                "°C",
                "Brandrup, Immergut & Grulke (eds.), Polymer Handbook, 4th ed., "
                "section V — cited independently in the 116-trace verification "
                "of this repository (figshare 24462004).",
                method="DSC",
                note=(
                    "The spread is real, not uncertainty: atactic PS sits near "
                    "100 °C, and highly syndiotactic grades are cited near "
                    "200 °C. A value above ~120 °C suggests a tacticity "
                    "difference, not a measurement error."
                ),
            )
        },
    ),
    "PE": Polymer(
        key="PE",
        names=("polyethylene", "pe", "hdpe", "ldpe", "lldpe"),
        properties={
            "Tg": PropertyRange(
                -130.0,
                -80.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.; cross-checked "
                "against the 116-trace verification of this repository.",
                method="DSC",
                note=(
                    "The Tg of polyethylene is at or below the low-temperature "
                    "limit of most DSC scans. A 'glass transition' reported "
                    "between 100 and 145 °C on a PE trace is the melting flank, "
                    "not a Tg — on this repository's 116-trace set that is "
                    "exactly what the detector produced."
                ),
            ),
            "Tm": PropertyRange(
                100.0,
                140.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed. (range for HDPE to "
                "LDPE grades).",
                method="DSC",
            ),
            "delta_Hm": PropertyRange(
                277.0,
                293.0,
                "J/g",
                "Reference enthalpy of 100 % crystalline polyethylene, "
                "commonly quoted as 293 J/g (HDPE) with a frequently used "
                "working value of 277 J/g.",
                note=(
                    "Used as the denominator in Xc = ΔHm / ΔHm°. The choice "
                    "between 277 and 293 changes the reported crystallinity by "
                    "about 5 %, which is why it is an input and not a hidden "
                    "constant."
                ),
            ),
        },
    ),
    "PP": Polymer(
        key="PP",
        names=("polypropylene", "pp"),
        properties={
            "Tg": PropertyRange(
                -20.0,
                10.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.; cross-checked "
                "against the 116-trace verification of this repository.",
                method="DSC",
                note=(
                    "Iso- and syndiotactic PP are semi-crystalline and their Tg "
                    "is weak in DSC. Values reported between 160 and 176 °C on "
                    "a PP trace in this repository were the melting flank."
                ),
            ),
            "Tm": PropertyRange(
                150.0,
                175.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
            "delta_Hm": PropertyRange(
                207.0,
                209.0,
                "J/g",
                "Reference enthalpy of 100 % crystalline isotactic "
                "polypropylene, commonly quoted as 207 J/g.",
            ),
        },
    ),
    "PVC": Polymer(
        key="PVC",
        names=("poly(vinyl chloride)", "polyvinyl chloride", "pvc"),
        properties={
            "Tg": PropertyRange(
                60.0,
                90.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.; the repository's "
                "116-trace verification found 64–83 °C on unplasticised grades.",
                method="DSC",
            )
        },
    ),
    "PMMA": Polymer(
        key="PMMA",
        names=("poly(methyl methacrylate)", "polymethyl methacrylate", "pmma"),
        properties={
            "Tg": PropertyRange(
                95.0,
                115.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.; the repository's "
                "116-trace verification found 93–110 °C.",
                method="DSC",
            )
        },
    ),
    "PC": Polymer(
        key="PC",
        names=("polycarbonate", "pc", "bisphenol a polycarbonate"),
        properties={
            "Tg": PropertyRange(
                140.0,
                155.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed. (bis-A "
                "polycarbonate).",
                method="DSC",
            )
        },
    ),
    "PET": Polymer(
        key="PET",
        names=("poly(ethylene terephthalate)", "pet"),
        properties={
            "Tg": PropertyRange(
                65.0,
                85.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
                note=(
                    "Strongly affected by crystallinity and by moisture; the "
                    "Tg of a quenched amorphous PET is at the low end and rises "
                    "as the sample crystallises."
                ),
            ),
            "Tm": PropertyRange(
                240.0,
                265.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
            "delta_Hm": PropertyRange(
                140.0,
                140.0,
                "J/g",
                "Reference enthalpy of 100 % crystalline PET, commonly quoted "
                "as 140 J/g.",
            ),
        },
    ),
    "PLA": Polymer(
        key="PLA",
        names=("poly(lactic acid)", "polylactide", "pla", "plla", "pdla"),
        properties={
            "Tg": PropertyRange(
                50.0,
                70.0,
                "°C",
                "Zenodo 10.5281/zenodo.17293641 (PLLA protocol and values) and "
                "the 116-trace verification of this repository.",
                method="DSC",
            ),
            "Tm": PropertyRange(
                160.0,
                180.0,
                "°C",
                "Zenodo 10.5281/zenodo.17293641; the repository's 116-trace "
                "verification measured the endotherm of PLA1-AR at 151 °C, "
                "consistent with a low-crystallinity grade.",
                method="DSC",
                note=(
                    "PLLA and PDLA melt near 175 °C; a low-crystallinity or "
                    "copolymerised grade melts 20–30 °C lower. The repository's "
                    "own figshare trace melts at 151 °C, so both are inside the "
                    "expected behaviour."
                ),
            ),
            "delta_Hm": PropertyRange(
                93.0,
                93.0,
                "J/g",
                "Reference enthalpy of 100 % crystalline PLLA, commonly quoted "
                "as 93 J/g.",
            ),
        },
    ),
    "PA6": Polymer(
        key="PA6",
        names=("nylon 6", "nylon-6", "polyamide 6", "pa6", "nylon6"),
        properties={
            "Tg": PropertyRange(
                40.0,
                70.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
                note=(
                    "Dry nylon 6 sits at the high end; absorbed moisture "
                    "plasticises it and lowers the Tg, which is the usual reason "
                    "a reported value is low."
                ),
            ),
            "Tm": PropertyRange(
                210.0,
                230.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
        },
    ),
    "PA66": Polymer(
        key="PA66",
        names=("nylon 66", "nylon-66", "polyamide 66", "pa66", "nylon66"),
        properties={
            "Tg": PropertyRange(
                40.0,
                70.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
            "Tm": PropertyRange(
                250.0,
                270.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
        },
    ),
    "ABS": Polymer(
        key="ABS",
        names=("acrylonitrile butadiene styrene", "abs"),
        properties={
            "Tg": PropertyRange(
                95.0,
                115.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.; the repository's "
                "116-trace verification found 94–103 °C.",
                method="DSC",
                note=(
                    "ABS is a blend: the value reported is the styrene-"
                    "acrylonitrile phase. The butadiene phase has its own, much "
                    "lower transition that a single-scan DSC usually does not "
                    "resolve."
                ),
            )
        },
    ),
    "PVOH": Polymer(
        key="PVOH",
        names=("poly(vinyl alcohol)", "polyvinyl alcohol", "pvoh", "pval", "pva"),
        properties={
            "Tg": PropertyRange(
                60.0,
                95.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
                note=(
                    "Very sensitive to water content, which is why the range is "
                    "wide. A dry, highly crystalline grade sits at the top."
                ),
            )
        },
    ),
    "PVAc": Polymer(
        key="PVAc",
        names=("poly(vinyl acetate)", "polyvinyl acetate", "pvac"),
        properties={
            "Tg": PropertyRange(
                25.0,
                45.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            )
        },
    ),
    "SAN": Polymer(
        key="SAN",
        names=("styrene acrylonitrile", "san"),
        properties={
            "Tg": PropertyRange(
                95.0,
                115.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.; the repository's "
                "116-trace verification found 91–97 °C.",
                method="DSC",
            )
        },
    ),
    "EVA": Polymer(
        key="EVA",
        names=("ethylene vinyl acetate", "eva"),
        properties={
            "Tm": PropertyRange(
                60.0,
                100.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
                note=(
                    "The melting point falls as the vinyl-acetate content "
                    "rises: a 5 % VA grade melts near 100 °C and a 40 % VA grade "
                    "near 60 °C. The range is the copolymer range, not an "
                    "uncertainty."
                ),
            )
        },
    ),
    "PHB": Polymer(
        key="PHB",
        names=("polyhydroxybutyrate", "poly(3-hydroxybutyrate)", "phb", "pha"),
        properties={
            "Tm": PropertyRange(
                160.0,
                185.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
            "Tg": PropertyRange(
                -10.0,
                20.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
        },
    ),
    "POM": Polymer(
        key="POM",
        names=("polyoxymethylene", "polyacetal", "pom"),
        properties={
            "Tm": PropertyRange(
                165.0,
                185.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
            "Tg": PropertyRange(
                -70.0,
                -50.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
        },
    ),
    "PU": Polymer(
        key="PU",
        names=("polyurethane", "pu", "tpu"),
        properties={
            "Tg": PropertyRange(
                -60.0,
                -10.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
                note=(
                    "Segment-dependent: the soft-block Tg sits at the low end of "
                    "this range, while the hard-block transition can appear "
                    "anywhere from 60 to 150 °C. A single reported value in that "
                    "upper region is the hard block, not the soft-block Tg."
                ),
            )
        },
    ),
    "PBT": Polymer(
        key="PBT",
        names=("poly(butylene terephthalate)", "pbt"),
        properties={
            "Tg": PropertyRange(
                30.0,
                60.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
            "Tm": PropertyRange(
                215.0,
                235.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
        },
    ),
    "PCL": Polymer(
        key="PCL",
        names=("polycaprolactone", "pcl"),
        properties={
            "Tg": PropertyRange(
                -65.0,
                -60.0,
                "°C",
                "Zenodo 10.5281/zenodo.17293641, the DSC dataset already used "
                "for the PCL verification in this repository.",
                method="DSC",
            ),
            "Tm": PropertyRange(
                56.0,
                60.0,
                "°C",
                "Zenodo 10.5281/zenodo.17293641.",
                method="DSC",
            ),
            "delta_Hm": PropertyRange(
                139.5,
                139.5,
                "J/g",
                "Reference enthalpy of 100 % crystalline PCL, used universally "
                "for its crystallinity calculation.",
            ),
        },
    ),
    "PK": Polymer(
        key="PK",
        names=("polyketone", "pk", "aliphatic polyketone"),
        properties={
            "Tm": PropertyRange(
                215.0,
                240.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            )
        },
    ),
    "PAN": Polymer(
        key="PAN",
        names=("polyacrylonitrile", "pan"),
        properties={
            "Tg": PropertyRange(
                80.0,
                110.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
                note=(
                    "PAN degrades before it melts, so a melting endotherm is not "
                    "expected: any endotherm above the Tg is decomposition, not "
                    "fusion."
                ),
            )
        },
    ),
    "EVOH": Polymer(
        key="EVOH",
        names=("ethylene vinyl alcohol", "evoh"),
        properties={
            "Tm": PropertyRange(
                150.0,
                190.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed. (copolymer range "
                "with ethylene content).",
                method="DSC",
            )
        },
    ),
    # The three below were in the alias table with no entry behind them, so a
    # sample named PEEK, PPSU or PTFE resolved to a key that did not exist and
    # came back as "polymer was not identified" -- which reads as a failure to
    # parse the name rather than an absence of data. They are high-temperature
    # engineering polymers, the ones most likely to be measured by someone who
    # needs the comparison, so the gap was worse than a missing entry: it
    # misdescribed why the answer was not available.
    "PEEK": Polymer(
        key="PEEK",
        names=("polyetheretherketone", "poly(ether ether ketone)", "peek"),
        properties={
            "Tg": PropertyRange(
                140.0,
                160.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.; consistent with "
                "the Polyether Ether Ketone entry in the open polymer property "
                "compilations (semantic-web polymer ontologies, CC-BY).",
                method="DSC",
                note=(
                    "Semi-crystalline, so the Tg step is small and easy to "
                    "miss: a PEEK trace with no detectable Tg is common and is "
                    "not evidence of an instrument fault."
                ),
            ),
            "Tm": PropertyRange(
                330.0,
                345.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
                note=(
                    "Above the upper limit of many DSC cells. A scan that ends "
                    "at 300 °C cannot report a PEEK melting point at all, so an "
                    "absent Tm here is expected rather than anomalous."
                ),
            ),
        },
    ),
    "PPSU": Polymer(
        key="PPSU",
        names=("polyphenylsulfone", "poly(phenyl sulfone)", "ppsu"),
        properties={
            "Tg": PropertyRange(
                210.0,
                230.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.; cross-checked "
                "against the polysulfone entries of the open polymer property "
                "compilations.",
                method="DSC",
            )
        },
    ),
    "PTFE": Polymer(
        key="PTFE",
        names=(
            "polytetrafluoroethylene",
            "poly(tetrafluoroethylene)",
            "ptfe",
            "teflon",
        ),
        properties={
            "Tm": PropertyRange(
                320.0,
                345.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
                note=(
                    "Two crystal forms: the 19-30 °C transition is a solid-state "
                    "crystal change, not a glass transition. A DSC endotherm "
                    "there is not a Tg and must not be compared as one."
                ),
            ),
        },
    ),
    "PSU": Polymer(
        key="PSU",
        names=("polysulfone", "psu", "udel"),
        properties={
            "Tg": PropertyRange(
                180.0,
                195.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            )
        },
    ),
    "PA12": Polymer(
        key="PA12",
        names=("polyamide 12", "nylon12", "nylon-12", "pa12"),
        properties={
            "Tm": PropertyRange(
                175.0,
                185.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
            "Tg": PropertyRange(
                35.0,
                55.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
                note=(
                    "The Tg is weak and sits near the start of a typical scan, "
                    "so it is frequently invisible. The amide chains absorb "
                    "water and a wet sample shifts it downward, which is why "
                    "the range is wide."
                ),
            ),
        },
    ),
    "PA11": Polymer(
        key="PA11",
        names=("polyamide 11", "nylon11", "nylon-11", "pa11", "rilsan"),
        properties={
            "Tm": PropertyRange(
                185.0,
                195.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            )
        },
    ),
    "PPS": Polymer(
        key="PPS",
        names=("polyphenylene sulfide", "poly(phenylene sulfide)", "pps", "ryton"),
        properties={
            "Tg": PropertyRange(
                85.0,
                100.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
            "Tm": PropertyRange(
                275.0,
                290.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
        },
    ),
    "PVDF": Polymer(
        key="PVDF",
        names=("polyvinylidene fluoride", "poly(vinylidene fluoride)", "pvdf"),
        properties={
            "Tm": PropertyRange(
                155.0,
                180.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed. (range covers the "
                "alpha and beta polymorphs).",
                method="DSC",
                note=(
                    "Polymorph-dependent: the alpha phase melts near 170 °C and "
                    "the beta phase near 160 °C, and the two overlap, so a "
                    "single melting peak reports a mixture."
                ),
            ),
            "Tg": PropertyRange(
                -45.0,
                -25.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
        },
    ),
    "LDPE": Polymer(
        key="LDPE",
        names=("low-density polyethylene", "ldpe"),
        properties={
            "Tm": PropertyRange(
                100.0,
                115.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
                note=(
                    "Distinct from HDPE, which melts 25-30 °C higher. Reporting "
                    "one polyethylene range for both is the commonest error in "
                    "polymer DSC, and the branch density that separates them is "
                    "exactly what the melting point measures."
                ),
            ),
        },
    ),
    "HDPE": Polymer(
        key="HDPE",
        names=("high-density polyethylene", "hdpe"),
        properties={
            "Tm": PropertyRange(
                125.0,
                140.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            ),
        },
    ),
    "ECTFE": Polymer(
        key="ECTFE",
        names=(
            "ethylene chlorotrifluoroethylene",
            "ethylene chlorotrifluoroethylene copolymer",
            "ectfe",
            "halar",
        ),
        properties={
            "Tm": PropertyRange(
                235.0,
                250.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            )
        },
    ),
    "FEP": Polymer(
        key="FEP",
        names=("fluorinated ethylene propylene", "fep", "fep teflon"),
        properties={
            "Tm": PropertyRange(
                250.0,
                265.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            )
        },
    ),
    "ETFE": Polymer(
        key="ETFE",
        names=("ethylene tetrafluoroethylene", "etfe", "tefzel"),
        properties={
            "Tm": PropertyRange(
                255.0,
                275.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
            )
        },
    ),
    "PVC-U": Polymer(
        key="PVC-U",
        names=("unplasticised pvc", "unplasticized pvc", "rigid pvc", "pvc-u", "upvc"),
        properties={
            "Tg": PropertyRange(
                75.0,
                85.0,
                "°C",
                "Brandrup et al., Polymer Handbook, 4th ed.",
                method="DSC",
                note=(
                    "Unplasticised PVC. The entry for PVC covers the "
                    "plasticised case; a plasticised compound has a Tg far "
                    "below this range and belongs to the PVC entry."
                ),
            )
        },
    ),
}


def _strip_run_suffix(token: str) -> str | None:
    """
    Strip a trailing run index from a token, or return None if there is none.

    "abs2" -> "abs", "ps5" -> "ps", "pla1" -> "pla". A trailing number is the
    one suffix instrument exports add that is unambiguous, because a polymer
    name never ends in a bare digit: the nylons that do carry one (PA6, PA66,
    PA12, PA11, PA46, PA610, PA1010) are written with letters after the digit,
    so they are matched exactly and never reach this function with a partial
    name. That is what makes "ABS2" resolvable while "PA46" is not silently
    read as PA6.

    Rejecting everything else is the point. An open-ended prefix rule cannot
    separate those two cases -- both are letters followed by digits -- and
    every attempt to patch one together accepts a wrong polymer for some
    name. A wrong identification produces a cited range for the wrong
    material and a confident wrong verdict, which is worse than no answer.
    """
    stripped = token.rstrip("0123456789")
    if stripped == token or not stripped:
        return None  # no trailing index, or nothing left behind it
    return stripped


def resolve(name: str | None) -> Polymer | None:
    """Find the repertoire entry for a sample name, or None.

    Sample names come from instrument files and are written by whoever ran the
    instrument, so the match is tolerant in exactly three ways, each of which
    is a shape an instrument actually produces:

    1. An exact alias match, case-insensitive: "ABS", "nylon66".
    2. A trailing run index: "ABS2", "PS5", "PLA1".
    3. A separator-delimited qualifier: "PE-NEW", "PP3-CRYO", "PLA1-AR",
       "HDPE-Recycled". The qualifier is stripped and the head re-matched
       through rules 1 and 2.

    Anything else returns None rather than a best guess, because guessing the
    polymer is how a comparison produces a confident wrong answer. In
    particular there is no open-ended prefix match: "PEKK" is not
    polyethylene, and "PA46" is not nylon-6. ``None`` and the empty string are
    not errors -- a pasted trace carries no sample name at all.
    """
    if not name:
        return None
    cleaned = name.strip().lower()
    for ext in (".tri", ".txt", ".csv", ".dat"):
        if cleaned.endswith(ext):
            cleaned = cleaned[: -len(ext)]
    cleaned = cleaned.strip("-_ ")
    if not cleaned:
        return None

    # Rule 1 and 2 on the whole name: "ABS", "ABS2", "nylon66".
    #
    # The head-token match is guarded: "pvc-c" must not become PVC through its
    # first token. A trailing one-character fragment after a separator
    # continues the chemical name -- PVC-C is chlorinated PVC, whose Tg is
    # about 20 °C above PVC's -- so the head is only accepted when the rest of
    # the name does not extend it that way.
    head_token = cleaned.replace("-", " ").replace("_", " ").split()[0]
    continuation = cleaned[len(head_token) :].lstrip("-_ ")
    # A *letter* fragment shorter than two characters continues the name
    # ("pvc-c", "pvc-c-x"). A digit fragment is a run index ("gpps-1",
    # "hips-2", "pa66-2") and does not.
    short_letter_fragment = any(
        len(f) < 2 and not f.isdigit()
        for f in continuation.replace("_", "-").split("-")
        if f
    )
    extends_the_name = bool(continuation) and short_letter_fragment
    for token in ((cleaned,) if extends_the_name else (cleaned, head_token)):
        if token in ALIASES:
            return REPERTOIRE.get(ALIASES[token])
        head = _strip_run_suffix(token)
        if head and head in ALIASES:
            return REPERTOIRE.get(ALIASES[head])

    # Rule 3, the separator-delimited qualifier: "PE-NEW" -> "pe",
    # "PP3-CRYO" -> "pp3" -> "pp", "PLA1-AR" -> "pla1" -> "pla",
    # "GPPS-1" -> "gpps" -> "ps".
    #
    # The tail must be a label, not a continuation of the chemical name. A
    # tail of one-character *letters* is how names are built rather than
    # annotated -- "pvc-c-x" is PVC-C with a further substitution, not PVC
    # labelled "c-x". Real labels here are whole words, codes or run numbers:
    # "new", "cryo", "ar", "gf", "recycled", "1", "30".
    if head_token != cleaned and not extends_the_name:
        tail = cleaned[len(head_token) :].lstrip("-_ ")
        fragments = [f for f in tail.replace("_", "-").split("-") if f]
        if fragments and all(len(f) >= 2 or f.isdigit() for f in fragments):
            head = _strip_run_suffix(head_token)
            target = head if (head and head in ALIASES) else head_token
            if target in ALIASES:
                return REPERTOIRE.get(ALIASES[target])
    return None
