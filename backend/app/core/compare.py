"""Compare a measured property against its published range.

The verdict is tri-state, and the third state is the point
---------------------------------------------------------
A comparison returns one of:

    WITHIN   the measured value falls inside the published range
    OUTSIDE  it falls outside
    NOT_COMPARABLE  the comparison cannot be made, and saying so is the answer

``NOT_COMPARABLE`` is not an error path and not a placeholder. It is required
whenever a two-state verdict would be misleading, and there are four such cases:

1. The polymer was not identified. Comparing against the wrong polymer's range
   produces a confident wrong answer, which is worse than no answer.
2. The property is a *suggested* inference and the stability flag failed. The
   tool has already said it does not trust the number; comparing it anyway
   would re-launder that doubt into an apparent measurement.
3. No published range covers this property for this polymer.
4. The measured quantity carries a unit the reference does not, and no
   conversion is defined. A silent unit mismatch is how "outside the range"
   gets reported for a value that is correct in different units.

Without the third state, a glass transition that the detector placed on a
melting flank comes back as "OUTSIDE the published range", which reads as a
finding about the sample. It is not: it is a statement about the detector. The
distinction is the entire reason this module exists separately from the
analysis.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.core.reference import Polymer, PropertyRange, resolve

#: The verdicts, as stable strings the API and the interface agree on.
WITHIN = "within"
OUTSIDE = "outside"
NOT_COMPARABLE = "not_comparable"


@dataclass(frozen=True)
class Comparison:
    """One measured value compared against its published range."""

    property: str
    verdict: str
    #: The measured value as given, or None when there was nothing to compare.
    measured: float | None = None
    unit: str | None = None
    #: The published range, when one exists for this polymer and property.
    reference: PropertyRange | None = None
    #: Why the comparison could not be made, when the verdict is
    #: NOT_COMPARABLE. Always populated in that case.
    reason: str | None = None
    #: The polymer the value was compared against, when one was identified.
    polymer: str | None = None

    def as_dict(self) -> dict[str, float | str | None]:
        return {
            "property": self.property,
            "verdict": self.verdict,
            "measured": self.measured,
            "unit": self.unit,
            "reference_low": self.reference.low if self.reference else None,
            "reference_high": self.reference.high if self.reference else None,
            "reference_unit": self.reference.unit if self.reference else None,
            "reference_source": self.reference.source if self.reference else None,
            "reference_method": (
                self.reference.method if self.reference else None
            ),
            "reference_note": self.reference.note if self.reference else None,
            "reason": self.reason,
            "polymer": self.polymer,
        }


def _not_comparable(prop: str, reason: str, **kw) -> Comparison:
    return Comparison(
        property=prop, verdict=NOT_COMPARABLE, reason=reason, **kw
    )


def compare_property(
    prop: str,
    measured: float | None,
    unit: str,
    polymer: Polymer | None,
    *,
    confidence: str | None = None,
    stable: bool | None = None,
) -> Comparison:
    """Compare one measured value against the published range for *prop*.

    Parameters
    ----------
    prop
        Property name, matching the analysis output ("Tg", "Tm", ...).
    measured
        The value, or None when the analysis did not report one.
    unit
        The unit of ``measured``. A mismatch with the reference unit is
        reported as NOT_COMPARABLE rather than converted silently.
    polymer
        The resolved repertoire entry, or None when the polymer was not
        identified.
    confidence
        The confidence rung of the measured value ("read", "formula",
        "suggested"), when known.
    stable
        For a suggested transition, whether it survived the stability check.
        ``False`` forces NOT_COMPARABLE: a value the analysis has already
        flagged as unstable must not be compared as though it were a
        measurement.
    """
    if polymer is None:
        return _not_comparable(
            prop,
            "The polymer was not identified, so there is no published range to "
            "compare against. Selecting the polymer explicitly would allow the "
            "comparison.",
        )

    if measured is None:
        return _not_comparable(
            prop,
            f"{prop} was not reported for this trace, so there is nothing to "
            "compare.",
            polymer=polymer.key,
        )

    # A value the analysis itself distrusts must not be laundered into a
    # comparison result. This check comes before the range lookup on purpose:
    # the reason for not comparing is about the measurement, not the reference.
    if confidence == "suggested" and stable is False:
        return _not_comparable(
            prop,
            f"{prop} is an inference that did not survive the stability check "
            "(it moves with the sampling of this trace). Comparing it against a "
            "published range would present an unstable value as a measurement. "
            "Repeat the run before comparing.",
            measured=measured,
            unit=unit,
            polymer=polymer.key,
        )

    ref = polymer.properties.get(prop)
    if ref is None:
        return _not_comparable(
            prop,
            f"No published range for {prop} of {polymer.key} is held in the "
            "reference repertoire.",
            measured=measured,
            unit=unit,
            polymer=polymer.key,
        )

    if ref.unit != unit:
        return _not_comparable(
            prop,
            f"The measured value is in {unit} and the published range is in "
            f"{ref.unit}; no conversion is applied silently.",
            measured=measured,
            unit=unit,
            reference=ref,
            polymer=polymer.key,
        )

    verdict = WITHIN if ref.contains(measured) else OUTSIDE
    return Comparison(
        property=prop,
        verdict=verdict,
        measured=measured,
        unit=unit,
        reference=ref,
        polymer=polymer.key,
    )


#: Which analysis outputs to compare, and the unit each is reported in. Kept
#: next to the comparison rather than in the caller so a new property is added
#: in one place.
COMPARABLE: tuple[tuple[str, str], ...] = (
    ("Tg", "°C"),
    ("Tm", "°C"),
    ("delta_Hm", "J/g"),
)


def compare_result(
    sample_name: str | None,
    values: dict[str, float | None],
    *,
    claims: Mapping[str, object] | None = None,
) -> list[Comparison]:
    """Compare every comparable value of one analysis against the repertoire.

    ``values`` maps property name to the reported value. ``claims`` optionally
    carries the confidence rung per property, so a suggested value that failed
    its stability check is reported as not comparable instead of being compared.
    """
    polymer = resolve(sample_name or "")
    out: list[Comparison] = []
    for prop, unit in COMPARABLE:
        claim = (claims or {}).get(prop)
        confidence = getattr(claim, "confidence", None)
        note = getattr(claim, "note", None) or ""
        stable: bool | None = None
        if confidence == "suggested":
            # The stability flag rides in the claim note, which is the only
            # place the analysis records it without adding a field per property.
            if "did NOT survive" in note:
                stable = False
        out.append(
            compare_property(
                prop,
                values.get(prop),
                unit,
                polymer,
                confidence=confidence,
                stable=stable,
            )
        )
    return out
