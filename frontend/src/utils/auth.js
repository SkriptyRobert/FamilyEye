const TOKEN_KEY = 'parental_control_token'
const BACKEND_URL_KEY = 'parental_control_backend_url'

export const getToken = () => {
  return localStorage.getItem(TOKEN_KEY)
}

export const setToken = (token) => {
  localStorage.setItem(TOKEN_KEY, token)
}

export const removeToken = () => {
  localStorage.removeItem(TOKEN_KEY)
}

export const getBackendUrl = () => {
  // Try localStorage first (saved during login)
  const saved = localStorage.getItem(BACKEND_URL_KEY)
  if (saved) return saved
  
  // Try environment variable
  const envUrl = import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_DEFAULT_BACKEND_URL
  if (envUrl) return envUrl
  
  // Auto-detect from current location - use same protocol and host
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol // http: or https:
    const currentHost = window.location.hostname
    const backendPort = import.meta.env?.VITE_BACKEND_PORT || '8000'
    
    // Use same protocol as current page (important for self-signed certs)
    return `${protocol}//${currentHost}:${backendPort}`
  }
  
  // Fallback for development
  return 'https://localhost:8000'
}

export const setBackendUrl = (url) => {
  localStorage.setItem(BACKEND_URL_KEY, url)
}

