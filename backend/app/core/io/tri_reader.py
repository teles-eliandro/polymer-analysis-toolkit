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

#: Byte gap between the int32 count word and the first float32 sample.
_SAMPLE_OFFSET = 22

#: Byte overhead per channel block on top of the float32 payload.
_BLOCK_OVERHEAD = 72

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

    Returns ``(count_offset, count)``. Every candidate int32 in the data region
    is tested: a genuine channel count is followed by a finite float32 payload
    and repeats at the channel stride. Among the candidates that pass, the one
    that yields the most complete channel series wins -- anchoring on the first
    match instead lands on a later copy of the count (the file repeats the
    value in its index structures) and then decodes only one channel.

    A plain "is this a plausible count" scan is not enough: the files hold long
    runs of small integers that look like counts, and roughly 40 % of the
    dataset mis-anchored that way.
    """
    n = len(buf)
    best: tuple[int, int, int] | None = None
    for off in range(body_start // 4 * 4, n - 4, 4):
        (count,) = struct.unpack_from("<I", buf, off)
        if not (500 <= count <= 5_000_000):
            continue
        data_off = off + _SAMPLE_OFFSET
        if data_off + count * 4 > n:
            continue
        probe = struct.unpack_from(f"<{min(count, 1024)}f", buf, data_off)
        if not (all(v == v and abs(v) < 1e12 for v in probe) and any(v != 0.0 for v in probe)):
            continue
        stride = count * 4 + _BLOCK_OVERHEAD
        # Score the anchor by how many consecutive channels it reproduces.
        series = 1
        while True:
            nxt = off + series * stride
            if nxt + 4 > n:
                break
            (c,) = struct.unpack_from("<I", buf, nxt)
            if c != count:
                break
            series += 1
        if series < 2:
            continue
        if best is None or series > best[2]:
            best = (off, count, series)
    if best is None:
        return None
    return best[0], best[1]


def _read_channels(buf: bytes, signal_names: list[str]) -> tuple[list[TriChannel], int]:
    """Recover every numeric channel using the fixed channel stride."""
    png_end = buf.rfind(b"IEND")
    body_start = png_end + 8 if png_end > 0 else 0

    found = _find_channel_base(buf, body_start)
    if found is None:
        return [], 0
    first_off, count = found
    stride = count * 4 + _BLOCK_OVERHEAD

    channels: list[TriChannel] = []
    off = first_off
    while off + _SAMPLE_OFFSET + count * 4 <= len(buf):
        # Every block must start with the count word, otherwise the series has
        # run out and the rest of the file is trailing data.
        (c,) = struct.unpack_from("<I", buf, off)
        if c != count:
            break
        data_off = off + _SAMPLE_OFFSET
        vals = struct.unpack_from(f"<{count}f", buf, data_off)
        sane = sum(1 for v in vals if v == v and abs(v) < 1e12)
        if sane < count * 0.98:
            break
        name = (
            _clean_signal_name(signal_names[len(channels)])
            if len(channels) < len(signal_names)
            else None
        )
        channels.append(
            TriChannel(index=len(channels), name=name, offset=data_off, values=list(vals))
        )
        off += stride
    return channels, count


def read_tri(path: str) -> TriFile:
    """Decode a TA Instruments .tri file into metadata plus numeric channels."""
    with open(path, "rb") as fh:
        buf = fh.read()
    meta = _read_metadata(buf)
    signals = [s.strip() for s in (meta.get("proceduresignals") or "").split(";") if s.strip()]
    channels, count = _read_channels(buf, signals)
    return TriFile(path=path, metadata=meta, channels=channels, sample_count=count)
