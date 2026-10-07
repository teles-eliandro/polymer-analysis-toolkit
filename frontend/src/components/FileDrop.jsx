/**
 * File input shared by every module panel.
 *
 * Reads the file in the browser and hands the text to the same parser the
 * paste box uses, so both routes accept exactly the same formats. The file is
 * not uploaded for analysis: only the parsed numbers are sent, which keeps
 * the API contract unchanged and means a file the parser cannot read fails
 * here with a readable message instead of as a 422 from the server.
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

/** Refuse anything large enough to freeze the tab while parsing. */
const MAX_BYTES = 8 * 1024 * 1024;

function extensionOf(name) {
  const dot = name.lastIndexOf('.');
  return dot === -1 ? '' : name.slice(dot).toLowerCase();
}

export default function FileDrop({
  onText,
  onError,
  label,
  hint,
  accept = TEXT_EXTENSIONS.join(','),
}) {
  const { t } = useI18n();
  const inputRef = useRef(null);
  const [fileName, setFileName] = useState('');
  const [dragging, setDragging] = useState(false);

  const read = (file) => {
    if (!file) return;
    onError?.('');
    const ext = extensionOf(file.name);
    if (!TEXT_EXTENSIONS.includes(ext)) {
      onError?.(t('file.unsupported', { ext: ext || file.name }));
      return;
    }
    if (file.size > MAX_BYTES) {
      onError?.(t('file.tooLarge', { mb: Math.round(MAX_BYTES / 1024 / 1024) }));
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
          accept={accept}
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
