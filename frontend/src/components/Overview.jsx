import React, { useState, useEffect } from 'react'
import api from '../services/api'
import { formatToLocalTime } from '../utils/date'
import './Overview.css'

const Overview = () => {
  const [devices, setDevices] = useState([])
  const [summaries, setSummaries] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      const devicesResponse = await api.get('/api/devices/')
      setDevices(devicesResponse.data)

      // Fetch summaries for all devices
      const summariesData = {}
      for (const device of devicesResponse.data) {
        try {
          const summaryResponse = await api.get(`/api/reports/device/${device.id}/summary`)
          summariesData[device.id] = summaryResponse.data
        } catch (err) {
          console.error(`Error fetching summary for device ${device.id}:`, err)
        }
      }
      setSummaries(summariesData)
    } catch (err) {
      console.error('Error fetching data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleInstantAction = async (deviceId, action, params = {}) => {
    try {
      let endpoint = ''

      switch (action) {
        case 'lock':
          endpoint = `/api/devices/${deviceId}/lock`
          break
        case 'unlock':
          endpoint = `/api/devices/${deviceId}/unlock`
          break
        case 'pause-internet':
          endpoint = `/api/devices/${deviceId}/pause-internet?duration_minutes=${params.duration || 60}`
          break
        case 'resume-internet':
          endpoint = `/api/devices/${deviceId}/resume-internet`
          break
        default:
          return
      }

      await api.post(endpoint)
      alert(`Akce "${action}" byla odeslána na zařízení`)
      fetchData()
    } catch (err) {
      console.error(`Error executing ${action}:`, err)
      alert(`Chyba při provádění akce: ${err.response?.data?.detail || err.message}`)
    }
  }

  if (loading) {
    return <div className="loading">Načítání přehledu...</div>
  }

  const totalUsageToday = Object.values(summaries).reduce((sum, s) => sum + (s.today_usage_seconds || 0), 0)
  const totalDevices = devices.length
  const activeDevices = devices.filter(d => d.is_active).length

  return (
    <div className="overview">
      <div className="overview-header">
        <h2>Přehled</h2>
        <button onClick={fetchData} className="refresh-button">
          Obnovit
        </button>
      </div>

      <div className="overview-stats">
        <div className="stat-card">
          <h3>Celkové zařízení</h3>
          <p className="stat-value">{totalDevices}</p>
        </div>
        <div className="stat-card">
          <h3>Aktivní zařízení</h3>
          <p className="stat-value">{activeDevices}</p>
        </div>
        <div className="stat-card">
          <h3>Celkový čas dnes</h3>
          <p className="stat-value">{Math.round(totalUsageToday / 3600 * 10) / 10} hodin</p>
        </div>
      </div>

      <div className="devices-overview">
        <h3>Zařízení</h3>
        {devices.length === 0 ? (
          <p className="empty">Žádná zařízení</p>
        ) : (
          <div className="devices-grid-overview">
            {devices.map((device) => {
              const summary = summaries[device.id]
              // Check if device is online
              const isOnline = device.is_online

              return (
                <div key={device.id} className="device-card-overview">
                  <div className="device-header">
                    <h4>{device.name}</h4>
                    <span className={`status-badge ${isOnline ? 'online' : 'offline'}`}>
                      {isOnline ? 'ONLINE' : 'OFFLINE'}
                    </span>
                  </div>

                  <div className="device-info">
                    <p className="device-type-badge">{device.device_type}</p>
                    {summary && (
                      <div className="device-stats">
                        <p>Dnes: {summary.today_usage_hours || 0} hodin</p>
                        <p>Aplikací: {summary.apps_used_today || 0}</p>
                        <p>Pravidel: {summary.active_rules || 0}</p>
                      </div>
                    )}
                    {device.last_seen && (
                      <p className="last-seen">
                        Naposledy: {formatToLocalTime(device.last_seen)}
                      </p>
                    )}
                  </div>

                  <div className="instant-actions">
                    <h4>Rychlé akce</h4>
                    <div className="actions-grid">
                      <button
                        onClick={() => handleInstantAction(device.id, 'lock')}
                        className="action-button lock"
                      >
                        Zamknout
                      </button>
                      <button
                        onClick={() => handleInstantAction(device.id, 'unlock')}
                        className="action-button unlock"
                      >
                        Odemknout
                      </button>
                      <button
                        onClick={() => handleInstantAction(device.id, 'pause-internet', { duration: 60 })}
                        className="action-button pause"
                      >
                        Pozastavit internet (1h)
                      </button>
                      <button
                        onClick={() => handleInstantAction(device.id, 'resume-internet')}
                        className="action-button resume"
                      >
                        Obnovit internet
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default Overview

