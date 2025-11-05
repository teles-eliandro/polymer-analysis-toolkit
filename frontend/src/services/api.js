import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://polymer-analysis-toolkit.onrender.com';

export const molecularApi = {
  calculate: async (jsonData = null, csvFile = null) => {
    const formData = new FormData();
    
    if (jsonData) {
      return axios.post(`${API_BASE_URL}/molecular/calc`, jsonData);
    }
    
    if (csvFile) {
      formData.append('file', csvFile);
      return axios.post(`${API_BASE_URL}/molecular/calc`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    }
    
    throw new Error('Either jsonData or csvFile must be provided');
  }
};
