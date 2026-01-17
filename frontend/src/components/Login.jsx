import React, { useState } from 'react'
import { Sun, Moon, Eye } from 'lucide-react'
import axios from 'axios'
import { setToken, setBackendUrl, getBackendUrl } from '../utils/auth'
import logo from '../assets/logo.png' // Import logo
import './Login.css'

const Login = ({ onLogin, darkMode, setDarkMode }) => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [backendUrl, setBackendUrlState] = useState(getBackendUrl())
  const [isLogin, setIsLogin] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [autoDetecting, setAutoDetecting] = useState(false)

  // Auto-detect backend URL on mount
  React.useEffect(() => {
    const autoDetectBackend = async () => {
      // Get default backend URL from env or use default
      const backendPort = parseInt(import.meta.env.VITE_BACKEND_PORT || '8000', 10)
      const currentHost = window.location.hostname
      const currentProtocol = window.location.protocol // 'http:' or 'https:'

      // Prefer HTTPS, fallback to same protocol as current page
      const preferredProtocol = 'https'
      const fallbackProtocol = currentProtocol.replace(':', '')

      // If we're on same-origin (port 8000), backend is probably serving us
      if (window.location.port === String(backendPort) || !window.location.port) {
        const sameOriginUrl = `${currentProtocol}//${currentHost}:${backendPort}`
        setBackendUrlState(sameOriginUrl)
        setBackendUrl(sameOriginUrl)
        return
      }

      if (backendUrl && backendUrl !== 'http://localhost:8000') {
        // User already has a saved URL, don't override
        return
      }

      setAutoDetecting(true)

      // Try common ports
      const commonPorts = [backendPort, 8000, 5000]
      const protocols = [preferredProtocol, fallbackProtocol]

      // Try to detect from current window location first
      if (currentHost && currentHost !== 'localhost' && currentHost !== '127.0.0.1') {
        for (const protocol of protocols) {
          for (const port of commonPorts) {
            try {
              const testUrl = `${protocol}://${currentHost}:${port}`
              const response = await axios.get(`${testUrl}/api/health`, { timeout: 2000 })
              if (response.data && response.data.status === 'healthy') {
                setBackendUrlState(testUrl)
                setBackendUrl(testUrl)
                setAutoDetecting(false)
                return
              }
            } catch (e) {
              // Continue trying
            }
          }
        }
      }

      // Try localhost
      const localhosts = ['localhost', '127.0.0.1']
      for (const protocol of protocols) {
        for (const host of localhosts) {
          for (const port of commonPorts) {
            try {
              const testUrl = `${protocol}://${host}:${port}`
              const response = await axios.get(`${testUrl}/api/health`, { timeout: 2000 })
              if (response.data && response.data.status === 'healthy') {
                setBackendUrlState(testUrl)
                setBackendUrl(testUrl)
                setAutoDetecting(false)
                return
              }
            } catch (e) {
              // Continue trying
            }
          }
        }
      }

      // Default to HTTPS on current host
      const defaultUrl = `https://${currentHost}:${backendPort}`
      setBackendUrlState(defaultUrl)
      setBackendUrl(defaultUrl)
      setAutoDetecting(false)
    }

    autoDetectBackend()
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      setBackendUrl(backendUrl)
      const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register'
      const response = await axios.post(`${backendUrl}${endpoint}`, {
        email,
        password,
        role: 'parent'
      })

      setToken(response.data.access_token)
      onLogin()
    } catch (err) {
      const errorMsg = err.response?.data?.detail || (isLogin ? 'Chyba při přihlášení' : 'Chyba při registraci')
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-box">
        <div style={{ position: 'absolute', top: '20px', right: '20px' }}>
          <button
            type="button"
            onClick={() => setDarkMode(!darkMode)}
            className="theme-toggle"
            title={darkMode ? 'Světlý režim' : 'Tmavý režim'}
          >
            {darkMode ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        </div>
        <h1>
          <img src={logo} alt="FamilyEye" className="login-logo" />
          FamilyEye
        </h1>
        <h2>{isLogin ? 'Přihlášení' : 'Registrace'}</h2>

        <div className="toggle">
          <button
            type="button"
            onClick={() => setIsLogin(true)}
            className={isLogin ? 'active' : ''}
          >
            Přihlásit se
          </button>
          <button
            type="button"
            onClick={() => setIsLogin(false)}
            className={!isLogin ? 'active' : ''}
          >
            Registrovat se
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              value={backendUrl}
              onChange={(e) => setBackendUrlState(e.target.value)}
              placeholder="Backend URL (např. http://192.168.0.145:8000)"
              className="input"
              required
              disabled={autoDetecting}
            />
            {autoDetecting && (
              <span style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', fontSize: '12px', color: '#666' }}>
                Detekuji...
              </span>
            )}
          </div>
          <small style={{ color: '#666', fontSize: '12px', display: 'block', marginTop: '-10px', marginBottom: '10px' }}>
            Pro lokální síť použijte IP adresu serveru (např. https://192.168.0.145:8000)
          </small>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            className="input"
            required
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Heslo"
            className="input"
            required
          />

          {error && <div className="error">{error}</div>}

          <button type="submit" disabled={loading} className="button">
            {loading ? 'Zpracování...' : isLogin ? 'Přihlásit' : 'Registrovat'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default Login

