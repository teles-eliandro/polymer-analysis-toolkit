# Polymer Analysis Toolkit (PAT)

Ferramenta web para análise de propriedades de polímeros, começando com o **Módulo Molecular**.

## Funcionalidades (MVP)
- Cálculo de Mn, Mw e dispersidade (Đ) a partir de massas e frações em peso
- Entrada manual ou upload de CSV
- Visualização gráfica e exportação de resultados

## Tecnologias
- **Backend**: Python, FastAPI, Pydantic, Pandas
- **Frontend**: React, Axios, Plotly

## Como rodar localmente

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000