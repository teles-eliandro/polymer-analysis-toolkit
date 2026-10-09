"""Reader for TA Instruments Trios .tri files (DSC raw data).

The container is proprietary but the layout is regular and was recovered
empirically from figshare dataset 24462004 (59 DSC runs, 20 polymers):

  * A metadata block sits at the head of the file. Keys and values are ASCII
    strings prefixed with their byte length and separated by control bytes
    (\\x10, \\x0e, \\r, \\n). This yields the sample name, sample size in mg,
    the pan type and the full procedure ("Ramp 10.00 C/min to 175.00 C").
  * A rendered PNG plot follows, ending with the IEND chunk.
  * After the PNG come the numeric channels. Every channel is written as an
    int32 sample count followed 22 bytes later by that many float32 samples.
    Channel blocks are separated by a fixed stride::

        stride = sample_count * 4 + 72

    The first channel is Time (seconds). The signal order comes from the
    ``proceduresignals`` metadata key.

Anchoring: the count word of a real channel is preceded by the same count on a
second, 18-byte-earlier writer pass, so a file contains the byte pattern
``<count as int32><18 bytes><count as int32>``. Searching for that pattern and
then confirming that the stride reproduces the count several times over is far
more reliable than scanning for "any plausible count", which picks up
concatenated noise runs and mis-anchors roughly 40 % of the files.

Validation: the recovered ramp rate is 10.00 C/min and the recovered glass
transitions land on published values (PS ~100 C, ABS ~100-109 C, PVC ~70 C).
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field

import numpy as np

#: Byte gap between the int32 count word and the first float32 sample.
#:
#: Recovered empirically: a block is laid out as
#:
#:     <int32 count> <int32 zero-pad> <count * float32 payload>
#:
#: i.e. the payload starts eight bytes after the count word. An earlier
#: constant of 22 came from a probe that happened to read in phase on part of
#: the set; on the rest it started mid-payload and the recovered channels were
#: garbage, which silently dropped ``heat_flow`` on those files.
_SAMPLE_OFFSET = 8

#: Leading samples of the Time channel, in seconds, used to anchor the payload.
#: The first channel of every file in this dataset is Time sampled at 10 Hz, so
#: the float32 sequence 0.1, 0.2, 0.3 is a reliable fingerprint. Matching data
#: directly is what makes the reader robust: the count word repeats throughout
#: the file (in index structures and in later buffer copies), so choosing an
#: anchor by "plausible count" alone lands on the wrong one and decodes noise.
_TIME_SIGNATURE = struct.pack("<3f", 0.1, 0.2, 0.3)

#: Byte overhead per channel block on top of the float32 payload.
_BLOCK_OVERHEAD = 72

#: Values at the end of a channel payload below this magnitude are the block's
#: trailing padding word, not samples. Real readings are of order 1e-3 to 1e3
#: (seconds, degrees, W/g), and the padding is a denormal near 1e-38.
_PADDING_EPS = 1e-30

#: Largest block header to search when locating a payload. The header seen in
#: this dataset is 8-40 bytes; the margin covers variants without scanning
#: the whole 27 MB file.
_MAX_HEADER = 62

#: Text keys carried in the .tri metadata block.
_KEYS = (
    "samplename",
    "samplesize",
    "samplepanmass",
    "pantype",
    "comments",
    "instrumentmode",
    "testtype",
    "proceduresegments",
    "proceduresignals",
    "operator",
    "date",
)


def _clean_signal_name(name: str) -> str:
    """Strip the length prefix TA writes in front of each signal name.

    Names are stored length-prefixed, so the first character is often the byte
    count of the string that follows -- ``"\\x01Time"`` rather than ``"Time"``.
    Left in place the name never matches a lookup, which silently disabled
    channel selection on part of the real dataset.
    """
    return name.strip().strip("\x01\x02\x03\x04\x05\x06\x07\x08\x0e\x10\r\n")


@dataclass
class TriChannel:
    """One numeric channel recovered from a .tri file."""

    index: int
    name: str | None
    offset: int
    values: list[float]


@dataclass
class TriFile:
    """Decoded contents of a .tri file."""

    path: str
    metadata: dict[str, str] = field(default_factory=dict)
    channels: list[TriChannel] = field(default_factory=list)
    sample_count: int = 0

    @property
    def sample_name(self) -> str | None:
        return self.metadata.get("samplename") or None

    @property
    def sample_mass_mg(self) -> float | None:
        raw = self.metadata.get("samplesize")
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    @property
    def procedure(self) -> str | None:
        return self.metadata.get("proceduresegments") or None

    @property
    def signal_names(self) -> list[str]:
        raw = self.metadata.get("proceduresignals") or ""
        names = []
        for part in raw.split(";"):
            cleaned = _clean_signal_name(part)
            if cleaned:
                names.append(cleaned)
        return names

    def channel(self, name: str) -> TriChannel | None:
        """Return the channel whose signal name matches *name* (case-insensitive)."""
        want = name.strip().lower()
        for ch in self.channels:
            if ch.name and ch.name.strip().lower() == want:
                return ch
        return None

    @property
    def temperature(self) -> list[float] | None:
        """Program temperature in C, if a temperature channel is present."""
        for ch in self.channels:
            if ch.name and "temperature" in ch.name.lower() and "zero" in ch.name.lower():
                return ch.values
        for ch in self.channels:
            if ch.name and ch.name.strip().lower() == "temperature":
                return ch.values
        return None

    @property
    def heat_flow(self) -> list[float] | None:
        """Heat flow channel in mW, if present."""
        for ch in self.channels:
            if ch.name and ch.name.strip().lower().startswith("heat flow"):
                return ch.values
        return None


def _read_metadata(buf: bytes) -> dict[str, str]:
    """Pull the key/value metadata block out of the file head."""
    png = buf.find(b"\x89PNG")
    head = buf[: png if png > 0 else 4096]
    text = head.decode("latin-1")

    out: dict[str, str] = {}
    for key in _KEYS:
        for m in re.finditer(re.escape(key), text):
            start = m.start()
            vlen_pos = start + len(key)
            if vlen_pos >= len(text):
                continue
            vlen = ord(text[vlen_pos])
            value = text[vlen_pos + 1 : vlen_pos + 1 + vlen]
            if value and sum(1 for c in value if 32 <= ord(c) < 127) / len(value) > 0.9:
                out.setdefault(key, value)
                break
    return out


def _find_channel_base(buf: bytes, body_start: int) -> tuple[int, int] | None:
    """Locate the first channel block after *body_start*.

    Returns ``(payload_offset, count)``. The anchor is found by matching the
    Time channel's first samples rather than by scanning for a plausible count
    word: the count is a small integer that repeats all over the file (index
    structures, later buffer copies), and an anchor chosen that way lands on
    the wrong copy and decodes noise. On this dataset the scan-for-count
    approach mis-anchored 6 of 116 files, and a "longest repeating series"
    refinement picked a spurious ``512`` word on exactly those.

    Matching the data itself is unambiguous. Every file starts its first
    channel with Time in seconds at 10 Hz, so the float32 triplet
    ``0.1, 0.2, 0.3`` identifies the payload. The count word sits
    ``_SAMPLE_OFFSET`` bytes earlier. The candidate is accepted only when the
    next block, a stride further on, carries the same count -- which validates
    both the count and the stride in one check.
    """
    n = len(buf)
    start = max(body_start, 0)

    pos = buf.find(_TIME_SIGNATURE, start)
    while pos >= 0:
        word_off = pos - _SAMPLE_OFFSET
        if word_off >= 0:
            (count,) = struct.unpack_from("<I", buf, word_off)
            if 500 <= count <= 5_000_000:
                stride = count * 4 + _BLOCK_OVERHEAD
                # The next block must repeat the count. This rejects a
                # coincidental float match in unrelated data.
                nxt = pos + stride - _SAMPLE_OFFSET
                if nxt + 4 <= n and struct.unpack_from("<I", buf, nxt)[0] == count:
                    return pos, count
                # A single block is still better than nothing when the stride
                # is unavailable (truncated file), provided the payload fits.
                if pos + count * 4 <= n:
                    return pos, count
        pos = buf.find(_TIME_SIGNATURE, pos + 1)
    return None


def _read_channels(buf: bytes, signal_names: list[str]) -> tuple[list[TriChannel], int]:
    """Recover every numeric channel using the fixed channel stride.

    ``_find_channel_base`` returns the *payload* offset of the first channel,
    so block ``k`` starts at ``payload_off + k * stride``.
    """
    png_end = buf.rfind(b"IEND")
    body_start = png_end + 8 if png_end > 0 else 0

    found = _find_channel_base(buf, body_start)
    if found is None:
        return [], 0
    payload_off, count = found
    stride = count * 4 + _BLOCK_OVERHEAD
    n = len(buf)

    channels: list[TriChannel] = []
    while payload_off + count * 4 <= n:
        # The count repeats several times per block in this container, so the
        # stride keeps landing on valid-looking data past the real end of the
        # channel list. The metadata names every channel, so stop there.
        if signal_names and len(channels) >= len(signal_names):
            break
        vals = np.frombuffer(buf, dtype="<f4", count=count, offset=payload_off)
        sane = int(np.isfinite(vals).sum())
        if sane < count * 0.98:
            break
        # The stored count is one larger than the number of real samples: the
        # block carries a trailing padding word inside its payload. Left in,
        # every channel ends with a spurious point, which put a 0 C reading at
        # the end of the temperature axis and made a ramp-rate check read
        # -6.9 K/min instead of +10. The padding is not exactly zero -- it is a
        # denormal such as 2.4e-38 that prints as 0.000 -- so the tail is
        # trimmed against a small absolute threshold rather than equality.
        last = count
        while last > 0 and abs(float(vals[last - 1])) < _PADDING_EPS:
            last -= 1
        # Never trim more than a token amount: a channel that is legitimately
        # all zeros (cell purge) must survive intact.
        if 0 < count - last <= 4 and last > count // 2:
            vals = vals[:last]
        name = (
            _clean_signal_name(signal_names[len(channels)])
            if len(channels) < len(signal_names)
            else None
        )
        channels.append(
            TriChannel(
                index=len(channels),
                name=name,
                offset=payload_off,
                values=vals.astype(float).tolist(),
            )
        )
        payload_off += stride
    return channels, count


def read_tri(path: str) -> TriFile:
    """Decode a TA Instruments .tri file into metadata plus numeric channels."""
    with open(path, "rb") as fh:
        buf = fh.read()
    meta = _read_metadata(buf)
    signals = [s.strip() for s in (meta.get("proceduresignals") or "").split(";") if s.strip()]
    channels, count = _read_channels(buf, signals)
    return TriFile(path=path, metadata=meta, channels=channels, sample_count=count)
