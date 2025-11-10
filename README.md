# Polymer Analysis Toolkit (PAT)

[![Démo en ligne](https://img.shields.io/badge/Démo-Vercel-000000?logo=vercel)](https://polymer-analysis-toolkit.vercel.app)
[![Licence](https://img.shields.io/badge/Licence-MIT-blue)](LICENSE)

**Polymer Analysis Toolkit (PAT)** est une application web open source conçue pour aider les chercheurs, ingénieurs et étudiants en science des matériaux à analyser les propriétés moléculaires des polymères de manière simple, précise et accessible — **sans aucune connaissance en programmation**.

Le module initial (**Moléculaire**) permet de calculer automatiquement les grandeurs fondamentales de la caractérisation polymérique à partir d’un fichier CSV contenant les masses moléculaires et leurs fractions en poids.

---

## 🔬 Fondements théoriques

Les calculs sont basés sur les définitions classiques de la **chimie des polymères** et de la **caractérisation par chromatographie d’exclusion stérique (SEC/GPC)**.

### 1. **Masse moyenne en nombre (Mn)**
Représente la moyenne arithmétique pondérée par le **nombre de chaînes** :
\[
M_n = \frac{1}{\sum \left( \frac{w_i}{M_i} \right)}
\]
où :
- \( M_i \) = masse moléculaire de la fraction \( i \)
- \( w_i \) = fraction en **poids** de la fraction \( i \)

> 💡 Cette formule est dérivée de la relation \( x_i = \frac{w_i / M_i}{\sum (w_j / M_j)} \), où \( x_i \) est la fraction molaire.

### 2. **Masse moyenne en poids (Mw)**
Pondère les masses par leur **contribution en masse** :
\[
M_w = \sum (w_i \cdot M_i)
\]

### 3. **Indice de dispersité (Đ)**
Indicateur de **polydispersité** du polymère :
\[
Đ = \frac{M_w}{M_n}
\]
- \( Đ = 1 \) : polymère monodispersé (idéal, rare)
- \( 1 < Đ < 1.2 \) : polymérisation contrôlée (ex: ATRP, RAFT)
- \( Đ > 1.5 \) : polymérisation radicalaire non contrôlée

> ✅ **Remarque** : PAT suppose que les fractions fournies sont des **fractions en poids** (comme c’est le cas dans les données brutes de GPC/SEC), ce qui est la convention expérimentale la plus courante.

---

## 🚀 Fonctionnalités (Module Moléculaire)

- ✅ **Upload de fichier CSV** avec colonnes `massa` et `fracao`
- ✅ **Validation automatique** :
  - Masses > 0
  - Fractions ≥ 0
  - Somme des fractions = 1.0 (±0.001)
- ✅ **Calcul précis** de Mn, Mw et Đ
- ✅ **Visualisation graphique** de la distribution (histogramme)
- ✅ **Export des résultats** au format JSON
- ✅ Interface entièrement en **anglais** (standard scientifique international)
- ✅ Déploiement **sans serveur** (Vercel + Render)

---

## 🛠️ Technologies utilisées

### Backend (API)
- **Langage** : Python 3.11
- **Framework** : [FastAPI](https://fastapi.tiangolo.com/) (API RESTful moderne, auto-documentée)
- **Validation** : Pydantic
- **Calculs** : NumPy, pandas
- **Hébergement** : [Render](https://render.com)

### Frontend (Interface utilisateur)
- **Framework** : React.js
- **Graphiques** : Plotly.js via `react-plotly.js`
- **Requêtes HTTP** : Axios
- **Hébergement** : [Vercel](https://vercel.app)

---

## ▶️ Comment utiliser l’outil ?

1. Accédez à la version de production :  
   👉 [https://polymer-analysis-toolkit.vercel.app](https://polymer-analysis-toolkit.vercel.app)

2. Préparez un fichier CSV avec **exactement deux colonnes** :
   ```csv
   massa,fracao
   1000,0.2
   2000,0.5
   5000,0.3


