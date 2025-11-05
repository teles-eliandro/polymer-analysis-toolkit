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
        alert('Please select a CSV file.');
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
      <h3>CSV File Upload</h3>
      <label className="file-upload">
        <input type="file" accept=".csv" onChange={handleFileChange} />
        {fileName || 'Click to select a CSV file'}
      </label>
      <p className="help-text">Expected columns: <code>massa,fracao</code> or <code>mass,fraction</code></p>
    </div>
  );
};

export default FileUploader;
