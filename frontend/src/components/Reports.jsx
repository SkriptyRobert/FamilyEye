import React, { useState, useEffect, lazy, Suspense } from 'react'
import api from '../services/api'
import {
  formatDuration,
  formatRelativeTime,
  filterAppsForDisplay,
  getAppIcon,
  getLimitStatus
} from '../utils/formatting'
// NOTE: App filtering moved to backend (Path A architecture)
import { BarChart3, Smartphone, Monitor, Inbox } from 'lucide-react'
import DynamicIcon from './DynamicIcon'
import './Reports.css'
import SmartInsights from './SmartInsights'

// Lazy load chart components
const ActivityHeatmap = lazy(() => import('./charts/ActivityHeatmap'))
const WeeklyBarChart = lazy(() => import('./charts/WeeklyBarChart'))
const AppDetailsModal = lazy(() => import('./charts/AppDetailsModal'))

// Loading placeholder
const ChartLoading = () => (
  <div className="chart-loading-placeholder">
    <div className="loading-spinner"></div>
  </div>
)

const Reports = ({ deviceId }) => {
  const [devices, setDevices] = useState([])
  const [selectedDeviceId, setSelectedDeviceId] = useState(deviceId)
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  // NOTE: appConfig removed - backend handles filtering now
  const [selectedApp, setSelectedApp] = useState(null)
  const [heatmapDays, setHeatmapDays] = useState(7)
  const [selectedDateFilter, setSelectedDateFilter] = useState(null)



  useEffect(() => {
    // NOTE: initAppConfig removed - backend handles filtering
    fetchDevices()
  }, [])

  useEffect(() => {
    if (selectedDeviceId) {
      fetchAllData()
      const interval = setInterval(fetchAllData, 30000)
      return () => clearInterval(interval)
    }
  }, [selectedDeviceId, selectedDateFilter])

  const handleDateClick = (dateStr) => {
    if (selectedDateFilter === dateStr) {
      setSelectedDateFilter(null)
    } else {
      setSelectedDateFilter(dateStr)
    }
  }

  const fetchDevices = async () => {
    try {
      const response = await api.get('/api/devices/')
      setDevices(response.data)
      if (response.data.length > 0 && !selectedDeviceId) {
        const activeDevice = response.data.find(d => d.last_seen) || response.data[0]
        setSelectedDeviceId(activeDevice.id)
      }
    } catch (err) {
      console.error('Error fetching devices:', err)
    }
  }

  const fetchAllData = async () => {
    if (!selectedDeviceId) return
    setLoading(true)

    try {
      const summaryRes = await api.get(`/api/reports/device/${selectedDeviceId}/summary`, {
        params: selectedDateFilter ? { date: selectedDateFilter } : {}
      })
      setSummary(summaryRes.data)
    } catch (err) {
      console.error('Error fetching data:', err)
    } finally {
      setLoading(false)
    }
  }

  const getFilteredApps = () => {
    if (!summary?.top_apps) return []
    // NOTE: Backend filters data, pass null config
    return filterAppsForDisplay(summary.top_apps, { minDurationSeconds: 60, limit: 6, config: null })
  }

  // Get top app of the day
  const getTopApp = () => {
    const filtered = getFilteredApps()
    if (filtered.length === 0) return null
    return filtered[0]
  }

  // Calculate comparison with yesterday
  const getComparisonBadge = () => {
    if (!summary) return null

    const todaySeconds = summary.today_usage_seconds || 0
    const yesterdaySeconds = summary.yesterday_usage_seconds || 0

    if (yesterdaySeconds === 0 && todaySeconds === 0) return null

    const diffSeconds = todaySeconds - yesterdaySeconds
    const diffMinutes = Math.abs(Math.round(diffSeconds / 60))

    if (diffMinutes < 1) return null

    return {
      isMore: diffSeconds > 0,
      minutes: diffMinutes,
      text: diffSeconds > 0 ? `▲ +${formatDuration(Math.abs(diffSeconds), true)}` : `▼ -${formatDuration(Math.abs(diffSeconds), true)}`
    }
  }

  const filteredApps = getFilteredApps()
  const topApp = getTopApp()
  const comparison = getComparisonBadge()

  if (loading && !summary) {
    return (
      <div className="reports-container">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Načítání statistik...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="reports-container bento-layout">
      {/* Header */}
      <div className="reports-header">
        <div className="header-left">
          <h2><BarChart3 size={20} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> Statistiky</h2>
        </div>

        <div className="header-controls">

          <select
            value={selectedDeviceId || ''}
            onChange={(e) => {
              setSelectedDeviceId(parseInt(e.target.value))
              setSelectedDateFilter(null)
            }}
            className="device-select"
          >
            <option value="">Vyberte zařízení</option>
            {devices.map((device) => (
              <option key={device.id} value={device.id}>
                {device.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {selectedDeviceId && summary && (
        <div className="bento-grid">

          {/* === TOP ROW: 3 Metric Cards === */}

          {/* Card 1: Total Time Today - HERO */}
          <div className="bento-card metric-card total-time">
            <span className="metric-label">Celkový čas {selectedDateFilter ? new Date(selectedDateFilter).toLocaleDateString('cs-CZ') : 'dnes'}</span>
            <span className="metric-value huge">
              {formatDuration(summary.today_usage_seconds || 0, true)}
            </span>
            {comparison && (
              <span className={`metric-badge ${comparison.isMore ? 'badge-red' : 'badge-green'}`}>
                {comparison.text} oproti včerejšku
              </span>
            )}
          </div>

          {/* Card 2: Top App */}
          <div className="bento-card metric-card top-app">
            <span className="metric-label">Nejvíce používáno</span>
            {topApp ? (
              <>
                <div className="top-app-display">
                  <div className="top-app-icon"><DynamicIcon name={topApp.icon} size={20} /></div>
                  <span className="metric-value app-name">{topApp.display_name}</span>
                </div>
                <span className="metric-subvalue">
                  {formatDuration(topApp.duration_seconds, true)} {selectedDateFilter ? new Date(selectedDateFilter).toLocaleDateString('cs-CZ') : 'dnes'}
                </span>
              </>
            ) : (
              <span className="metric-value muted">Žádná aktivita</span>
            )}
          </div>

          {/* Card 3: Smart Insights Analytics */}
          <SmartInsights insights={summary?.insights} />

          {/* === MIDDLE ROW: Weekly Chart (60%) + Top Apps (40%) === */}

          {/* Weekly Bar Chart */}
          <div className="bento-card chart-card weekly-chart">
            <Suspense fallback={<ChartLoading />}>
              <WeeklyBarChart
                deviceId={selectedDeviceId}
                onDateSelect={handleDateClick}
                selectedDate={selectedDateFilter}
              />
            </Suspense>
          </div>

          {/* Top Apps List - Enhanced */}
          <div className="bento-card apps-card">
            <h3><Smartphone size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Aplikace {selectedDateFilter ? new Date(selectedDateFilter).toLocaleDateString('cs-CZ') : 'dnes'}</h3>
            <div className="apps-list">
              {filteredApps.length > 0 ? (
                filteredApps.map((app, idx) => {
                  const maxDuration = filteredApps[0]?.duration_seconds || 1
                  const percentage = Math.round((app.duration_seconds / maxDuration) * 100)
                  const colors = ['#6366f1', '#a855f7', '#ec4899', '#f97316', '#10b981', '#06b6d4']
                  const color = colors[idx % colors.length]

                  // Check if this app has a limit
                  const appLimit = summary.apps_with_limits?.find(
                    l => l.app_name.toLowerCase() === (app.app_name || app.display_name).toLowerCase()
                  )
                  const limitInfo = appLimit ? getLimitStatus(app.duration_seconds, appLimit.limit_minutes) : null

                  return (
                    <div
                      key={idx}
                      className="app-item clickable-app-report"
                      onClick={() => setSelectedApp(app.app_name || app.display_name)}
                      title="Klikněte pro zobrazení detailu"
                    >
                      <div className="app-row">
                        <div className="app-icon-name">
                          <div className="app-icon"><DynamicIcon name={app.icon} size={18} /></div>
                          <span className="app-name">{app.display_name}</span>
                        </div>
                        <div className="app-meta-group">
                          <span className="app-duration">
                            {formatDuration(app.duration_seconds, true)}
                          </span>
                          <span className="chevron-icon">›</span>
                        </div>
                      </div>

                      {/* Progress bar */}
                      <div className="app-bar-container">
                        <div
                          className="app-bar"
                          style={{ width: `${percentage}%`, backgroundColor: color }}
                        ></div>
                      </div>

                      {/* Limit indicator if exists */}
                      {limitInfo && limitInfo.hasLimit && (
                        <div className="app-limit-row">
                          <div className="app-limit-bar-container">
                            <div
                              className={`app-limit-bar ${limitInfo.status}`}
                              style={{ width: `${limitInfo.percentage}%` }}
                            ></div>
                          </div>
                          <span className={`app-limit-text ${limitInfo.status}`}>
                            {limitInfo.percentage}% z limitu
                          </span>
                        </div>
                      )}
                    </div>
                  )
                })
              ) : (
                <div className="no-apps">
                  <Inbox size={24} className="no-apps-icon" />
                  <span>Zatím žádná aktivita</span>
                </div>
              )}
            </div>
          </div>

          {/* === BOTTOM ROW: Activity Heatmap === */}
          <div className="bento-card heatmap-card">
            <Suspense fallback={<ChartLoading />}>
              <ActivityHeatmap
                deviceId={selectedDeviceId}
                days={heatmapDays}
                onDaysChange={setHeatmapDays}
                largerDots={true}
              />
            </Suspense>
          </div>

          {/* Running Processes Panel - Always Visible */}
          <div className="process-monitor-panel">
            <div className="monitor-header">
              <div className="monitor-title">
                <span className={`pulse-dot ${(summary.running_processes?.length > 0) ? 'active' : 'inactive'}`}></span>
                <h4><Monitor size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Aktivní aplikace</h4>
                <span className="process-count">{summary.running_processes?.length || 0}</span>
              </div>
              <span className="monitor-timestamp">
                {summary.running_processes_updated
                  ? formatRelativeTime(summary.running_processes_updated)
                  : '...'}
              </span>
            </div>

            <div className="process-table">
              <div className="process-table-header">
                <span className="col-name">APLIKACE</span>
                <span className="col-status">STAV</span>
              </div>
              <div className="process-table-body">
                {summary.running_processes && summary.running_processes.length > 0 ? (
                  summary.running_processes.map((process, index) => (
                    <div key={index} className="process-row">
                      <span className="col-name">{process}</span>
                      <span className="col-status running">⬤ BĚŽÍ</span>
                    </div>
                  ))
                ) : (
                  <div className="process-row empty-state">
                    <span className="col-name muted" style={{ padding: '12px', textAlign: 'center', width: '100%' }}>
                      Žádné sledované procesy nebyly detekovány
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>


          {/* Quick Stats Footer */}
          <div className="bento-footer">
            <div className="footer-stat">
              <span className="footer-value">{filteredApps.length}</span>
              <span className="footer-label">aplikací</span>
            </div>
            <div className="footer-stat">
              <span className="footer-value">{summary.active_rules || 0}</span>
              <span className="footer-label">pravidel</span>
            </div>
            <div className="footer-stat">
              <span className="footer-value">{formatRelativeTime(summary.last_seen)}</span>
              <span className="footer-label">naposledy online</span>
            </div>
          </div>
        </div>
      )}

      {/* App Details Modal */}
      {
        selectedApp && (
          <Suspense fallback={<ChartLoading />}>
            <AppDetailsModal
              deviceId={selectedDeviceId}
              appName={selectedApp}
              onClose={() => setSelectedApp(null)}
            />
          </Suspense>
        )
      }
    </div >
  )
}

export default Reports
