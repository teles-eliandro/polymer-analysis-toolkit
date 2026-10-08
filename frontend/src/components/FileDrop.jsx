/**
 * File input shared by every module panel.
 *
 * Two modes, chosen by which callback is passed:
 *
 * - `onText` (default): the file is read in the browser and its text handed
 *   to the same parser the paste box uses, so both routes accept exactly the
 *   same formats. Only the parsed numbers are uploaded, which keeps the API
 *   contract unchanged and means a file the parser cannot read fails here
 *   with a readable message instead of as a 422 from the server.
 * - `onFile`: the File object itself is handed back, without reading it. Used
 *   by the molar-mass module, whose importer runs on the server and detects
 *   the vendor convention from the raw bytes, so gating on a browser-side
 *   text parse would reject formats the backend can read.
 *
 * The visual design, drag-and-drop, size guard and clear button are identical
 * in both modes; only the accepted extensions and what is done with the file
 * differ.
 */

import React, { useRef, useState } from 'react';
import { useI18n } from '../i18n/I18nContext';

/** Extensions we attempt to read as text. Binary instrument formats are not. */
const TEXT_EXTENSIONS = [
  '.csv',
  '.tsv',
  '.txt',
  '.dat',
  '.asc',
  '.prn',
  '.xy',
  '.json',
];

/** Extensions the molar-mass importer attempts. Wider than the text list
 * because the file goes to the server, which sniffs the delimiter, the header
 * language and the column roles instead of assuming a fixed layout. Spreadsheet
 * and binary instrument formats are not listed: the importer parses text, and
 * accepting a file it would then fail to read is worse than refusing it here. */
const IMPORT_EXTENSIONS = [
  ...TEXT_EXTENSIONS,
  '.asc',
  '.prn',
];

/** Refuse anything large enough to freeze the tab while parsing. */
const MAX_BYTES = 8 * 1024 * 1024;

/** Server uploads never touch the tab's memory, so allow a larger file. */
const MAX_UPLOAD_BYTES = 32 * 1024 * 1024;

function extensionOf(name) {
  const dot = name.lastIndexOf('.');
  return dot === -1 ? '' : name.slice(dot).toLowerCase();
}

export default function FileDrop({
  onText,
  onFile,
  onError,
  label,
  hint,
  accept,
}) {
  const { t } = useI18n();
  const inputRef = useRef(null);
  const [fileName, setFileName] = useState('');
  const [dragging, setDragging] = useState(false);

  // Upload mode: the server importer does the format detection.
  const uploadMode = !onText && typeof onFile === 'function';
  const allowed = uploadMode ? IMPORT_EXTENSIONS : TEXT_EXTENSIONS;
  const maxBytes = uploadMode ? MAX_UPLOAD_BYTES : MAX_BYTES;
  const resolvedAccept = accept || allowed.join(',');

  const read = (file) => {
    if (!file) return;
    onError?.('');
    const ext = extensionOf(file.name);
    if (!allowed.includes(ext)) {
      onError?.(t('file.unsupported', { ext: ext || file.name }));
      return;
    }
    if (file.size > maxBytes) {
      onError?.(t('file.tooLarge', { mb: Math.round(maxBytes / 1024 / 1024) }));
      return;
    }
    if (uploadMode) {
      setFileName(file.name);
      onFile(file);
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setFileName(file.name);
      onText?.(String(reader.result ?? ''), file);
    };
    reader.onerror = () => onError?.(t('file.readFailed', { name: file.name }));
    // Instrument exports are frequently latin-1 rather than UTF-8, and a
    // mis-decoded degree sign would be reported as a parse failure. Decoding
    // as UTF-8 and substituting keeps the numbers, which is what we need.
    reader.readAsText(file, 'utf-8');
  };

  const onInputChange = (e) => read(e.target.files?.[0]);

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    read(e.dataTransfer?.files?.[0]);
  };

  const clear = () => {
    setFileName('');
    if (inputRef.current) inputRef.current.value = '';
    onText?.('', null);
  };

  return (
    <div className="file-drop-wrap">
      <div
        className={`file-drop${dragging ? ' is-dragging' : ''}${
          fileName ? ' has-file' : ''
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        role="button"
        tabIndex={0}
        aria-label={label || t('file.choose')}
      >
        <input
          ref={inputRef}
          type="file"
          accept={resolvedAccept}
          onChange={onInputChange}
          onClick={(e) => e.stopPropagation()}
          className="file-drop-input"
        />
        <span className="file-drop-icon" aria-hidden="true">
          {fileName ? '✓' : '⇪'}
        </span>
        <span className="file-drop-text">
          <span className="file-drop-primary">
            {fileName || label || t('file.chooseOrDrop')}
          </span>
          <span className="file-drop-hint">
            {hint || t('file.accepted', { list: 'CSV, TSV, TXT, DAT, ASC' })}
          </span>
        </span>
      </div>
      {fileName ? (
        <button type="button" className="file-drop-clear" onClick={clear}>
          {t('file.clear')}
        </button>
      ) : null}
    </div>
  );
}
