import React, { useState } from 'react'
import axios from 'axios'
import { Sun, Moon, Eye } from 'lucide-react'
import api, { updateApiBaseURL } from '../../services/api'
import { setToken, setBackendUrl, getBackendUrl } from '../../utils/auth'
import logo from '../../assets/logo.png' // Import logo
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
      const currentHost = window.location.hostname
      const currentPort = window.location.port || (window.location.protocol === 'https:' ? '443' : '80')
      const currentProtocol = window.location.protocol

      // 1. Initial Guess: Use the current address (since we are served by the backend)
      let candidateUrl = `${currentProtocol}//${currentHost}:${currentPort}`

      // Clean up port 80/443 if standard
      if ((currentProtocol === 'http:' && currentPort === '80') ||
        (currentProtocol === 'https:' && currentPort === '443')) {
        candidateUrl = `${currentProtocol}//${currentHost}`
      }

      // Check if we can get better info from the API (Dynamic IP)
      // This upgrades "localhost" to "192.168.x.x"
      try {
        const infoRes = await axios.get(`${candidateUrl}/api/info`, { timeout: 2000 })
        if (infoRes.data && infoRes.data.local_ip) {
          const lanIp = infoRes.data.local_ip
          const lanUrl = `https://${lanIp}:${currentPort}`

          // CRITICAL FIX: If we are on localhost, but found a real LAN IP,
          // REDIRECT the browser to the LAN IP.
          // This solves "Cross-Origin" login issues and ensures the user sees the real address.
          if (currentHost === 'localhost' || currentHost === '127.0.0.1') {
            if (lanIp !== '127.0.0.1' && lanIp !== 'localhost') {
              // Force redirect
              window.location.href = lanUrl
              return
            }
          }

          setBackendUrlState(lanUrl)
          setBackendUrl(lanUrl)
          setAutoDetecting(false)
          return
        }
      } catch (e) {
        // console.warn("Failed to fetch API info:", e)
      }

      // Fallback: Just use what we are on
      setBackendUrlState(candidateUrl)
      setBackendUrl(candidateUrl)
      setAutoDetecting(false)
    }

    autoDetectBackend()
  }, [])

  const copyToClipboard = () => {
    navigator.clipboard.writeText(backendUrl)
      .then(() => alert('URL zkopírována: ' + backendUrl))
      .catch(() => { })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      // Update global API service with the current backend URL
      updateApiBaseURL(backendUrl)
      setBackendUrl(backendUrl)

      const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register'
      const response = await api.post(endpoint, {
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
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <input
              type="text"
              value={backendUrl}
              onChange={(e) => setBackendUrlState(e.target.value)}
              placeholder="Backend URL (automaticky detekováno)"
              className="input"
              style={{ paddingRight: '40px', marginBottom: 0 }}
              required
              disabled={autoDetecting}
            />
            <button
              type="button"
              onClick={copyToClipboard}
              style={{
                position: 'absolute',
                right: '10px',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: '#666'
              }}
              title="Kopírovat adresu"
            >
              📋
            </button>
          </div>
          <small style={{ color: '#666', fontSize: '12px', display: 'block', marginTop: '5px', marginBottom: '15px' }}>
            URL serveru. Pro připojení dalších zařízení použijte <strong style={{ color: '#667eea' }}>{backendUrl}</strong>
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

