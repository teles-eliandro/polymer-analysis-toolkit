import React from 'react';

const FileUploader = ({ onFileSelect }) => {
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.name.endsWith('.csv')) {
        onFileSelect(file);
      } else {
        alert('Please select a CSV file.');
        e.target.value = null;
        onFileSelect(null);
      }
    } else {
      onFileSelect(null);
    }
  };

  return (
    <div className="form-section">
      <label className="file-upload">
        <input type="file" accept=".csv" onChange={handleFileChange} />
        Click to select a CSV file (columns: <code>massa,fracao</code>)
      </label>
    </div>
  );
};

export default FileUploader;
