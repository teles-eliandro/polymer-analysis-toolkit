/**
 * Tests for the dependency-free ZIP writer.
 *
 * A hand-written binary format is the kind of thing that ships broken: the
 * file looks fine until someone unzips it. These tests therefore check the
 * bytes that make an archive readable -- signatures, sizes, CRC -- and the
 * package's own `unzip` is used in CI-adjacent manual checks.
 */

import { buildZip, dataUrlToBytes, toCsv } from '../services/zip';

/** Minimal reader for the fields an unzip tool actually validates. */
function readUint32(bytes, at) {
  return (
    (bytes[at] |
      (bytes[at + 1] << 8) |
      (bytes[at + 2] << 16) |
      (bytes[at + 3] << 24)) >>>
    0
  );
}
function readUint16(bytes, at) {
  return bytes[at] | (bytes[at + 1] << 8);
}

async function blobBytes(blob) {
  // jsdom's Blob predates arrayBuffer(); FileReader is the portable path.
  if (typeof blob.arrayBuffer === 'function') {
    const buf = await blob.arrayBuffer();
    return new Uint8Array(buf);
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(new Uint8Array(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(blob);
  });
}

describe('buildZip', () => {
  it('starts with the local file header signature', async () => {
    const zip = buildZip([{ name: 'a.txt', data: 'hello' }]);
    const bytes = await blobBytes(zip);
    expect(readUint32(bytes, 0)).toBe(0x04034b50);
  });

  it('writes the file name and contents verbatim', async () => {
    const zip = buildZip([{ name: 'graph.png', data: 'PNGDATA' }]);
    const bytes = await blobBytes(zip);
    const nameLen = readUint16(bytes, 26);
    const name = new TextDecoder().decode(bytes.slice(30, 30 + nameLen));
    expect(name).toBe('graph.png');
    const body = new TextDecoder().decode(bytes.slice(30 + nameLen, 30 + nameLen + 7));
    expect(body).toBe('PNGDATA');
  });

  it('records the correct CRC-32 and sizes for the entry', async () => {
    const data = 'hello';
    const zip = buildZip([{ name: 'a.txt', data }]);
    const bytes = await blobBytes(zip);
    const crc = readUint32(bytes, 14);
    const compSize = readUint32(bytes, 18);
    const uncompSize = readUint32(bytes, 22);
    expect(compSize).toBe(5);
    expect(uncompSize).toBe(5);
    // CRC-32 of "hello" is a well-known constant; a wrong table would miss it.
    expect(crc).toBe(0x3610a686);
  });

  it('declares every entry in the end-of-central-directory record', async () => {
    const zip = buildZip([
      { name: 'a.txt', data: 'a' },
      { name: 'b.txt', data: 'b' },
      { name: 'c.txt', data: 'c' },
    ]);
    const bytes = await blobBytes(zip);
    // The EOCD sits at the very end; find its signature from the tail.
    let at = -1;
    for (let i = bytes.length - 22; i >= 0; i -= 1) {
      if (readUint32(bytes, i) === 0x06054b50) {
        at = i;
        break;
      }
    }
    expect(at).toBeGreaterThan(-1);
    expect(readUint16(bytes, at + 8)).toBe(3); // entries on this disk
    expect(readUint16(bytes, at + 10)).toBe(3); // entries total
  });

  it('carries binary payloads unchanged', async () => {
    const png = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
    const zip = buildZip([{ name: 'p.png', data: png }]);
    const bytes = await blobBytes(zip);
    const nameLen = readUint16(bytes, 26);
    const body = bytes.slice(30 + nameLen, 30 + nameLen + 8);
    expect(Array.from(body)).toEqual(Array.from(png));
  });
});

describe('dataUrlToBytes', () => {
  it('decodes a base64 PNG data URL', () => {
    // 1x1 transparent PNG.
    const url =
      'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
    const bytes = dataUrlToBytes(url);
    expect(bytes[0]).toBe(0x89);
    expect(bytes[1]).toBe(0x50); // 'P'
    expect(bytes.length).toBeGreaterThan(50);
  });

  it('rejects something that is not a data URL', () => {
    expect(() => dataUrlToBytes('https://example.com/a.png')).toThrow();
  });
});

describe('toCsv', () => {
  it('quotes the header and the values', () => {
    const csv = toCsv(['T', 'H'], [[1, 2], [3, 4]]);
    expect(csv).toBe('"T","H"\n"1","2"\n"3","4"');
  });

  it('leaves a missing value empty rather than writing null', () => {
    expect(toCsv(['a', 'b'], [[1, null]])).toBe('"a","b"\n"1",""');
  });
});
