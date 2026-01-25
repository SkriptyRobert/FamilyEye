import React, { useState, useEffect } from 'react'
import api from '../services/api'
import { formatToLocalTime } from '../utils/date'
import { getDeviceTypeInfo } from '../utils/formatting'
import { RefreshCw, Calendar, Smartphone, Trash2, Edit, Shield, ShieldOff, AlertTriangle } from 'lucide-react'
import DynamicIcon from './DynamicIcon'
import DeviceOwnerSetup from './DeviceOwnerSetup'
import './DeviceList.css'

const DeviceList = ({ onSelectDevice }) => {
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deviceOwnerSetupDevice, setDeviceOwnerSetupDevice] = useState(null)
  
  // Device Owner deactivation state
  const [deactivateDevice, setDeactivateDevice] = useState(null)
  const [deactivatePassword, setDeactivatePassword] = useState('')
  const [deactivateLoading, setDeactivateLoading] = useState(false)
  const [deactivateError, setDeactivateError] = useState('')

  useEffect(() => {
    fetchDevices()
    const handleDevicePaired = () => fetchDevices()
    window.addEventListener('device-paired', handleDevicePaired)

    // Poll for updates
    const intervalId = setInterval(fetchDevices, 10000)

    return () => {
      window.removeEventListener('device-paired', handleDevicePaired)
      clearInterval(intervalId)
    }
  }, [])

  const fetchDevices = async () => {
    try {
      const response = await api.get('/api/devices/')
      setDevices(response.data)
    } catch (err) {
      setError('Chyba při načítání zařízení')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (deviceId) => {
    if (!window.confirm('Opravdu chcete smazat toto zařízení?')) return
    try {
      await api.delete(`/api/devices/${deviceId}`)
      await fetchDevices()
    } catch (err) {
      setError('Chyba při mazání zařízení')
    }
  }

  const handleRename = async (deviceId, newName) => {
    try {
      await api.put(`/api/devices/${deviceId}`, { name: newName })
      await fetchDevices()
    } catch (err) {
      setError('Chyba při přejmenování zařízení')
      console.error(err)
    }
  }

  const handleResetPin = async (deviceId) => {
    const newPin = prompt("Zadejte nový 4-místný PIN pro toto zařízení:", "0000");
    if (newPin === null) return; // Cancelled

    if (!/^\d{4,6}$/.test(newPin)) {
      alert("PIN musí obsahovat 4 až 6 číslic.");
      return;
    }

    try {
      await api.post(`/api/devices/${deviceId}/reset-pin`, { new_pin: newPin });
      alert(`Příkaz pro reset PINu (na ${newPin}) byl odeslán.`);
    } catch (err) {
      setError('Chyba při resetování PINu');
      console.error(err);
    }
  }

  // Handle Device Owner deactivation
  const handleDeactivateDeviceOwner = async () => {
    if (!deactivatePassword.trim()) {
      setDeactivateError('Zadejte heslo pro potvrzení');
      return;
    }

    setDeactivateLoading(true);
    setDeactivateError('');

    try {
      await api.post(`/api/devices/${deactivateDevice.id}/deactivate-device-owner`, {
        password: deactivatePassword
      });
      
      // Success - close modal and refresh
      setDeactivateDevice(null);
      setDeactivatePassword('');
      await fetchDevices();
      alert('Device Owner ochrany byly deaktivovany. Aplikaci lze nyni odinstalovat.');
    } catch (err) {
      console.error('Failed to deactivate Device Owner:', err);
      if (err.response?.status === 401) {
        setDeactivateError('Nesprávné heslo');
      } else {
        setDeactivateError(err.response?.data?.detail || 'Chyba při deaktivaci Device Owner');
      }
    } finally {
      setDeactivateLoading(false);
    }
  }

  if (loading) return <div className="loading">Načítání...</div>
  if (error) return <div className="error">{error}</div>

  const handleRefresh = () => fetchDevices()

  return (
    <div className="device-page-container">
      <div className="page-header">
        <h1>Spravovaná zařízení</h1>
        <button
          onClick={handleRefresh}
          className="refresh-btn-icon"
          title="Obnovit seznam"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {devices.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon"><Calendar size={48} color="var(--text-muted)" /></div>
          <p>Žádná zařízení. Přidejte nové zařízení pomocí QR kódu.</p>
        </div>
      ) : (
        <div className="devices-flex-container">
          {devices.map((device) => {
            const typeInfo = getDeviceTypeInfo(device.device_type)
            const isAndroid = typeInfo.id === 'android';

            return (
              <div
                key={device.id}
                className="modern-device-card"
                onClick={() => onSelectDevice(device)}
              >
                <div className="card-top">
                  <div className="card-icon-wrapper"><DynamicIcon name={typeInfo.iconName} size={24} /></div>
                  <div className="card-meta">
                    <h3 className="card-title">{device.name}</h3>
                    <span className="card-subtitle">{typeInfo.label}</span>
                  </div>
                </div>

                <div className="card-status-row">
                  <span className={`status-pill ${device.is_online ? 'online' : 'offline'}`}>
                    {device.is_online ? 'Online' : 'Offline'}
                  </span>
                  <span className="last-seen">
                    {device.is_online ? '' : formatToLocalTime(device.last_seen)}
                  </span>
                </div>

                <div className="card-actions">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      const newName = prompt('Zadejte nový název zařízení:', device.name)
                      if (newName && newName !== device.name) {
                        handleRename(device.id, newName)
                      }
                    }}
                    className="card-btn edit"
                  >
                    <Edit size={14} style={{ marginRight: '6px' }} /> Upravit
                  </button>

                  {isAndroid && (
                    <>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleResetPin(device.id)
                        }}
                        className="card-btn edit"
                        title="Resetovat PIN"
                        style={{ color: 'var(--color-warning, #f59e0b)', borderColor: 'var(--color-warning, #f59e0b)' }}
                      >
                        <DynamicIcon name="unlock" size={14} style={{ marginRight: '6px' }} /> PIN
                      </button>
                      
                      {/* Device Owner activation button (when not active) */}
                      {!device.is_device_owner && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setDeviceOwnerSetupDevice(device)
                          }}
                          className="card-btn edit"
                          title="Aktivovat Device Owner"
                          style={{ color: 'var(--color-primary, #3b82f6)', borderColor: 'var(--color-primary, #3b82f6)' }}
                        >
                          <Shield size={14} style={{ marginRight: '6px' }} /> Aktivovat DO
                        </button>
                      )}
                      
                      {/* Device Owner deactivation button (when active) */}
                      {device.is_device_owner && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setDeactivateDevice(device)
                            setDeactivatePassword('')
                            setDeactivateError('')
                          }}
                          className="card-btn edit"
                          title="Deaktivovat Device Owner ochrany"
                          style={{ color: 'var(--color-error, #ef4444)', borderColor: 'var(--color-error, #ef4444)' }}
                        >
                          <ShieldOff size={14} style={{ marginRight: '6px' }} /> Deaktivovat DO
                        </button>
                      )}
                    </>
                  )}

                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDelete(device.id)
                    }}
                    className="card-btn delete"
                  >
                    <Trash2 size={14} style={{ marginRight: '6px' }} /> Odstranit
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Device Owner Setup Modal */}
      {deviceOwnerSetupDevice && (
        <div className="modal-overlay" onClick={() => setDeviceOwnerSetupDevice(null)}>
          <div className="modal-content device-owner-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Device Owner Setup</h2>
              <button className="modal-close" onClick={() => setDeviceOwnerSetupDevice(null)}>×</button>
            </div>
            <DeviceOwnerSetup
              deviceId={deviceOwnerSetupDevice.device_id}
              onComplete={async () => {
                // Notify backend that Device Owner was activated
                try {
                  await api.post(`/api/devices/${deviceOwnerSetupDevice.id}/device-owner-activated`)
                  await fetchDevices() // Refresh device list
                  setDeviceOwnerSetupDevice(null)
                } catch (err) {
                  console.error('Failed to notify backend:', err)
                }
              }}
              onCancel={() => setDeviceOwnerSetupDevice(null)}
            />
          </div>
        </div>
      )}

      {/* Device Owner Deactivation Confirmation Modal */}
      {deactivateDevice && (
        <div className="modal-overlay" onClick={() => setDeactivateDevice(null)}>
          <div className="modal-content deactivate-do-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Deaktivovat Device Owner</h2>
              <button className="modal-close" onClick={() => setDeactivateDevice(null)}>×</button>
            </div>
            
            <div className="deactivate-do-content">
              <div className="warning-box">
                <AlertTriangle size={24} />
                <div>
                  <strong>Upozorneni</strong>
                  <p>Toto odstraní všechny Device Owner ochrany ze zarizeni "{deactivateDevice.name}".</p>
                </div>
              </div>
              
              <div className="deactivate-info">
                <p><strong>Co se stane:</strong></p>
                <ul>
                  <li>Aplikaci FamilyEye bude mozne odinstalovat</li>
                  <li>Factory reset bude povolen</li>
                  <li>Safe Mode bude povolen</li>
                  <li>Force Stop bude povolen</li>
                  <li>USB debugging bude povolen</li>
                </ul>
              </div>
              
              <div className="password-confirm">
                <label>Zadejte heslo pro potvrzeni:</label>
                <input
                  type="password"
                  value={deactivatePassword}
                  onChange={(e) => setDeactivatePassword(e.target.value)}
                  placeholder="Vase heslo"
                  autoFocus
                />
              </div>
              
              {deactivateError && (
                <div className="error-message">{deactivateError}</div>
              )}
              
              <div className="modal-actions">
                <button 
                  className="btn-secondary"
                  onClick={() => setDeactivateDevice(null)}
                  disabled={deactivateLoading}
                >
                  Zrusit
                </button>
                <button 
                  className="btn-danger"
                  onClick={handleDeactivateDeviceOwner}
                  disabled={deactivateLoading || !deactivatePassword.trim()}
                >
                  {deactivateLoading ? 'Deaktivuji...' : 'Deaktivovat ochrany'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DeviceList
