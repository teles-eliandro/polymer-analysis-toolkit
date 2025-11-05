import React, { useState } from 'react';
import MolecularForm from './components/MolecularForm';
import FileUploader from './components/FileUploader';
import ResultsDisplay from './components/ResultsDisplay';
import { molecularApi } from './services/api';
import './App.css';

function App() {
  const [manualData, setManualData] = useState([]);
  const [csvFile, setCsvFile] = useState(null);
  const [csvPreview, setCsvPreview] = useState(null);
  const [results, setResults] = useState(null);
  const [inputData, setInputData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleManualDataChange = (rows) => {
    setManualData(rows);
    setCsvFile(null);
    setCsvPreview(null);
  };

  const handleFileSelect = (file) => {
    if (!file) {
      setCsvFile(null);
      setCsvPreview(null);
      return;
    }

    setCsvFile(file);
    setManualData([]);

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target.result;
      const lines = text.split('\n').filter(line => line.trim() !== '');
      if (lines.length < 2) return;

      const headers = lines[0].split(',').map(h => h.trim());
      const massIndex = headers.findIndex(h => h.toLowerCase() === 'massa' || h.toLowerCase() === 'mass');
      const fracIndex = headers.findIndex(h => h.toLowerCase() === 'fracao' || h.toLowerCase() === 'fraction');

      if (massIndex === -1 || fracIndex === -1) {
        setError('CSV must contain "massa"/"mass" and "fracao"/"fraction" columns.');
        return;
      }

      const data = [];
      for (let i = 1; i < lines.length; i++) {
        const fields = lines[i].split(',');
        if (fields.length > Math.max(massIndex, fracIndex)) {
          const massa = parseFloat(fields[massIndex]);
          const fracao = parseFloat(fields[fracIndex]);
          if (!isNaN(massa) && !isNaN(fracao)) {
            data.push({ massa, fracao });
          }
        }
      }

      if (data.length === 0) {
        setError('No valid data found in CSV.');
        return;
      }

      const masses = data.map(d => d.massa);
      const fracs = data.map(d => d.fracao);
      setCsvPreview({ masses, weight_fractions: fracs });
    };
    reader.readAsText(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResults(null);

    try {
      if (csvFile && csvPreview) {
        const response = await molecularApi.calculate(null, csvFile);
        setResults(response.data);
        setInputData(csvPreview);
      } else if (manualData.length > 0) {
        const validRows = manualData.filter(row => row.massa !== '' && row.fracao !== '');
        if (validRows.length === 0) throw new Error('Enter at least one valid data row.');

        const masses = validRows.map(r => {
          const val = parseFloat(r.massa);
          if (isNaN(val) || val <= 0) throw new Error('Mass values must be positive numbers.');
          return val;
        });
        const fracs = validRows.map(r => {
          const val = parseFloat(r.fracao);
          if (isNaN(val) || val < 0) throw new Error('Fraction values must be non-negative numbers.');
          return val;
        });

        const total = fracs.reduce((a, b) => a + b, 0);
        if (Math.abs(total - 1.0) > 0.001) {
          throw new Error(`Fractions must sum to 1.0 (current: ${total.toFixed(4)}).`);
        }

        const jsonData = { masses, weight_fractions: fracs };
        const response = await molecularApi.calculate(jsonData, null);
        setResults(response.data);
        setInputData({ masses, weight_fractions: fracs });
      } else {
        throw new Error('Enter manual data or upload a CSV file.');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'An unknown error occurred.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header>
        <h1>Polymer Analysis Toolkit (PAT)</h1>
        <p>Molecular Module — Calculate Mn, Mw, and Dispersity (Đ)</p>
      </header>

      <main>
        <form onSubmit={handleSubmit}>
          <MolecularForm onManualDataChange={handleManualDataChange} />
          <FileUploader onFileSelect={handleFileSelect} />

          <button type="submit" disabled={loading} className="submit-btn">
            {loading ? 'Calculating...' : 'Calculate Properties'}
          </button>

          {error && <div className="error-message">{error}</div>}
        </form>

        {results && inputData && (
          <ResultsDisplay results={results} inputData={inputData} />
        )}
      </main>

      <footer>
        <p>
          Developed by <strong>Eliandro P. Teles</strong> •{' '}
          <a
            href="https://github.com/teles-eliandro/polymer-analysis-toolkit"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: '#2196F3', textDecoration: 'none' }}
          >
            GitHub Repository
          </a>
        </p>
      </footer>
    </div>
  );
}

export default App;
