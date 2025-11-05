
// frontend/src/services/api.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const molecularApi = {
  calculate: async (jsonData = null, csvFile = null) => {
    if (jsonData) {
      return axios.post(`${API_BASE_URL}/api/v1/molecular/calc`, jsonData);
    }
    if (csvFile) {
      const formData = new FormData();
      formData.append('file', csvFile);
      return axios.post(`${API_BASE_URL}/api/v1/molecular/calc`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    }
    throw new Error('Either JSON data or CSV file must be provided');
  }
};
