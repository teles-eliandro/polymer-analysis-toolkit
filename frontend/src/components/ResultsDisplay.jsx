import React from 'react';
import Plot from 'react-plotly.js';
import { saveAs } from 'file-saver';

const ResultsDisplay = ({ results, inputData }) => {
  const exportData = (format) => {
    const data = {
      input: inputData,
      results: results
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    saveAs(blob, `pat_results.${format}`);
  };

  const plotData = [
    {
      x: inputData.masses,
      y: inputData.weight_fractions,
      type: 'bar',
      marker: { color: '#4A90E2' }
    }
  ];

  const layout = {
    title: 'Distribuição de Massa (Fração em Peso)',
    xaxis: { title: 'Massa Molecular (g/mol)' },
    yaxis: { title: 'Fração em Peso' },
    width: 600,
    height: 400
  };

  return (
    <div className="results-section">
      <h2>Resultados</h2>
      <div className="metrics">
        <div className="metric-box">
          <h4>Mn (número)</h4>
          <p>{results.Mn.toFixed(2)} g/mol</p>
        </div>
        <div className="metric-box">
          <h4>Mw (peso)</h4>
          <p>{results.Mw.toFixed(2)} g/mol</p>
        </div>
        <div className="metric-box">
          <h4>Đ (dispersidade)</h4>
          <p>{results.dispersity.toFixed(4)}</p>
        </div>
      </div>

      <div className="chart-container">
        <Plot data={plotData} layout={layout} />
      </div>

      <div className="export-buttons">
        <button onClick={() => exportData('json')}>Exportar JSON</button>
        {/* CSV export requires extra formatting — can be added later */}
      </div>
    </div>
  );
};

export default ResultsDisplay;