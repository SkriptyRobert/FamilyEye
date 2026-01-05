import React, { useState } from 'react'
import api from '../services/api'
import { Eye } from 'lucide-react'
import './InitialSetup.css'

const InitialSetup = ({ onComplete }) => {
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [formData, setFormData] = useState({
    parent_email: '',
    parent_password: '',
    confirm_password: '',
    device_name: window.localStorage.getItem('computerName') || 'Můj Počítač'
  })

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const handleNext = () => {
    if (step === 1) {
      if (!formData.parent_email || !formData.parent_password) {
        setError('Vyplňte prosím všechna pole')
        return
      }
      if (formData.parent_password !== formData.confirm_password) {
        setError('Hesla se neshodují')
        return
      }
      setError('')
      setStep(2)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      // 1. Vytvořit účet rodiče
      await api.post('/api/auth/register', {
        email: formData.parent_email,
        password: formData.parent_password,
        role: 'parent'
      })

      // 2. Přihlásit se pro získání tokenu
      const loginRes = await api.post('/api/auth/login', {
        email: formData.parent_email,
        password: formData.parent_password
      })

      // Uložit token pro další požadavky
      localStorage.setItem('token', loginRes.data.access_token)
      api.defaults.headers.common['Authorization'] = `Bearer ${loginRes.data.access_token}`

      // 3. Zaregistrovat toto zařízení
      await api.post('/api/devices/', {
        name: formData.device_name,
        device_type: 'pc',
        os_info: 'Windows'
      })

      onComplete()
    } catch (err) {
      // Handle the case where the user already exists
      if (err.response?.status === 400 && (err.response?.data?.detail?.includes('exists') || err.response?.data?.detail?.includes('zaregistrován'))) {
        try {
          // If already exists, just try to login and register device
          const loginRes = await api.post('/api/auth/login', {
            email: formData.parent_email,
            password: formData.parent_password
          })
          localStorage.setItem('token', loginRes.data.access_token)
          api.defaults.headers.common['Authorization'] = `Bearer ${loginRes.data.access_token}`

          await api.post('/api/devices/', {
            name: formData.device_name,
            device_type: 'pc',
            os_info: 'Windows'
          })
          onComplete()
          return
        } catch (loginErr) {
          setError('Tento účet již existuje, ale zadané heslo je nesprávné.')
          return
        }
      }
      setError(err.response?.data?.detail || 'Chyba při nastavování. Zkuste to prosím znovu.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="setup-container">
      <div className="setup-card">
        <div className="setup-header">
          <h1>👁️ FamilyEye - Počáteční nastavení</h1>
          <div className="steps-indicator">
            <span className={step === 1 ? 'active' : ''}>1</span>
            <span className={step === 2 ? 'active' : ''}>2</span>
          </div>
        </div>

        {step === 1 ? (
          <div className="setup-step">
            <h2>Krok 1: Účet rodiče</h2>
            <p>Vytvořte si účet, pomocí kterého budete spravovat toto zařízení.</p>

            <input
              type="email"
              name="parent_email"
              value={formData.parent_email}
              onChange={handleChange}
              placeholder="Email rodiče"
              className="setup-input"
            />
            <input
              type="password"
              name="parent_password"
              value={formData.parent_password}
              onChange={handleChange}
              placeholder="Heslo"
              className="setup-input"
            />
            <input
              type="password"
              name="confirm_password"
              value={formData.confirm_password}
              onChange={handleChange}
              placeholder="Potvrzení hesla"
              className="setup-input"
            />

            {error && <div className="setup-error">{error}</div>}

            <button onClick={handleNext} className="setup-button">
              Pokračovat
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="setup-step">
            <h2>Krok 2: Název zařízení</h2>
            <p>Jak se má tento počítač jmenovat v přehledu?</p>

            <input
              type="text"
              name="device_name"
              value={formData.device_name}
              onChange={handleChange}
              placeholder="Název zařízení (např. Lukášův PC)"
              className="setup-input"
            />

            {error && <div className="setup-error">{error}</div>}

            <div className="setup-buttons">
              <button type="button" onClick={() => setStep(1)} className="setup-button secondary">
                Zpět
              </button>
              <button type="submit" disabled={loading} className="setup-button">
                {loading ? 'Nastavuji...' : 'Dokončit nastavení'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

export default InitialSetup
