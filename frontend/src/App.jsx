import React, { useState } from 'react';
import MolecularForm from './components/MolecularForm';
import FileUploader from './components/FileUploader';
import ResultsDisplay from './components/ResultsDisplay';
import { molecularApi } from './services/api';
import './App.css';

function App() {
  const [manualData, setManualData] = useState([]);
  const [csvFile, setCsvFile] = useState(null);
  const [results, setResults] = useState(null);
  const [inputData, setInputData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleManualDataChange = (rows) => {
    setManualData(rows);
    setCsvFile(null); // clear file if manual input is used
  };

  const handleFileSelect = (file) => {
    setCsvFile(file);
    setManualData([]); // clear manual if file is used
  };

  const validateAndPrepareData = () => {
    if (csvFile) return { type: 'file', data: csvFile };

    const validRows = manualData.filter(row => row.massa !== '' && row.fracao !== '');
    if (validRows.length === 0) throw new Error('Insira pelo menos uma linha válida.');

    const masses = validRows.map(r => parseFloat(r.massa));
    const fracs = validRows.map(r => parseFloat(r.fracao));

    if (masses.some(m => isNaN(m) || m <= 0)) throw new Error('Massas devem ser números positivos.');
    if (fracs.some(f => isNaN(f) || f < 0)) throw new Error('Frações devem ser números não negativos.');

    const total = fracs.reduce((a, b) => a + b, 0);
    if (Math.abs(total - 1.0) > 0.001) {
      throw new Error(`Frações devem somar 1.0 (atual: ${total.toFixed(4)}).`);
    }

    return {
      type: 'json',
      data: { masses, weight_fractions: fracs }
    };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResults(null);

    try {
      const payload = validateAndPrepareData();
      const response = await molecularApi.calculate(
        payload.type === 'json' ? payload.data : null,
        payload.type === 'file' ? payload.data : null
      );

      // Prepare input for display
      let displayInput;
      if (payload.type === 'json') {
        displayInput = payload.data;
      } else {
        // For file, we don’t parse client-side — but we can show file name
        displayInput = { source: 'CSV: ' + csvFile.name };
      }

      setResults(response.data);
      setInputData(displayInput);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Erro desconhecido');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header>
        <h1>Polymer Analysis Toolkit (PAT)</h1>
        <p>Módulo Molecular — Análise de Mn, Mw e Dispersidade</p>
      </header>

      <main>
        <form onSubmit={handleSubmit}>
          <MolecularForm onManualDataChange={handleManualDataChange} />
          <FileUploader onFileSelect={handleFileSelect} />

          <button type="submit" disabled={loading} className="submit-btn">
            {loading ? 'Calculando...' : 'Calcular Propriedades'}
          </button>

          {error && <div className="error-message">{error}</div>}
        </form>

        {results && inputData && (
          <ResultsDisplay results={results} inputData={inputData} />
        )}
      </main>

      <footer>
        <p>PAT v0.1 — Ferramenta para caracterização polimérica</p>
      </footer>
    </div>
  );
}

export default App;