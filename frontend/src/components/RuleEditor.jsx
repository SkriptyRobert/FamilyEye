import React, { useState, useEffect } from 'react'
import api from '../services/api'
import {
  RefreshCw, X, Globe, BarChart3, Monitor, Shield
} from 'lucide-react'
import DayPicker from './DayPicker'
import { RuleCard, HiddenAppsSection } from './rules'
import './RuleEditor.css'

// Fallback suggested apps (shown when no data available)
const DEFAULT_SUGGESTED_APPS = [
  { name: 'Epic Games', keyword: 'Epic' },
  { name: 'Steam', keyword: 'Steam' },
  { name: 'Discord', keyword: 'Discord' },
  { name: 'Chrome', keyword: 'Chrome' },
  { name: 'Roblox', keyword: 'Roblox' },
  { name: 'Minecraft', keyword: 'Minecraft' }
]

const INITIAL_FORM_DATA = {
  rule_type: 'app_block',
  name: '',
  app_name: '',
  website_url: '',
  time_limit: '',
  enabled: true,
  schedule_start_time: '',
  schedule_end_time: '',
  schedule_days: '',
  block_network: false
}

const RuleEditor = ({ deviceId }) => {
  const [devices, setDevices] = useState([])
  const [selectedDeviceId, setSelectedDeviceId] = useState(deviceId)
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)

  const [showForm, setShowForm] = useState(false)
  const [editingRuleId, setEditingRuleId] = useState(null)
  const [frequentApps, setFrequentApps] = useState([])
  const [hiddenApps, setHiddenApps] = useState([])
  const [selectedApps, setSelectedApps] = useState([])
  const [appInputValue, setAppInputValue] = useState('')
  const [scheduleTarget, setScheduleTarget] = useState('apps')
  const [formData, setFormData] = useState(INITIAL_FORM_DATA)

  useEffect(() => {
    fetchDevices()
  }, [])

  useEffect(() => {
    if (selectedDeviceId) {
      fetchRules()
      fetchFrequentApps()
    }
    fetchHiddenApps()
  }, [selectedDeviceId])

  const fetchHiddenApps = () => {
    try {
      const stored = localStorage.getItem('familyeye_user_blacklist')
      setHiddenApps(stored ? JSON.parse(stored) : [])
    } catch (e) {
      console.error('Failed to load hidden apps:', e)
    }
  }

  const handleRestoreApp = (appName) => {
    try {
      const stored = localStorage.getItem('familyeye_user_blacklist')
      let list = stored ? JSON.parse(stored) : []
      list = list.filter(item => item !== appName.toLowerCase())
      localStorage.setItem('familyeye_user_blacklist', JSON.stringify(list))
      setHiddenApps(list)
    } catch (e) {
      console.error('Failed to restore app:', e)
    }
  }

  const fetchDevices = async () => {
    try {
      const response = await api.get('/api/devices/')
      setDevices(response.data)
      if (response.data.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(response.data[0].id)
      }
    } catch (err) {
      console.error('Error fetching devices:', err)
    }
  }

  const fetchRules = async () => {
    if (!selectedDeviceId) return

    setLoading(true)
    try {
      const response = await api.get(`/api/rules/device/${selectedDeviceId}`)
      setRules(response.data)
    } catch (err) {
      console.error('Error fetching rules:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchFrequentApps = async () => {
    if (!selectedDeviceId) return

    try {
      const response = await api.get(`/api/reports/device/${selectedDeviceId}/summary`)
      const topApps = response.data?.top_apps || []

      const apps = topApps
        .filter(app => {
          const name = (app.app_name || '').toLowerCase()
          const skipPatterns = ['service', 'host', 'helper', 'system', 'windows', 'svchost']
          return !skipPatterns.some(p => name.includes(p))
        })
        .slice(0, 8)
        .map(app => ({
          name: app.display_name || app.app_name,
          keyword: app.app_name,
          duration: app.duration_seconds
        }))

      setFrequentApps(apps)
    } catch (err) {
      console.error('Error fetching frequent apps:', err)
      setFrequentApps([])
    }
  }

  const getSuggestedApps = () => {
    const allApps = [...frequentApps]

    DEFAULT_SUGGESTED_APPS.forEach(defaultApp => {
      const exists = allApps.some(
        app => app.keyword.toLowerCase() === defaultApp.keyword.toLowerCase()
      )
      if (!exists) {
        allApps.push(defaultApp)
      }
    })

    return allApps.slice(0, 12)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!selectedDeviceId) return

    // Validation
    if (formData.rule_type === 'app_block' || formData.rule_type === 'time_limit') {
      if (selectedApps.length === 0) {
        alert('Prosím vyberte alespoň jednu aplikaci')
        return
      }
    }
    if (formData.rule_type === 'schedule' && scheduleTarget === 'apps') {
      if (selectedApps.length === 0) {
        alert('Prosím vyberte alespoň jednu aplikaci')
        return
      }
    }
    if (formData.rule_type === 'web_block') {
      if (!formData.website_url.trim()) {
        alert('Prosím zadejte URL webu')
        return
      }
    }

    try {
      const appNameValue = formData.rule_type === 'schedule' && scheduleTarget === 'device'
        ? ''
        : selectedApps.join(',')

      const payload = {
        ...formData,
        app_name: appNameValue,
        device_id: selectedDeviceId,
        time_limit: formData.time_limit ? parseInt(formData.time_limit) : null
      }

      if (editingRuleId) {
        await api.put(`/api/rules/${editingRuleId}`, payload)
      } else {
        await api.post('/api/rules/', payload)
      }

      resetForm()
      fetchRules()
    } catch (err) {
      console.error('Error saving rule:', err)
      alert('Chyba při ukládání pravidla')
    }
  }

  const resetForm = () => {
    setShowForm(false)
    setEditingRuleId(null)
    setSelectedApps([])
    setAppInputValue('')
    setScheduleTarget('apps')
    setFormData(INITIAL_FORM_DATA)
  }

  const handleEdit = (rule) => {
    setEditingRuleId(rule.id)

    let apps = []
    if (rule.app_name) {
      apps = rule.app_name.split(',').filter(a => a)
    }

    setSelectedApps(apps)

    if (rule.rule_type === 'schedule') {
      setScheduleTarget(!rule.app_name ? 'device' : 'apps')
    }

    setFormData({
      rule_type: rule.rule_type,
      name: rule.name || '',
      app_name: rule.app_name || '',
      website_url: rule.website_url || '',
      time_limit: rule.time_limit || '',
      enabled: rule.enabled,
      schedule_start_time: rule.schedule_start_time || '',
      schedule_end_time: rule.schedule_end_time || '',
      schedule_days: rule.schedule_days || '',
      block_network: rule.block_network || false
    })

    setShowForm(true)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleDelete = async (ruleId) => {
    try {
      await api.delete(`/api/rules/${ruleId}`)
      await fetchRules()
    } catch (err) {
      console.error('Error deleting rule:', err)
    }
  }

  const handleAddApp = (appName) => {
    const trimmed = appName.trim().toLowerCase()
    if (trimmed && !selectedApps.includes(trimmed)) {
      setSelectedApps([...selectedApps, trimmed])
    }
    setAppInputValue('')
  }

  const handleRemoveApp = (appName) => {
    setSelectedApps(selectedApps.filter(a => a !== appName))
  }

  const handleAppInputKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAddApp(appInputValue)
    }
  }

  const handleSuggestedClick = (app) => {
    handleAddApp(app.keyword)
  }

  if (loading && devices.length === 0) {
    return <div className="loading">Načítání...</div>
  }

  const currentDevice = devices.find(d => d.id === selectedDeviceId)

  return (
    <div className="rule-editor">
      <div className="rule-editor-header">
        <h2>Správa pravidel</h2>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <select
            value={selectedDeviceId || ''}
            onChange={(e) => setSelectedDeviceId(parseInt(e.target.value))}
            className="device-select"
          >
            <option value="">Vyberte zařízení</option>
            {devices.map((device) => (
              <option key={device.id} value={device.id}>
                {device.name}
              </option>
            ))}
          </select>
          <button onClick={fetchRules} className="button" style={{ padding: '8px 12px' }} title="Obnovit pravidla">
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {selectedDeviceId && (
        <>
          <div style={{ marginBottom: '20px' }}>
            <button
              onClick={() => {
                setShowForm(!showForm)
                if (showForm) setEditingRuleId(null)
              }}
              className={`button ${showForm ? 'button-secondary' : ''}`}
              style={{ width: '100%', padding: '12px', fontWeight: 'bold' }}
            >
              {showForm ? <><X size={16} style={{ marginRight: '8px' }} /> Zrušit {editingRuleId ? 'úpravu' : 'přidávání'}</> : '+ Přidat nové pravidlo'}
            </button>
          </div>

          {showForm && (
            <form onSubmit={handleSubmit} className="rule-form premium-card">
              <div className="form-group">
                <label>Typ pravidla</label>
                <select
                  value={formData.rule_type}
                  onChange={(e) => setFormData({ ...formData, rule_type: e.target.value })}
                  className="input"
                >
                  <option value="app_block">Blokovat aplikaci</option>
                  <option value="time_limit">Absolutní denní limit (pro aplikaci)</option>
                  <option value="daily_limit">Celkový denní limit zařízení</option>
                  {currentDevice?.device_type !== 'android' && (
                    <option value="web_block">Blokovat web</option>
                  )}
                  <option value="schedule">Časový rozvrh (blokovat vše v čase)</option>
                </select>
              </div>

              <div className="form-group">
                <label>Název pravidla (volitelné)</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="např. Škola, Víkend, Trénink"
                  className="input"
                />
              </div>

              {formData.rule_type !== 'daily_limit' && !(formData.rule_type === 'schedule' && scheduleTarget === 'device') && (
                <div className="form-group">
                  <label>{(formData.rule_type === 'website_block' || formData.rule_type === 'web_block') ? 'Webová adresa' : 'Název aplikace'}</label>
                  {(formData.rule_type === 'website_block' || formData.rule_type === 'web_block') ? (
                    <input
                      type="text"
                      value={formData.website_url}
                      onChange={(e) => setFormData({ ...formData, website_url: e.target.value })}
                      placeholder="např. tiktok.com nebo jen tiktok"
                      className="input"
                    />
                  ) : (
                    <>
                      {/* Selected Apps Chips */}
                      {selectedApps.length > 0 && (
                        <div className="selected-apps-chips">
                          {selectedApps.map(app => (
                            <span key={app} className="app-chip">
                              {app}
                              <X
                                size={14}
                                onClick={() => handleRemoveApp(app)}
                                style={{ cursor: 'pointer', marginLeft: '4px' }}
                              />
                            </span>
                          ))}
                        </div>
                      )}

                      <input
                        type="text"
                        value={appInputValue}
                        onChange={(e) => setAppInputValue(e.target.value)}
                        onKeyDown={handleAppInputKeyDown}
                        placeholder={selectedApps.length > 0 ? "Přidat další aplikaci..." : "Název (např. Epic, Chrome, Minecraft)"}
                        className="input"
                      />

                      <div className="suggested-apps" style={{ marginTop: '10px' }}>
                        <small style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>
                          {frequentApps.length > 0 ? <><BarChart3 size={12} style={{ marginRight: '4px' }} /> Nejpoužívanější aplikace:</> : 'Časté aplikace:'}
                        </small>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                          {getSuggestedApps().map(app => (
                            <button
                              key={app.keyword}
                              type="button"
                              className={`tag-button ${selectedApps.includes(app.keyword.toLowerCase()) ? 'selected' : ''}`}
                              onClick={() => handleSuggestedClick(app)}
                              title={app.duration ? `Použito: ${Math.round(app.duration / 60)} min` : ''}
                              disabled={selectedApps.includes(app.keyword.toLowerCase())}
                            >
                              {app.name}
                            </button>
                          ))}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}

              {(formData.rule_type === 'time_limit' || formData.rule_type === 'daily_limit') && (
                <div className="form-group">
                  <label>Absolutní denní limit (minuty)</label>
                  <small style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '0.85em' }}>
                    Určuje maximální povolený čas pro každý den. V přehledu lze tento čas operativně navýšit.
                  </small>
                  <input
                    type="number"
                    value={formData.time_limit}
                    onChange={(e) => setFormData({ ...formData, time_limit: e.target.value })}
                    placeholder="počet minut za den"
                    className="input"
                  />
                </div>
              )}

              {formData.rule_type === 'schedule' && (
                <div className="form-group">
                  <label>Rozvrh platí pro:</label>
                  <div className="schedule-target-selector">
                    <label className={`radio-option ${scheduleTarget === 'device' ? 'selected' : ''}`}>
                      <input
                        type="radio"
                        name="scheduleTarget"
                        value="device"
                        checked={scheduleTarget === 'device'}
                        onChange={(e) => setScheduleTarget(e.target.value)}
                      />
                      <Monitor size={16} />
                      <span>Celé zařízení</span>
                    </label>
                    <label className={`radio-option ${scheduleTarget === 'apps' ? 'selected' : ''}`}>
                      <input
                        type="radio"
                        name="scheduleTarget"
                        value="apps"
                        checked={scheduleTarget === 'apps'}
                        onChange={(e) => setScheduleTarget(e.target.value)}
                      />
                      <Shield size={16} />
                      <span>Vybrané aplikace</span>
                    </label>
                  </div>

                  <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
                    <div style={{ flex: 1 }}>
                      <label>Od</label>
                      <input
                        type="time"
                        value={formData.schedule_start_time}
                        onChange={(e) => setFormData({ ...formData, schedule_start_time: e.target.value })}
                        className="input"
                      />
                    </div>
                    <div style={{ flex: 1 }}>
                      <label>Do</label>
                      <input
                        type="time"
                        value={formData.schedule_end_time}
                        onChange={(e) => setFormData({ ...formData, schedule_end_time: e.target.value })}
                        className="input"
                      />
                    </div>
                  </div>
                  <label style={{ marginTop: '10px' }}>Dny v týdnu</label>
                  <DayPicker
                    selectedDays={formData.schedule_days}
                    onChange={(days) => setFormData({ ...formData, schedule_days: days })}
                  />
                </div>
              )}

              {formData.rule_type === 'app_block' && (
                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '5px', padding: '10px', background: 'rgba(0,0,0,0.05)', borderRadius: '8px', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={formData.block_network}
                    onChange={(e) => setFormData({ ...formData, block_network: e.target.checked })}
                  />
                  <div>
                    <span style={{ fontWeight: 'bold' }}>Blokovat síťový přístup</span><br />
                    <small>Zabrání aplikaci v přístupu k internetu úplně.</small>
                  </div>
                </label>
              )}

              <button type="submit" className="button button-success" style={{ marginTop: '15px' }}>
                {editingRuleId ? 'Aktualizovat pravidlo' : 'Uložit pravidlo'}
              </button>
            </form>
          )}

          <div className="rules-list">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
              <h3 style={{ margin: 0 }}>Aktivní pravidla ({rules.length})</h3>
            </div>

            {loading ? (
              <div className="loading-small">Načítání pravidel...</div>
            ) : rules.length === 0 ? (
              <p className="empty">Žádná pravidla pro toto zařízení.</p>
            ) : (
              <div className="rules-grid">
                {rules.map((rule) => (
                  <RuleCard
                    key={rule.id}
                    rule={rule}
                    onEdit={handleEdit}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            )}
          </div>

          <HiddenAppsSection
            hiddenApps={hiddenApps}
            onRestoreApp={handleRestoreApp}
          />
        </>
      )}
    </div>
  )
}

export default RuleEditor
