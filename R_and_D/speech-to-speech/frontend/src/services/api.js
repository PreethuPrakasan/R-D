import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getConfig = async () => {
  const response = await api.get('/config');
  return response.data;
};

export const updateConfig = async (config) => {
  const response = await api.post('/config', config);
  return response.data;
};

export const getLLMResponse = async (text) => {
  const response = await api.post('/llm/respond', { text });
  return response.data.response;
};

export const getTTSAudio = async (text) => {
  const response = await api.post('/tts/speak', { text }, {
    responseType: 'blob',
  });
  return response.data;
};

export default api;

