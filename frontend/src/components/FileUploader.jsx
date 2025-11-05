import React, { useState } from 'react';

const FileUploader = ({ onFileSelect }) => {
  const [fileName, setFileName] = useState('');

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.name.endsWith('.csv')) {
        setFileName(file.name);
        onFileSelect(file);
      } else {
        alert('Por favor, selecione um arquivo CSV.');
        e.target.value = null;
        onFileSelect(null);
      }
    } else {
      setFileName('');
      onFileSelect(null);
    }
  };

  return (
    <div className="form-section">
      <h3>Upload de Arquivo CSV</h3>
      <label className="file-upload">
        <input type="file" accept=".csv" onChange={handleFileChange} />
        {fileName || 'Clique para selecionar um arquivo CSV'}
      </label>
      <p className="help-text">Colunas esperadas: <code>massa,fracao</code></p>
    </div>
  );
};

export default FileUploader;