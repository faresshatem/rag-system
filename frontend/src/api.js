import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const login = async (username, password) => {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  const response = await api.post('/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  });
  return response.data;
};

export const register = async (username, password, role = "User", allowed_domains = "") => {
  const response = await api.post('/register', { username, password, role, allowed_domains });
  return response.data;
};

export const runQuery = async (query) => {
  const response = await api.post('/query', { query });
  return response.data;
};

export const ingestData = async (domain, file) => {
  const formData = new FormData();
  formData.append('domain', domain);
  formData.append('file', file);
  
  const response = await api.post('/ingest', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export default api;
