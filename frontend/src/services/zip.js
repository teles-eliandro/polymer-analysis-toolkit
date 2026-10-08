/**
 * A minimal, dependency-free ZIP writer (STORED / no compression).
 *
 * The results export has to carry a PNG plus its numbers in one file. The
 * obvious route is jszip, but this bundle is already 1.18 MB and flagged by
 * CRA; a full zip library for two or three entries of already-compressed data
 * (PNG) and tiny text (JSON, CSV) buys nothing. Storing the entries costs a
 * few hundred bytes over deflating them.
 *
 * Only what is needed is implemented: local file headers, a central directory
 * and the end-of-central-directory record. No ZIP64, no encryption -- entries
 * here are kilobytes, not gigabytes.
 *
 * Format reference: PKWARE APPNOTE.TXT sections 4.3.6, 4.3.7, 4.3.12.
 */

/** CRC-32 (IEEE 802.3), the checksum ZIP requires per entry. */
const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i += 1) {
    let c = i;
    for (let k = 0; k < 8; k += 1) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[i] = c >>> 0;
  }
  return table;
})();

function crc32(bytes) {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i += 1) {
    c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

const encoder = new TextEncoder();

function toBytes(data) {
  if (data instanceof Uint8Array) return data;
  if (data instanceof ArrayBuffer) return new Uint8Array(data);
  return encoder.encode(String(data));
}

/** Reads a base64 data: URL (what Plotly's toImage returns) into bytes. */
export function dataUrlToBytes(dataUrl) {
  const comma = dataUrl.indexOf(',');
  if (comma < 0) throw new Error('not a data URL');
  const meta = dataUrl.slice(0, comma);
  const payload = dataUrl.slice(comma + 1);
  if (!/;base64/i.test(meta)) {
    // A percent-encoded payload is still decodable, just not via atob.
    const decoded = decodeURIComponent(payload);
    const out = new Uint8Array(decoded.length);
    for (let i = 0; i < decoded.length; i += 1) out[i] = decoded.charCodeAt(i) & 0xff;
    return out;
  }
  const binary = atob(payload);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) out[i] = binary.charCodeAt(i);
  return out;
}

/**
 * Builds a ZIP from [{ name, data }] and returns it as a Blob.
 * Files are stored in the order given.
 */
export function buildZip(entries) {
  const chunks = [];
  const central = [];
  let offset = 0;

  entries.forEach((entry) => {
    const nameBytes = encoder.encode(entry.name);
    const data = toBytes(entry.data);
    const crc = crc32(data);
    const size = data.length;

    const header = new DataView(new ArrayBuffer(30));
    header.setUint32(0, 0x04034b50, true); // local file header signature
    header.setUint16(4, 20, true); // version needed to extract
    header.setUint16(6, 0, true); // flags
    header.setUint16(8, 0, true); // method: 0 = stored
    header.setUint16(10, 0, true); // modification time
    header.setUint16(12, 0, true); // modification date
    header.setUint32(14, crc, true);
    header.setUint32(18, size, true); // compressed size
    header.setUint32(22, size, true); // uncompressed size
    header.setUint16(26, nameBytes.length, true);
    header.setUint16(28, 0, true); // extra field length

    chunks.push(new Uint8Array(header.buffer), nameBytes, data);

    const dir = new DataView(new ArrayBuffer(46));
    dir.setUint32(0, 0x02014b50, true); // central directory signature
    dir.setUint16(4, 20, true); // version made by
    dir.setUint16(6, 20, true); // version needed
    dir.setUint16(8, 0, true); // flags
    dir.setUint16(10, 0, true); // method
    dir.setUint16(12, 0, true); // time
    dir.setUint16(14, 0, true); // date
    dir.setUint32(16, crc, true);
    dir.setUint32(20, size, true);
    dir.setUint32(24, size, true);
    dir.setUint16(28, nameBytes.length, true);
    dir.setUint16(30, 0, true); // extra
    dir.setUint16(32, 0, true); // comment
    dir.setUint16(34, 0, true); // disk number
    dir.setUint16(36, 0, true); // internal attributes
    dir.setUint32(38, 0, true); // external attributes
    dir.setUint32(42, offset, true); // offset of local header

    central.push(new Uint8Array(dir.buffer), nameBytes);
    offset += 30 + nameBytes.length + size;
  });

  const centralSize = central.reduce((n, c) => n + c.length, 0);
  const end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true); // end of central directory signature
  end.setUint16(4, 0, true); // this disk
  end.setUint16(6, 0, true); // disk with central directory
  end.setUint16(8, entries.length, true);
  end.setUint16(10, entries.length, true);
  end.setUint32(12, centralSize, true);
  end.setUint32(16, offset, true); // central directory offset
  end.setUint16(20, 0, true); // comment length

  return new Blob([...chunks, ...central, new Uint8Array(end.buffer)], {
    type: 'application/zip',
  });
}

/** Turns the two-column trace a panel holds into CSV text. */
export function toCsv(columns, rows) {
  const cell = (v) => {
    // A missing measurement is an empty field, not the word "null".
    if (v === null || v === undefined || (typeof v === 'number' && Number.isNaN(v))) return '""';
    return `"${String(v).replace(/"/g, '""')}"`;
  };
  const head = columns.map(cell).join(',');
  const body = rows.map((r) => r.map(cell).join(','));
  return [head, ...body].join('\n');
}
