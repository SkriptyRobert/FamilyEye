import axios from 'axios'
import { getToken, getBackendUrl } from '../utils/auth'

// Get initial backend URL - use environment variable or auto-detect
const getDefaultBackendUrl = () => {
  const saved = getBackendUrl()
  if (saved) return saved
  const envUrl = import.meta.env?.VITE_BACKEND_URL
  if (envUrl) return envUrl
  // Auto-detect from current location
  if (typeof window !== 'undefined') {
    const currentHost = window.location.hostname
    const backendPort = import.meta.env?.VITE_BACKEND_PORT || '8000'
    return currentHost && currentHost !== 'localhost' && currentHost !== '127.0.0.1'
      ? `http://${currentHost}:${backendPort}`
      : `http://localhost:${backendPort}`
  }
  return 'http://localhost:8000'
}

let currentBackendUrl = getDefaultBackendUrl()

const api = axios.create({
  baseURL: currentBackendUrl,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Function to update base URL
export const updateApiBaseURL = (newUrl) => {
  currentBackendUrl = newUrl
  api.defaults.baseURL = newUrl
}

// Add token to requests and prevent caching
api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  const backendUrl = getBackendUrl()
  if (backendUrl) {
    config.baseURL = backendUrl
  }
  // Prevent browser caching of API responses
  config.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
  config.headers['Pragma'] = 'no-cache'
  config.headers['Expires'] = '0'
  return config
}, (error) => {
  return Promise.reject(error)
})

// Handle 401 errors - redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - clear it
      localStorage.removeItem('parental_control_token')
      // Redirect to login if not already there
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api

