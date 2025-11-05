import React, { useState } from 'react';
import FileUploader from './components/FileUploader';
import ResultsDisplay from './components/ResultsDisplay';
import { molecularApi } from './services/api';
import './App.css';

function App() {
  const [csvFile, setCsvFile] = useState(null);
  const [csvPreview, setCsvPreview] = useState(null);
  const [results, setResults] = useState(null);
  const [inputData, setInputData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFileSelect = (file) => {
    if (!file) {
      setCsvFile(null);
      setCsvPreview(null);
      return;
    }

    if (!file.name.endsWith('.csv')) {
      setError('Please select a CSV file.');
      return;
    }

    setCsvFile(file);

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target.result;
      const lines = text.split('\n').filter(line => line.trim() !== '');
      if (lines.length < 2) {
        setError('CSV must contain at least one data row.');
        return;
      }

      const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
      const massIndex = headers.indexOf('massa');
      const fracIndex = headers.indexOf('fracao');

      if (massIndex === -1 || fracIndex === -1) {
        setError('CSV must contain columns named exactly: "massa" and "fracao".');
        return;
      }

      const data = [];
      for (let i = 1; i < lines.length; i++) {
        const fields = lines[i].split(',');
        if (fields.length > Math.max(massIndex, fracIndex)) {
          const massa = parseFloat(fields[massIndex]);
          const fracao = parseFloat(fields[fracIndex]);
          if (!isNaN(massa) && !isNaN(fracao) && massa > 0 && fracao >= 0) {
            data.push({ massa, fracao });
          }
        }
      }

      if (data.length === 0) {
        setError('No valid numeric data found in CSV.');
        return;
      }

      const masses = data.map(d => d.massa);
      const fracs = data.map(d => d.fracao);
      const total = fracs.reduce((a, b) => a + b, 0);
      if (Math.abs(total - 1.0) > 0.001) {
        setError(`Fractions must sum to 1.0 (current sum: ${total.toFixed(4)}).`);
        return;
      }

      setCsvPreview({ masses, weight_fractions: fracs });
    };
    reader.readAsText(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!csvFile) {
      setError('Please select a CSV file.');
      return;
    }

    setLoading(true);
    setError('');
    setResults(null);

    try {
      const response = await molecularApi.calculate(null, csvFile);
      setResults(response.data);
      setInputData(csvPreview);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error processing file. Check format and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header>
        <h1>Polymer Analysis Toolkit (PAT)</h1>
        <p className="subtitle">Molecular Weight Distribution Analyzer</p>
      </header>

      <main>
        <div className="introduction">
          <p>
            PAT calculates key molecular properties from polymer characterization data:
          </p>
          <ul>
            <li><strong>Mn</strong> — Number-average molecular weight</li>
            <li><strong>Mw</strong> — Weight-average molecular weight</li>
            <li><strong>Đ</strong> — Dispersity index (Mw/Mn)</li>
          </ul>
          <p>
            <strong>Instructions:</strong> Upload a CSV file with two columns: 
            <code>massa</code> (molecular weight in g/mol) and <code>fracao</code> (weight fraction). 
            Fractions must sum to 1.0.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <FileUploader onFileSelect={handleFileSelect} />
          <button type="submit" disabled={loading || !csvFile} className="submit-btn">
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
