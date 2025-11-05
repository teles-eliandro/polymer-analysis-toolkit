import React, { useState } from 'react';

const MolecularForm = ({ onManualDataChange }) => {
  const [rows, setRows] = useState([{ massa: '', fracao: '' }]);

  const addRow = () => {
    setRows([...rows, { massa: '', fracao: '' }]);
  };

  const removeRow = (index) => {
    if (rows.length > 1) {
      const newRows = rows.filter((_, i) => i !== index);
      setRows(newRows);
      onManualDataChange(newRows);
    }
  };

  const handleInputChange = (index, field, value) => {
    const newRows = [...rows];
    newRows[index][field] = value;
    setRows(newRows);
    onManualDataChange(newRows);
  };

  return (
    <div className="form-section">
      <h3>Entrada Manual</h3>
      {rows.map((row, index) => (
        <div key={index} className="input-row">
          <input
            type="number"
            placeholder="Massa"
            value={row.massa}
            onChange={(e) => handleInputChange(index, 'massa', e.target.value)}
            min="0"
            step="any"
          />
          <input
            type="number"
            placeholder="Fração (peso)"
            value={row.fracao}
            onChange={(e) => handleInputChange(index, 'fracao', e.target.value)}
            min="0"
            step="any"
          />
          <button type="button" onClick={() => removeRow(index)} disabled={rows.length <= 1}>
            🗑️
          </button>
        </div>
      ))}
      <button type="button" onClick={addRow} className="add-row-btn">
        + Adicionar linha
      </button>
    </div>
  );
};

export default MolecularForm;