import React from 'react';
import Plot from 'react-plotly.js';
import { saveAs } from 'file-saver';

const ResultsDisplay = ({ results, inputData }) => {
  const exportData = () => {
    const data = {
      input: inputData,
      results: results
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    saveAs(blob, 'pat_results.json');
  };

  if (!inputData || !inputData.masses || !inputData.weight_fractions) {
    return <div>Erro: dados de entrada não disponíveis para visualização.</div>;
  }

  const plotData = [
    {
      x: inputData.masses,
      y: inputData.weight_fractions,
      type: 'bar',
      marker: { color: '#4A90E2' },
      name: 'Fração em Peso'
    }
  ];

  const layout = {
    title: 'Distribuição de Massa Molecular (Fração em Peso)',
    xaxis: { title: 'Massa Molecular (g/mol)' },
    yaxis: { title: 'Fração em Peso' },
    width: 600,
    height: 400,
    margin: { l: 60, r: 20, t: 60, b: 60 }
  };

  return (
    <div className="results-section">
      <h2>Resultados</h2>
      <div className="metrics">
        <div className="metric-box">
          <h4>Mn (numérico)</h4>
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
        <button onClick={exportData}>Exportar JSON</button>
      </div>
    </div>
  );
};

export default ResultsDisplay;
