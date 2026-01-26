import React, { useState, useEffect } from 'react'
import api from '../services/api'
import { RefreshCw, X, Shield, Plus } from 'lucide-react'
import { 
  RuleCard, 
  HiddenAppsSection, 
  AppPicker, 
  ScheduleForm,
  INITIAL_FORM_DATA,
  SYSTEM_APP_PATTERNS 
} from './rules'
import './RuleEditor.css'

const RuleEditor = ({ deviceId }) => {
  const [devices, setDevices] = useState([])
  const [selectedDeviceId, setSelectedDeviceId] = useState(deviceId)
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)

  const [showForm, setShowForm] = useState(false)
  const [editingRuleId, setEditingRuleId] = useState(null)
  const [frequentApps, setFrequentApps] = useState([])
  const [allApps, setAllApps] = useState([])
  const [hiddenApps, setHiddenApps] = useState([])
  const [selectedApps, setSelectedApps] = useState([])
  const [appInputValue, setAppInputValue] = useState('')
  const [scheduleTarget, setScheduleTarget] = useState('apps')
  const [formData, setFormData] = useState(INITIAL_FORM_DATA)

  // Data fetching
  useEffect(() => { fetchDevices() }, [])

  useEffect(() => {
    if (selectedDeviceId) {
      fetchRules()
      fetchFrequentApps()
      fetchDeviceApps()
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
          return !SYSTEM_APP_PATTERNS.some(p => name.includes(p))
        })
        .slice(0, 8)
        .map(app => ({
          name: app.display_name || app.app_name,
          keyword: app.app_name,
          duration: app.duration_seconds
        }))
      setFrequentApps(apps)
    } catch (err) {
      setFrequentApps([])
    }
  }

  const fetchDeviceApps = async () => {
    if (!selectedDeviceId) return
    try {
      const response = await api.get(`/api/reports/device/${selectedDeviceId}/apps`)
      setAllApps(response.data || [])
    } catch (err) {
      setAllApps([])
    }
  }

  // Form handling
  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!selectedDeviceId) return

    // Validation
    if ((formData.rule_type === 'app_block' || formData.rule_type === 'time_limit') && selectedApps.length === 0) {
      alert('Prosim vyberte alespon jednu aplikaci')
      return
    }
    if (formData.rule_type === 'schedule' && scheduleTarget === 'apps' && selectedApps.length === 0) {
      alert('Prosim vyberte alespon jednu aplikaci')
      return
    }
    if (formData.rule_type === 'web_block' && !formData.website_url.trim()) {
      alert('Prosim zadejte URL webu')
      return
    }

    try {
      const appNameValue = formData.rule_type === 'schedule' && scheduleTarget === 'device'
        ? '' : selectedApps.join(',')

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
      alert('Chyba pri ukladani pravidla')
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
    setSelectedApps(rule.app_name ? rule.app_name.split(',').filter(a => a) : [])
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
    if (!appName) return
    const trimmed = appName.trim().toLowerCase()
    if (trimmed && !selectedApps.includes(trimmed)) {
      setSelectedApps([...selectedApps, trimmed])
    }
    setAppInputValue('')
  }

  const handleRemoveApp = (appName) => {
    setSelectedApps(selectedApps.filter(a => a !== appName))
  }

  // Render
  if (loading && devices.length === 0) {
    return <div className="loading">Nacitani...</div>
  }

  const currentDevice = devices.find(d => d.id === selectedDeviceId)
  const showAppPicker = formData.rule_type !== 'daily_limit' && 
    formData.rule_type !== 'web_block' && 
    formData.rule_type !== 'website_block' &&
    !(formData.rule_type === 'schedule' && scheduleTarget === 'device')

  return (
    <div className="rule-editor premium-card">
      {/* Header */}
      <div className="rule-editor-header">
        <div className="header-title-group">
          <h2>Sprava pravidel</h2>
          <span className="rules-count-badge">{rules.length}</span>
        </div>
        <div className="header-actions">
          <select
            value={selectedDeviceId || ''}
            onChange={(e) => setSelectedDeviceId(parseInt(e.target.value))}
            className="device-select"
          >
            <option value="">Vyberte zarizeni</option>
            {devices.map((device) => (
              <option key={device.id} value={device.id}>{device.name}</option>
            ))}
          </select>
          <div className="action-buttons-group">
            <button onClick={fetchRules} className="refresh-btn-icon" disabled={loading} title="Obnovit pravidla">
              <RefreshCw size={18} className={loading ? 'spinning' : ''} />
            </button>
            <button
              onClick={() => { setShowForm(!showForm); if (showForm) setEditingRuleId(null) }}
              className={`add-rule-btn ${showForm ? 'active' : ''}`}
            >
              {showForm ? <X size={18} /> : <Plus size={18} />}
              <span>{showForm ? 'Zrusit' : 'Nove pravidlo'}</span>
            </button>
          </div>
        </div>
      </div>

      {selectedDeviceId && (
        <>
          {/* Rule Form */}
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
                  <option value="time_limit">Absolutni denni limit (pro aplikaci)</option>
                  <option value="daily_limit">Celkovy denni limit zarizeni</option>
                  {currentDevice?.device_type !== 'android' && (
                    <option value="web_block">Blokovat web</option>
                  )}
                  <option value="schedule">Casovy rozvrh (blokovat vse v case)</option>
                </select>
              </div>

              <div className="form-group">
                <label>Nazev pravidla (volitelne)</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="napr. Skola, Vikend, Trenink"
                  className="input"
                />
              </div>

              {/* Web URL input */}
              {(formData.rule_type === 'website_block' || formData.rule_type === 'web_block') && (
                <div className="form-group">
                  <label>Webova adresa</label>
                  <input
                    type="text"
                    value={formData.website_url}
                    onChange={(e) => setFormData({ ...formData, website_url: e.target.value })}
                    placeholder="napr. tiktok.com nebo jen tiktok"
                    className="input"
                  />
                </div>
              )}

              {/* App Picker */}
              {showAppPicker && (
                <div className="form-group">
                  <label>Nazev aplikace</label>
                  <AppPicker
                    selectedApps={selectedApps}
                    onAddApp={handleAddApp}
                    onRemoveApp={handleRemoveApp}
                    inputValue={appInputValue}
                    onInputChange={setAppInputValue}
                    frequentApps={frequentApps}
                    allApps={allApps}
                  />
                </div>
              )}

              {/* Time Limit */}
              {(formData.rule_type === 'time_limit' || formData.rule_type === 'daily_limit') && (
                <div className="form-group">
                  <label>Absolutni denni limit (minuty)</label>
                  <small style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '0.85em' }}>
                    Urcuje maximalni povoleny cas pro kazdy den. V prehledu lze tento cas operativne navysit.
                  </small>
                  <input
                    type="number"
                    value={formData.time_limit}
                    onChange={(e) => setFormData({ ...formData, time_limit: e.target.value })}
                    placeholder="pocet minut za den"
                    className="input"
                  />
                </div>
              )}

              {/* Schedule Form */}
              {formData.rule_type === 'schedule' && (
                <div className="form-group">
                  <ScheduleForm
                    scheduleTarget={scheduleTarget}
                    onScheduleTargetChange={setScheduleTarget}
                    startTime={formData.schedule_start_time}
                    endTime={formData.schedule_end_time}
                    selectedDays={formData.schedule_days}
                    onStartTimeChange={(v) => setFormData({ ...formData, schedule_start_time: v })}
                    onEndTimeChange={(v) => setFormData({ ...formData, schedule_end_time: v })}
                    onDaysChange={(days) => setFormData({ ...formData, schedule_days: days })}
                  />
                </div>
              )}

              {/* Network Block Option */}
              {formData.rule_type === 'app_block' && (
                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '5px', padding: '10px', background: 'rgba(0,0,0,0.05)', borderRadius: '8px', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={formData.block_network}
                    onChange={(e) => setFormData({ ...formData, block_network: e.target.checked })}
                  />
                  <div>
                    <span style={{ fontWeight: 'bold' }}>Blokovat sitovy pristup</span><br />
                    <small>Zabrani aplikaci v pristupu k internetu uplne.</small>
                  </div>
                </label>
              )}

              <button type="submit" className="button button-success" style={{ marginTop: '15px' }}>
                {editingRuleId ? 'Aktualizovat pravidlo' : 'Ulozit pravidlo'}
              </button>
            </form>
          )}

          {/* Rules List */}
          <div className="rules-list">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
              <h3 style={{ margin: 0 }}>Aktivni pravidla ({rules.length})</h3>
            </div>
            {loading ? (
              <div className="loading-small">Nacitani pravidel...</div>
            ) : rules.length === 0 ? (
              <div className="rules-empty-state">
                <div className="empty-state-icon"><Shield size={48} /></div>
                <h3>Zadna aktivni pravidla</h3>
                <p>Pro toto zarizeni zatim nebyla nastavena zadna omezeni. Kliknete na tlacitko "Nove pravidlo" pro zacatek.</p>
              </div>
            ) : (
              <div className="rules-grid">
                {rules.map((rule) => (
                  <RuleCard key={rule.id} rule={rule} onEdit={handleEdit} onDelete={handleDelete} />
                ))}
              </div>
            )}
          </div>

          <HiddenAppsSection hiddenApps={hiddenApps} onRestoreApp={handleRestoreApp} />
        </>
      )}
    </div>
  )
}

export default RuleEditor
