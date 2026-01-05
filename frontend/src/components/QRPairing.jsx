import React, { useState, useEffect } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import api from '../services/api'
import { getBackendUrl } from '../utils/auth'
import './QRPairing.css'

const QRPairing = () => {
  const [pairingToken, setPairingToken] = useState('')
  const [pairingUrl, setPairingUrl] = useState('')
  const [deviceName, setDeviceName] = useState('')
  const [deviceType, setDeviceType] = useState('windows')
  const [manualToken, setManualToken] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [backendUrl, setBackendUrl] = useState('')

  useEffect(() => {
    setBackendUrl(getBackendUrl())
  }, [])

  const handleCreatePairing = async () => {
    setLoading(true)
    setError('')
    setSuccess('')

    try {
      const response = await api.post('/api/devices/pairing/token')
      setPairingToken(response.data.token)
      setPairingUrl(response.data.pairing_url)
      setManualToken(response.data.token) // Also set for manual entry
    } catch (err) {
      console.error('Pairing error:', err)
      const errorMsg = err.response?.data?.detail || 'Chyba při vytváření pairing tokenu'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const handleManualPair = async () => {
    if (!manualToken.trim()) {
      setError('Zadejte pairing token')
      return
    }

    setLoading(true)
    setError('')
    setSuccess('')

    try {
      // Generate unique device ID and MAC address
      const timestamp = Date.now()
      const randomSuffix = Math.random().toString(36).substring(2, 9)
      const deviceId = `${deviceType}-${timestamp}-${randomSuffix}`
      // Generate random MAC address (agent will use real one if available)
      const macParts = Array.from({ length: 6 }, () => 
        Math.floor(Math.random() * 256).toString(16).padStart(2, '0')
      )
      const macAddress = macParts.join(':')

      const response = await api.post('/api/devices/pairing/pair', {
        token: manualToken.trim(),
        device_name: deviceName || (deviceType === 'android' ? 'Android Device' : 'Windows PC'),
        device_type: deviceType,
        mac_address: macAddress,
        device_id: deviceId
      })

      setSuccess(`Zařízení úspěšně spárované! Device ID: ${deviceId}`)
      setManualToken('')
      setDeviceName('')
      setPairingToken('')
      setPairingUrl('')
      
      // Refresh device list after a moment
      setTimeout(() => {
        // Trigger refresh by navigating to devices tab
        window.dispatchEvent(new Event('device-paired'))
      }, 2000)
    } catch (err) {
      console.error('Pairing error:', err)
      const errorMsg = err.response?.data?.detail || 'Chyba při párování zařízení'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="qr-pairing">
      <h2>Přidat nové zařízení</h2>
      <p>Vygenerujte QR kód nebo použijte manuální párování pomocí tokenu</p>

      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      <div style={{ marginBottom: '30px' }}>
        <h3>Metoda 1: QR kód</h3>
        {!pairingUrl ? (
          <button onClick={handleCreatePairing} disabled={loading} className="button">
            {loading ? 'Vytváření...' : 'Vygenerovat QR kód'}
          </button>
        ) : (
          <div className="qr-container">
            <QRCodeSVG value={pairingUrl} size={256} />
            <p className="info">
              Naskenujte tento QR kód pomocí agenta na zařízení, které chcete přidat.
            </p>
            <p className="token-info">Token: {pairingToken}</p>
            <button
              onClick={() => {
                setPairingToken('')
                setPairingUrl('')
              }}
              className="button"
            >
              Vygenerovat nový QR kód
            </button>
          </div>
        )}
      </div>

      <div style={{ marginTop: '40px', paddingTop: '30px', borderTop: '1px solid var(--border-color)' }}>
        <h3>Metoda 2: Manuální párování</h3>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
          Pro Windows agent: Spusťte <code>python windows_agent/pair_device.py</code> a zadejte token
        </p>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', maxWidth: '500px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Typ zařízení:
            </label>
            <select
              value={deviceType}
              onChange={(e) => setDeviceType(e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                fontSize: '14px'
              }}
            >
              <option value="windows">Windows PC</option>
              <option value="android">Android</option>
              <option value="ios">iOS (iPhone/iPad)</option>
              <option value="linux">Linux</option>
              <option value="other">Jiné</option>
            </select>
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Název zařízení (volitelné):
            </label>
            <input
              type="text"
              value={deviceName}
              onChange={(e) => setDeviceName(e.target.value)}
              placeholder={deviceType === 'android' ? 'Např. Samsung Galaxy' : 'Např. Robert-PC'}
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                fontSize: '14px'
              }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Pairing Token:
            </label>
            <input
              type="text"
              value={manualToken}
              onChange={(e) => setManualToken(e.target.value)}
              placeholder="Vložte pairing token zde"
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                fontSize: '14px',
                fontFamily: 'monospace'
              }}
            />
            {pairingToken && !manualToken && (
              <button
                onClick={() => setManualToken(pairingToken)}
                style={{
                  marginTop: '5px',
                  padding: '5px 10px',
                  fontSize: '12px',
                  background: 'var(--accent-color)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Použít token z QR kódu
              </button>
            )}
          </div>

          <button
            onClick={handleManualPair}
            disabled={loading || !manualToken.trim()}
            className="button"
          >
            {loading ? 'Párování...' : 'Spárovat zařízení'}
          </button>
        </div>

        <div style={{ marginTop: '20px', padding: '15px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '13px' }}>
          <strong>Instrukce pro Windows agent:</strong>
          <ol style={{ marginTop: '10px', paddingLeft: '20px' }}>
            <li>Otevřete PowerShell jako Administrator</li>
            <li>Přejděte do složky projektu</li>
            <li>Spusťte: <code>python windows_agent/pair_device.py</code></li>
            <li>Zadejte Backend URL: <code>{backendUrl}</code> (nebo stiskněte Enter)</li>
            <li>Zadejte Pairing Token nebo QR URL: můžete zkopírovat celý QR URL nebo jen token</li>
            <li>Zadejte název zařízení (volitelné)</li>
          </ol>
        </div>
      </div>
    </div>
  )
}

export default QRPairing

