import React, { useState, useEffect } from 'react'
import api from '../services/api'
import { formatToLocalTime } from '../utils/date'
import { getDeviceTypeInfo } from '../utils/formatting'
import { RefreshCw, Calendar, Smartphone, Trash2, Edit } from 'lucide-react'
import DynamicIcon from './DynamicIcon'
import './DeviceList.css'

const DeviceList = ({ onSelectDevice }) => {
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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
    </div>
  )
}

export default DeviceList
