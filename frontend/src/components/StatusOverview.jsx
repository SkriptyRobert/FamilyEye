import React, { useState, useEffect, useCallback, useRef } from 'react'
import api from '../services/api'
import {
    formatDuration,
    formatRelativeTime,
    formatTimestamp,
    getDeviceState,
    getDataFreshness,
    getDeviceTypeInfo,
    getLimitStatus,
    filterSystemApps,
    formatLimitText,
    mapAppName
} from '../utils/formatting'
// NOTE: App filtering moved to backend (Path A architecture)
import DynamicIcon from './DynamicIcon'
import {
    Monitor,
    Smartphone,
    Lock,
    Unlock,
    Globe,
    AlertTriangle,
    CheckCircle,
    Clock,
    Calendar,
    RefreshCw,
    WifiOff,
    XCircle,
    CircleDot,
    Wifi,
    EyeOff,
    X,
    Check,
    Camera,
    Maximize2
} from 'lucide-react'
import './StatusOverview.css'

const StatusOverview = () => {
    const [devices, setDevices] = useState([])
    const [summaries, setSummaries] = useState({})
    const [rules, setRules] = useState({})
    const [loading, setLoading] = useState(true)
    // NOTE: appConfig removed - backend handles filtering now
    const [error, setError] = useState(null)
    const [lastFetch, setLastFetch] = useState(null)
    const [actionPending, setActionPending] = useState({})
    const [actionFeedback, setActionFeedback] = useState({})
    const [expandedDevice, setExpandedDevice] = useState(null)
    const [deviceFilter, setDeviceFilter] = useState('all') // all, pc, phone
    const [showAllAppsModal, setShowAllAppsModal] = useState(null) // deviceId or null
    const [showScreenshotModal, setShowScreenshotModal] = useState(null) // deviceId or null

    const fetchIntervalRef = useRef(null)

    const fetchData = useCallback(async (showLoading = false) => {
        if (showLoading) setLoading(true)
        setError(null)

        try {
            const devicesResponse = await api.get('/api/devices/')
            const devicesList = devicesResponse.data
            setDevices(devicesList)

            // Fetch summaries and rules for all devices in parallel
            const summaryPromises = devicesList.map(device =>
                api.get(`/api/reports/device/${device.id}/summary`)
                    .then(res => ({ deviceId: device.id, data: res.data }))
                    .catch(() => ({ deviceId: device.id, data: null }))
            )

            const rulesPromises = devicesList.map(device =>
                api.get(`/api/rules/device/${device.id}`)
                    .then(res => ({ deviceId: device.id, data: res.data }))
                    .catch(() => ({ deviceId: device.id, data: [] }))
            )

            const [summaryResults, rulesResults] = await Promise.all([
                Promise.all(summaryPromises),
                Promise.all(rulesPromises)
            ])

            const summariesData = {}
            summaryResults.forEach(result => {
                if (result.data) summariesData[result.deviceId] = result.data
            })
            setSummaries(summariesData)

            const rulesData = {}
            rulesResults.forEach(result => {
                rulesData[result.deviceId] = result.data || []
            })
            setRules(rulesData)

            setLastFetch(new Date())
        } catch (err) {
            console.error('Error fetching data:', err)
            setError('Nepodařilo se načíst data ze serveru')
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        // NOTE: initAppConfig removed - backend handles filtering
        fetchData(true)
        fetchIntervalRef.current = setInterval(() => fetchData(false), 30000)
        return () => {
            if (fetchIntervalRef.current) clearInterval(fetchIntervalRef.current)
        }
    }, [fetchData])

    const handleQuickAction = async (deviceId, action) => {
        const actionKey = `${deviceId}-${action}`
        setActionPending(prev => ({ ...prev, [actionKey]: true }))
        setActionFeedback(prev => ({ ...prev, [actionKey]: { status: 'sending', message: 'Odesílám příkaz...' } }))

        try {
            let endpoint = ''
            let successMessage = ''

            switch (action) {
                case 'lock':
                    endpoint = `/api/devices/${deviceId}/lock`
                    successMessage = 'Zařízení zamčeno'
                    break
                case 'unlock':
                    endpoint = `/api/devices/${deviceId}/unlock`
                    successMessage = 'Zařízení odemčeno'
                    break
                case 'pause-internet':
                    endpoint = `/api/devices/${deviceId}/pause-internet?duration_minutes=60`
                    successMessage = 'Internet pozastaven'
                    break
                case 'resume-internet':
                    endpoint = `/api/devices/${deviceId}/resume-internet`
                    successMessage = 'Internet obnoven'
                    break
                case 'screenshot':
                    endpoint = `/api/devices/${deviceId}/request-screenshot`
                    successMessage = 'Požadavek na screenshot odeslán'
                    break
                default:
                    return
            }

            await api.post(endpoint)

            setActionFeedback(prev => ({ ...prev, [actionKey]: { status: 'success', message: successMessage } }))

            // Clear feedback after 3 seconds
            setTimeout(() => {
                setActionFeedback(prev => ({ ...prev, [actionKey]: null }))
            }, 3000)

            // Refresh data
            setTimeout(() => fetchData(false), 500)
        } catch (err) {
            setActionFeedback(prev => ({
                ...prev,
                [actionKey]: { status: 'error', message: err.response?.data?.detail || 'Příkaz selhal' }
            }))
            setTimeout(() => {
                setActionFeedback(prev => ({ ...prev, [actionKey]: null }))
            }, 5000)
        } finally {
            setActionPending(prev => ({ ...prev, [actionKey]: false }))
        }
    }

    // Quick action: Adjust limit (add/subtract time)
    const handleAdjustLimit = async (deviceId, appName, adjustMinutes) => {
        const actionKey = `${deviceId}-adjust-${appName}`
        setActionPending(prev => ({ ...prev, [actionKey]: true }))
        setActionFeedback(prev => ({ ...prev, [actionKey]: { status: 'sending', message: 'Upravuji limit...' } }))

        try {
            // Find existing rule for this app
            const deviceRules = rules[deviceId] || []
            const existingRule = deviceRules.find(r =>
                (r.rule_type === 'time_limit' || r.rule_type === 'app_time_limit') &&
                (r.app_name?.toLowerCase() === appName.toLowerCase() ||
                    r.target?.toLowerCase() === appName.toLowerCase())
            )

            if (existingRule) {
                // Update existing rule with new limit
                const newLimit = Math.max(5, (existingRule.time_limit || existingRule.limit_minutes || 30) + adjustMinutes)
                await api.put(`/api/rules/${existingRule.id}`, {
                    ...existingRule,
                    time_limit: newLimit,
                    limit_minutes: newLimit
                })
                setActionFeedback(prev => ({
                    ...prev,
                    [actionKey]: { status: 'success', message: `Limit ${adjustMinutes > 0 ? 'prodloužen' : 'zkrácen'} na ${newLimit} min` }
                }))
            } else {
                // Create new time limit rule
                await api.post('/api/rules/', {
                    device_id: deviceId,
                    rule_type: 'time_limit',
                    app_name: appName,
                    time_limit: Math.max(5, 30 + adjustMinutes),
                    enabled: true
                })
                setActionFeedback(prev => ({
                    ...prev,
                    [actionKey]: { status: 'success', message: 'Nový limit vytvořen' }
                }))
            }

            setTimeout(() => {
                setActionFeedback(prev => ({ ...prev, [actionKey]: null }))
            }, 3000)
            setTimeout(() => fetchData(false), 500)
        } catch (err) {
            console.error('Error adjusting limit:', err)
            setActionFeedback(prev => ({
                ...prev,
                [actionKey]: { status: 'error', message: 'Chyba při úpravě limitu' }
            }))
            setTimeout(() => {
                setActionFeedback(prev => ({ ...prev, [actionKey]: null }))
            }, 5000)
        } finally {
            setActionPending(prev => ({ ...prev, [actionKey]: false }))
        }
    }

    // Quick action: Block or set limit for an app
    // For limits: ADD the selected time to current usage (e.g., 25min used + 30m limit = 55min total)
    const handleAppQuickAction = async (deviceId, appName, action) => {
        const actionKey = `${deviceId}-app-${appName}-${action}`
        setActionPending(prev => ({ ...prev, [actionKey]: true }))

        const actionMessages = {
            'block': 'Blokuji aplikaci...',
            'limit-30': 'Nastavuji limit +30 min...',
            'limit-60': 'Nastavuji limit +60 min...',
            'limit-120': 'Nastavuji limit +2 hodiny...'
        }
        setActionFeedback(prev => ({ ...prev, [actionKey]: { status: 'sending', message: actionMessages[action] || 'Zpracovávám...' } }))

        try {
            let ruleData = {
                device_id: deviceId,
                app_name: appName,
                enabled: true
            }

            // Find existing rule first to avoid duplicates
            const deviceRules = rules[deviceId] || []
            const existingRule = deviceRules.find(r =>
                (r.rule_type === 'time_limit' || r.rule_type === 'app_time_limit' || r.rule_type === 'app_block') &&
                (r.app_name?.toLowerCase() === appName.toLowerCase() || r.target?.toLowerCase() === appName.toLowerCase())
            )

            if (existingRule) {
                // Update existing rule
                if (action === 'block') {
                    await api.put(`/api/rules/${existingRule.id}`, {
                        ...existingRule,
                        rule_type: 'app_block',
                        enabled: true
                    })
                    ruleData = { ...existingRule, rule_type: 'app_block' } // for feedback
                } else {
                    // Add time to existing limit
                    const addMinutes = parseInt(action.split('-')[1]) || 60
                    // If switching from block to limit, start with 0 + addMinutes? Or some default?
                    // Assuming base is existing limit or 0
                    const currentLimit = (existingRule.rule_type === 'app_block') ? 0 : (existingRule.time_limit || existingRule.limit_minutes || 0)
                    const newLimit = currentLimit + addMinutes

                    await api.put(`/api/rules/${existingRule.id}`, {
                        ...existingRule,
                        rule_type: 'time_limit',
                        time_limit: newLimit,
                        enabled: true
                    })
                    ruleData = { ...existingRule, rule_type: 'time_limit', time_limit: newLimit } // for feedback
                }
            } else {
                // Create new rule
                if (action === 'block') {
                    ruleData.rule_type = 'app_block'
                } else {
                    // Get current usage for this app to calculate proper limit
                    const summary = summaries[deviceId]
                    const topApps = summary?.top_apps || []
                    const appUsage = topApps.find(a =>
                        a.app_name?.toLowerCase() === appName.toLowerCase() ||
                        a.display_name?.toLowerCase() === appName.toLowerCase()
                    )
                    const currentUsageMinutes = Math.ceil((appUsage?.duration_seconds || 0) / 60)

                    // ADD the limit to current usage (e.g., used 25min + 30min limit = 55min total limit)
                    const addMinutes = parseInt(action.split('-')[1]) || 60
                    const totalLimitMinutes = currentUsageMinutes + addMinutes

                    ruleData.rule_type = 'time_limit'
                    ruleData.time_limit = totalLimitMinutes
                }

                await api.post('/api/rules/', ruleData)
            }

            const successMessages = {
                'block': `${appName} zablokována`,
                'limit-30': `+30 min pro ${appName} (celkem ${ruleData.time_limit}m)`,
                'limit-60': `+60 min pro ${appName} (celkem ${ruleData.time_limit}m)`,
                'limit-120': `+2h pro ${appName} (celkem ${ruleData.time_limit}m)`
            }
            setActionFeedback(prev => ({
                ...prev,
                [actionKey]: { status: 'success', message: successMessages[action] || 'Hotovo' }
            }))

            setTimeout(() => {
                setActionFeedback(prev => ({ ...prev, [actionKey]: null }))
            }, 3000)
            setTimeout(() => fetchData(false), 500)
        } catch (err) {
            console.error('Error with app action:', err)
            setActionFeedback(prev => ({
                ...prev,
                [actionKey]: { status: 'error', message: 'Chyba při nastavení pravidla' }
            }))
            setTimeout(() => {
                setActionFeedback(prev => ({ ...prev, [actionKey]: null }))
            }, 5000)
        } finally {
            setActionPending(prev => ({ ...prev, [actionKey]: false }))
        }
    }

    // Filter devices by type
    const filteredDevices = devices.filter(device => {
        if (deviceFilter === 'all') return true
        const typeInfo = getDeviceTypeInfo(device.device_type)
        if (deviceFilter === 'pc') return typeInfo.label === 'Počítač' || typeInfo.label === 'Notebook'
        if (deviceFilter === 'phone') return typeInfo.label === 'Telefon' || typeInfo.label === 'Tablet'
        return true
    })

    // Get time-limited apps across all devices
    const getAppsWithLimits = (deviceId) => {
        const deviceRules = rules[deviceId] || []
        const summary = summaries[deviceId]
        const topApps = summary?.top_apps || []

        // PREFER backend's pre-calculated apps_with_limits if available
        // Backend already correctly matches app names and calculates usage
        const backendAppsWithLimits = summary?.apps_with_limits || []

        if (backendAppsWithLimits.length > 0) {
            // Use backend data - it's already correctly calculated
            return backendAppsWithLimits.map(app => {
                const usedSeconds = app.usage_seconds || 0
                const limitMinutes = app.limit_minutes || 0
                const limitStatus = getLimitStatus(usedSeconds, limitMinutes)

                return {
                    appName: app.app_name,
                    usedSeconds,
                    limitMinutes,
                    ...limitStatus
                }
            })
        }

        // Fallback: calculate from rules - use 'time_limit' rule type (backend uses this)
        const result = deviceRules
            .filter(rule => (rule.rule_type === 'time_limit' || rule.rule_type === 'app_time_limit') &&
                (rule.enabled !== false && rule.is_active !== false) &&
                (rule.limit_minutes > 0 || rule.time_limit > 0))
            .map(rule => {
                // Get target app name from rule
                const ruleAppName = rule.target || rule.app_name || ''
                const limitMinutes = rule.limit_minutes || rule.time_limit || 0

                // Find app usage with STRICT matching algorithm
                const appUsage = topApps.find(a => {
                    const ruleTargetLower = ruleAppName.toLowerCase()
                    const appNameLower = a.app_name?.toLowerCase() || ''
                    const displayNameLower = a.display_name?.toLowerCase() || ''

                    // 1. Exact match has highest priority
                    if (appNameLower === ruleTargetLower || displayNameLower === ruleTargetLower) {
                        return true
                    }

                    // 2. Partial match only if rule target is at least 3 characters
                    // This prevents short names like "e" from matching everything
                    if (ruleTargetLower.length >= 3) {
                        // Check if app name CONTAINS the rule target
                        if (appNameLower.includes(ruleTargetLower) || displayNameLower.includes(ruleTargetLower)) {
                            return true
                        }
                    }

                    // 3. Reverse partial match - only for exact process name variations
                    // e.g., rule "discord" should match app "discord.exe" or "discordptb"
                    if (appNameLower.length >= 3 && ruleTargetLower.startsWith(appNameLower)) {
                        return true
                    }

                    return false
                })

                const usedSeconds = appUsage?.duration_seconds || 0
                const limitStatus = getLimitStatus(usedSeconds, limitMinutes)

                return {
                    appName: ruleAppName,
                    usedSeconds,
                    limitMinutes,
                    ...limitStatus
                }
            })

        // Zobrazit všechny limity, i když aplikace ještě nebyla použita (usedSeconds = 0)
        return result
    }


    const freshness = getDataFreshness(lastFetch)

    if (loading) {
        return (
            <div className="status-overview">
                <div className="loading-state">
                    <div className="loading-spinner"></div>
                    <p>Načítání přehledu...</p>
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="status-overview">
                <div className="error-state">
                    <span className="error-icon"><AlertTriangle size={24} /></span>
                    <p>{error}</p>
                    <button onClick={() => fetchData(true)} className="retry-button">
                        Zkusit znovu
                    </button>
                </div>
            </div>
        )
    }

    if (devices.length === 0) {
        return (
            <div className="status-overview">
                <div className="empty-state">
                    <div className="empty-icon"><DynamicIcon name="smartphone" size={48} color="var(--text-muted)" /></div>
                    <h3>Žádná zařízení</h3>
                    <p>Přidejte první zařízení pomocí záložky "Přidat"</p>
                </div>
            </div>
        )
    }

    // Calculate totals
    const totalUsageToday = Object.values(summaries).reduce(
        (sum, s) => sum + (s?.today_usage_seconds || 0), 0
    )
    const onlineDevices = devices.filter(d => d.is_online).length
    const pcCount = devices.filter(d => {
        const t = getDeviceTypeInfo(d.device_type)
        return t.label === 'Počítač' || t.label === 'Notebook'
    }).length
    const phoneCount = devices.length - pcCount

    return (
        <div className="status-overview">
            {/* Data freshness indicator */}
            <div className={`freshness-indicator ${freshness.color}`}>
                <span className="freshness-dot"></span>
                <span className="freshness-text">{freshness.message}</span>
            </div>

            {/* Device type filter */}
            <div className="device-filter">
                <button
                    className={`filter-btn ${deviceFilter === 'all' ? 'active' : ''}`}
                    onClick={() => setDeviceFilter('all')}
                >
                    Všechna ({devices.length})
                </button>
                {pcCount > 0 && (
                    <button
                        className={`filter-btn ${deviceFilter === 'pc' ? 'active' : ''}`}
                        onClick={() => setDeviceFilter('pc')}
                    >
                        <Monitor size={14} style={{ marginRight: '6px' }} /> Počítače ({pcCount})
                    </button>
                )}
                {phoneCount > 0 && (
                    <button
                        className={`filter-btn ${deviceFilter === 'phone' ? 'active' : ''}`}
                        onClick={() => setDeviceFilter('phone')}
                    >
                        <Smartphone size={14} style={{ marginRight: '6px' }} /> Telefony ({phoneCount})
                    </button>
                )}
            </div>

            {/* Global stats bar */}
            <div className="global-stats">
                <div className="global-stat">
                    <span className="stat-icon"><Smartphone size={20} /></span>
                    <div className="stat-content">
                        <span className="stat-value">{onlineDevices}/{devices.length}</span>
                        <span className="stat-label">online</span>
                    </div>
                </div>
                <div className="global-stat">
                    <span className="stat-icon"><Clock size={20} /></span>
                    <div className="stat-content">
                        <span className="stat-value">{formatDuration(totalUsageToday, true)}</span>
                        <span className="stat-label">celkem dnes</span>
                    </div>
                </div>
            </div>

            {/* Device cards */}
            <div className="device-list">
                {filteredDevices.map((device) => {
                    const summary = summaries[device.id]
                    const state = getDeviceState(device, summary)
                    const typeInfo = getDeviceTypeInfo(device.device_type)
                    const isExpanded = expandedDevice === device.id
                    // Use app activity sum for "Dnes aktivní" - properly handles PC restarts
                    // Backend merges overlapping intervals: morning 3h + evening 2h = 5h correct
                    const todayUsage = summary?.today_usage_seconds || 0
                    // NOTE: Backend filters data, pass null config
                    const topApps = filterSystemApps(summary?.top_apps || [], null)
                    const appsWithLimits = getAppsWithLimits(device.id)

                    return (
                        <div
                            key={device.id}
                            className={`device-card ${state.status} ${isExpanded ? 'expanded' : ''}`}
                            onClick={() => setExpandedDevice(isExpanded ? null : device.id)}
                        >
                            {/* Device header */}
                            <div className="device-header">
                                <div className="device-identity">
                                    <span className="device-type-icon" title={typeInfo.label}>
                                        <DynamicIcon name={typeInfo.iconName} size={24} />
                                    </span>
                                    <div className="device-name-group">
                                        <h3 className="device-name">{device.name}</h3>
                                        <span className={`device-status ${state.color}`}>
                                            <span className="status-icon"><DynamicIcon name={state.iconName} size={14} /></span>
                                            <span className="status-label">{state.label}</span>
                                        </span>
                                    </div>
                                </div>
                                <div className="device-meta">
                                    <span className="last-seen">
                                        {device.last_seen
                                            ? formatRelativeTime(device.last_seen)
                                            : 'nikdy nepřipojeno'
                                        }
                                    </span>
                                </div>
                            </div>

                            {/* Today's usage */}
                            <div className="usage-today">
                                <div className="usage-primary">
                                    <span className="usage-value">{formatDuration(todayUsage, true)}</span>
                                    <span className="usage-label">dnes aktivní</span>
                                </div>
                            </div>

                            {/* Compact limit chips - visible without expanding */}
                            {appsWithLimits.length > 0 && (
                                <div className="limit-chips" onClick={e => e.stopPropagation()}>
                                    {appsWithLimits.slice(0, 3).map((app, idx) => (
                                        <div key={idx} className={`limit-chip ${app.color}`}>
                                            <span className="limit-chip-name">{app.appName}</span>
                                            <span className="limit-chip-value">
                                                {Math.min(Math.floor(app.usedSeconds / 60), app.limitMinutes)}/{app.limitMinutes}m
                                            </span>
                                            <span className="limit-chip-indicator">
                                                {app.status === 'exceeded' ? <XCircle size={10} color="#ef4444" /> :
                                                    app.status === 'warning' ? <CircleDot size={10} color="#f59e0b" /> : <CheckCircle size={10} color="#10b981" />}
                                            </span>
                                        </div>
                                    ))}
                                    {appsWithLimits.length > 3 && (
                                        <span className="limit-chips-more">
                                            +{appsWithLimits.length - 3}
                                        </span>
                                    )}
                                </div>
                            )}

                            {/* Quick actions */}
                            <div className="quick-actions" onClick={e => e.stopPropagation()}>
                                {device.is_online ? (
                                    <>
                                        <div className="action-group">
                                            <button
                                                className={`action-btn lock ${actionPending[`${device.id}-lock`] ? 'pending' : ''}`}
                                                onClick={() => handleQuickAction(device.id, 'lock')}
                                                disabled={actionPending[`${device.id}-lock`]}
                                            >
                                                <Lock size={14} /> Zamknout
                                            </button>
                                            <button
                                                className={`action-btn internet ${actionPending[`${device.id}-pause-internet`] ? 'pending' : ''}`}
                                                onClick={() => handleQuickAction(device.id, 'pause-internet')}
                                                disabled={actionPending[`${device.id}-pause-internet`]}
                                            >
                                                <WifiOff size={14} /> Internet
                                            </button>
                                            <button
                                                className={`action-btn screenshot ${actionPending[`${device.id}-screenshot`] ? 'pending' : ''}`}
                                                onClick={() => handleQuickAction(device.id, 'screenshot')}
                                                disabled={actionPending[`${device.id}-screenshot`]}
                                                title="Pořídit screenshot"
                                            >
                                                <Camera size={14} /> Foto
                                            </button>
                                        </div>
                                        {/* Action feedback */}
                                        {(actionFeedback[`${device.id}-lock`] ||
                                            actionFeedback[`${device.id}-pause-internet`] ||
                                            actionFeedback[`${device.id}-screenshot`]) && (
                                                <div className={`action-feedback ${actionFeedback[`${device.id}-lock`]?.status ||
                                                    actionFeedback[`${device.id}-pause-internet`]?.status ||
                                                    actionFeedback[`${device.id}-screenshot`]?.status
                                                    }`}>
                                                    {actionFeedback[`${device.id}-lock`]?.message ||
                                                        actionFeedback[`${device.id}-pause-internet`]?.message ||
                                                        actionFeedback[`${device.id}-screenshot`]?.message}
                                                </div>
                                            )}
                                        {device.last_screenshot && (
                                            <button
                                                className="view-screenshot-btn"
                                                onClick={() => setShowScreenshotModal(device.id)}
                                            >
                                                <Maximize2 size={12} /> Poslední snímek
                                            </button>
                                        )}
                                    </>
                                ) : (
                                    <span className="offline-notice">
                                        Zařízení není dostupné
                                    </span>
                                )}
                            </div>

                            {/* Expanded content */}
                            {isExpanded && (
                                <div className="device-details" onClick={e => e.stopPropagation()}>
                                    {/* Monitoring info */}
                                    <div className="detail-section monitoring-info">
                                        <div className="detail-item">
                                            <span className="detail-icon"><Calendar size={18} /></span>
                                            <div className="detail-content">
                                                <span className="detail-label">Monitorování od</span>
                                                <span className="detail-value">
                                                    {summary?.paired_at
                                                        ? formatTimestamp(summary.paired_at, 'full')
                                                        : 'neznámý datum'
                                                    }
                                                </span>
                                            </div>
                                        </div>
                                        <div className="detail-item">
                                            <span className="detail-icon"><RefreshCw size={18} /></span>
                                            <div className="detail-content">
                                                <span className="detail-label">Poslední kontrola</span>
                                                <span className="detail-value">
                                                    {device.last_seen
                                                        ? formatTimestamp(device.last_seen, 'full')
                                                        : 'nikdy'
                                                    }
                                                </span>
                                            </div>
                                        </div>
                                    </div>

                                    {/* App limits in expanded section */}
                                    {appsWithLimits.length > 0 && (
                                        <div className="detail-section limits-section-expanded">
                                            <h4 className="section-title"><Clock size={16} /> Limity aplikací</h4>
                                            {appsWithLimits.map((app, idx) => {
                                                const adjustKey = `${device.id}-adjust-${app.appName}`
                                                const isPending = actionPending[adjustKey]
                                                const feedback = actionFeedback[adjustKey]

                                                return (
                                                    <div key={idx} className={`limit-item-expanded ${app.color}`}>
                                                        <div className="limit-header">
                                                            <span className="limit-app-name">{app.appName}</span>
                                                            <span className={`limit-text ${app.color}`}>
                                                                {formatLimitText(app.usedSeconds, app.limitMinutes)}
                                                            </span>
                                                        </div>
                                                        <div className="limit-bar-container">
                                                            <div
                                                                className={`limit-bar ${app.color}`}
                                                                style={{ width: `${Math.min(100, app.actualPercentage)}%` }}
                                                            ></div>
                                                        </div>
                                                        <div className="limit-footer">
                                                            {app.status === 'exceeded' ? (
                                                                <span className="limit-exceeded-badge"><XCircle size={14} /> Limit dosažen</span>
                                                            ) : app.status === 'critical' ? (
                                                                <span className="limit-critical-badge"><AlertTriangle size={14} /> Téměř vyčerpán</span>
                                                            ) : app.status === 'warning' ? (
                                                                <span className="limit-warning-badge"><Clock size={14} /> Blízko limitu</span>
                                                            ) : (
                                                                <span className="limit-ok-badge">
                                                                    <CheckCircle size={14} /> Zbývá {Math.max(0, app.limitMinutes - Math.floor(app.usedSeconds / 60))} min
                                                                </span>
                                                            )}
                                                        </div>

                                                        {/* Quick actions for limit adjustment */}
                                                        <div className="limit-quick-actions">
                                                            <button
                                                                className={`limit-action-btn subtract ${isPending ? 'pending' : ''}`}
                                                                onClick={() => handleAdjustLimit(device.id, app.appName, -15)}
                                                                disabled={isPending}
                                                                title="Odebrat 15 minut"
                                                            >
                                                                -15m
                                                            </button>
                                                            <button
                                                                className={`limit-action-btn add ${isPending ? 'pending' : ''}`}
                                                                onClick={() => handleAdjustLimit(device.id, app.appName, 15)}
                                                                disabled={isPending}
                                                                title="Přidat 15 minut"
                                                            >
                                                                +15m
                                                            </button>
                                                            <button
                                                                className={`limit-action-btn add-more ${isPending ? 'pending' : ''}`}
                                                                onClick={() => handleAdjustLimit(device.id, app.appName, 30)}
                                                                disabled={isPending}
                                                                title="Přidat 30 minut"
                                                            >
                                                                +30m
                                                            </button>
                                                        </div>

                                                        {/* Feedback for limit adjustment */}
                                                        {feedback && (
                                                            <div className={`limit-action-feedback ${feedback.status}`}>
                                                                {feedback.message}
                                                            </div>
                                                        )}
                                                    </div>
                                                )
                                            })}
                                        </div>
                                    )}

                                    {/* Daily device limit */}
                                    {summary?.daily_limit && (
                                        <div className="detail-section limits-section-expanded">
                                            <h4 className="section-title"><Calendar size={16} /> Denní limit zařízení</h4>
                                            <div className={`limit-item-expanded ${summary.daily_limit.percentage_used >= 100 ? 'red' :
                                                summary.daily_limit.percentage_used >= 65 ? 'orange' : 'green'
                                                }`}>
                                                <div className="limit-header">
                                                    <span className="limit-app-name">Celkový čas dnes</span>
                                                    <span className={`limit-text ${summary.daily_limit.percentage_used >= 100 ? 'red' :
                                                        summary.daily_limit.percentage_used >= 65 ? 'orange' : 'green'
                                                        }`}>
                                                        {formatDuration(summary.daily_limit.usage_seconds, true)} / {summary.daily_limit.limit_minutes} min
                                                    </span>
                                                </div>
                                                <div className="limit-bar-container">
                                                    <div
                                                        className={`limit-bar ${summary.daily_limit.percentage_used >= 100 ? 'red' :
                                                            summary.daily_limit.percentage_used >= 65 ? 'orange' : 'green'
                                                            }`}
                                                        style={{ width: `${Math.min(100, summary.daily_limit.percentage_used)}%` }}
                                                    ></div>
                                                </div>
                                                <div className="limit-footer">
                                                    {summary.daily_limit.percentage_used >= 100 ? (
                                                        <span className="limit-exceeded-badge"><XCircle size={14} /> Denní limit dosažen</span>
                                                    ) : summary.daily_limit.percentage_used >= 65 ? (
                                                        <span className="limit-warning-badge"><AlertTriangle size={14} /> Blízko denního limitu</span>
                                                    ) : (
                                                        <span className="limit-ok-badge">
                                                            <CheckCircle size={14} /> Zbývá {Math.round(summary.daily_limit.remaining_minutes)} min
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Active schedules */}
                                    {summary?.schedules && summary.schedules.length > 0 && (
                                        <div className="detail-section schedules-section">
                                            <h4 className="section-title"><Clock size={16} /> Časové rozvrhy</h4>
                                            <div className="schedules-list">
                                                {summary.schedules.map((schedule, idx) => (
                                                    <div key={idx} className="schedule-item">
                                                        <span className="schedule-icon"><Clock size={18} /></span>
                                                        <div className="schedule-content">
                                                            <span className="schedule-time">
                                                                {schedule.start_time} - {schedule.end_time}
                                                            </span>
                                                            <span className="schedule-days">
                                                                {schedule.days ? `Dny: ${schedule.days}` : 'Všechny dny'}
                                                            </span>
                                                            {schedule.app_name && (
                                                                <span className="schedule-app">Aplikace: {schedule.app_name}</span>
                                                            )}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Top apps today with quick actions */}
                                    {topApps.length > 0 && (
                                        <div className="detail-section apps-section">
                                            <div className="section-header-row">
                                                <h4 className="section-title" title="Seřazeno podle času používání od půlnoci">
                                                    <Smartphone size={16} /> Top 5 používaných aplikací dnes
                                                </h4>
                                                <button
                                                    className="show-all-apps-btn"
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        setShowAllAppsModal(device.id)
                                                    }}
                                                >
                                                    <DynamicIcon name="clipboardList" size={14} /> Všechny ({topApps.length})
                                                </button>
                                            </div>
                                            <div className="apps-list">
                                                {topApps.slice(0, 5).map((app, index) => {
                                                    const appName = app.app_name || app.display_name
                                                    const blockKey = `${device.id}-app-${appName}-block`
                                                    const limit60Key = `${device.id}-app-${appName}-limit-60`
                                                    const isPending = actionPending[blockKey] || actionPending[limit60Key]
                                                    const feedback = actionFeedback[blockKey] || actionFeedback[limit60Key]

                                                    // Check if this app already has a rule
                                                    const deviceRules = rules[device.id] || []
                                                    const hasRule = deviceRules.some(r =>
                                                        r.app_name?.toLowerCase() === appName?.toLowerCase()
                                                    )

                                                    return (
                                                        <div key={index} className="app-item-with-actions">
                                                            <div className="app-item-main">
                                                                <div className="top-app-icon-group">
                                                                    <div className="top-app-icon">
                                                                        <DynamicIcon name={app.icon || app.icon_type} size={20} />
                                                                    </div>
                                                                    <div className="top-app-name-details">
                                                                        <span className="top-app-name-internal">{app.display_name}</span>
                                                                        {app.window_title && (
                                                                            <span className="top-app-window-title" title={app.window_title}>
                                                                                {app.window_title.length > 40 ? app.window_title.substring(0, 37) + '...' : app.window_title}
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                                <span className="app-duration">
                                                                    {formatDuration(app.duration_seconds, true)}
                                                                </span>
                                                            </div>

                                                            {/* Quick actions for this app */}
                                                            {!hasRule && (
                                                                <div className="app-quick-actions">
                                                                    <button
                                                                        className={`app-action-btn block ${isPending ? 'pending' : ''}`}
                                                                        onClick={() => handleAppQuickAction(device.id, appName, 'block')}
                                                                        disabled={isPending}
                                                                        title="Zablokovat aplikaci"
                                                                    >
                                                                        <XCircle size={14} />
                                                                    </button>
                                                                    <button
                                                                        className={`app-action-btn limit ${isPending ? 'pending' : ''}`}
                                                                        onClick={() => handleAppQuickAction(device.id, appName, 'limit-30')}
                                                                        disabled={isPending}
                                                                        title="Nastavit limit 30 min"
                                                                    >
                                                                        30m
                                                                    </button>
                                                                    <button
                                                                        className={`app-action-btn limit ${isPending ? 'pending' : ''}`}
                                                                        onClick={() => handleAppQuickAction(device.id, appName, 'limit-60')}
                                                                        disabled={isPending}
                                                                        title="Nastavit limit 60 min"
                                                                    >
                                                                        1h
                                                                    </button>
                                                                    <button
                                                                        className="app-action-btn hide"
                                                                        onClick={(e) => {
                                                                            e.stopPropagation()
                                                                            const name = (appName || '').toLowerCase().trim()
                                                                            try {
                                                                                const stored = localStorage.getItem('familyeye_user_blacklist')
                                                                                const list = stored ? JSON.parse(stored) : []
                                                                                if (!list.includes(name)) {
                                                                                    list.push(name)
                                                                                    localStorage.setItem('familyeye_user_blacklist', JSON.stringify(list))
                                                                                    // Force re-render by refreshing data
                                                                                    fetchData(false)
                                                                                }
                                                                            } catch (err) {
                                                                                console.error('Failed to hide app:', err)
                                                                            }
                                                                        }}
                                                                        title="Skrýt z přehledu (systémová app)"
                                                                    >
                                                                        <EyeOff size={14} />
                                                                    </button>
                                                                </div>
                                                            )}

                                                            {hasRule && (
                                                                <span className="app-has-rule-badge"><Check size={10} style={{ marginRight: '2px' }} /> Pravidlo</span>
                                                            )}

                                                            {/* Feedback */}
                                                            {feedback && (
                                                                <div className={`app-action-feedback ${feedback.status}`}>
                                                                    {feedback.message}
                                                                </div>
                                                            )}
                                                        </div>
                                                    )
                                                })}
                                            </div>
                                        </div>
                                    )}

                                    {/* Extended actions */}
                                    <div className="detail-section actions-section">

                                        <button
                                            className={`action-btn-full unlock ${actionPending[`${device.id}-unlock`] ? 'pending' : ''}`}
                                            onClick={() => handleQuickAction(device.id, 'unlock')}
                                            disabled={actionPending[`${device.id}-unlock`] || !device.is_online}
                                        >
                                            <Unlock size={14} style={{ marginRight: '6px' }} /> Odemknout zařízení
                                        </button>
                                        <button
                                            className={`action-btn-full resume ${actionPending[`${device.id}-resume-internet`] ? 'pending' : ''}`}
                                            onClick={() => handleQuickAction(device.id, 'resume-internet')}
                                            disabled={actionPending[`${device.id}-resume-internet`] || !device.is_online}
                                        >
                                            <Globe size={14} style={{ marginRight: '6px' }} /> Obnovit internet
                                        </button>
                                        {/* Feedback for extended actions */}
                                        {(actionFeedback[`${device.id}-unlock`] || actionFeedback[`${device.id}-resume-internet`]) && (
                                            <div className={`action-feedback ${actionFeedback[`${device.id}-unlock`]?.status ||
                                                actionFeedback[`${device.id}-resume-internet`]?.status
                                                }`}>
                                                {actionFeedback[`${device.id}-unlock`]?.message ||
                                                    actionFeedback[`${device.id}-resume-internet`]?.message}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Expand indicator */}
                            <div className="expand-indicator">
                                <span className={`expand-arrow ${isExpanded ? 'up' : 'down'}`}>
                                    {isExpanded ? '▲' : '▼'}
                                </span>
                            </div>
                        </div>
                    )
                })}
            </div>

            {/* All Apps Modal */}
            {showAllAppsModal && (() => {
                const device = devices.find(d => d.id === showAllAppsModal)
                const summary = summaries[showAllAppsModal]
                const allApps = filterSystemApps(summary?.top_apps || [])
                const deviceRules = rules[showAllAppsModal] || []

                return (
                    <div className="all-apps-modal-overlay" onClick={() => setShowAllAppsModal(null)}>
                        <div className="all-apps-modal" onClick={e => e.stopPropagation()}>
                            <div className="modal-header">
                                <div>
                                    <h3><Smartphone size={20} /> Detailní přehled aplikací</h3>
                                    <p className="modal-description">
                                        Top 100 aplikací seřazených podle délky používání dnes (od 00:00).
                                    </p>
                                    <span className="modal-device-name">{device?.name}</span>
                                </div>
                                <button className="modal-close-btn" onClick={() => setShowAllAppsModal(null)}>
                                    <X size={20} />
                                </button>
                            </div>

                            <div className="modal-subtitle">
                                <span>Aktualizováno {lastFetch ? formatRelativeTime(lastFetch) : 'teď'}</span>
                                <span className="apps-count">{allApps.length} aplikací</span>
                            </div>

                            <div className="modal-apps-list">
                                {allApps.length === 0 ? (
                                    <div className="no-apps-message">
                                        Zatím žádné aplikace nebyly použity
                                    </div>
                                ) : (
                                    allApps.map((app, index) => {
                                        const appName = app.app_name || app.display_name
                                        const hasRule = deviceRules.some(r =>
                                            r.app_name?.toLowerCase() === appName?.toLowerCase()
                                        )
                                        const blockKey = `${showAllAppsModal}-app-${appName}-block`
                                        const limitKey = `${showAllAppsModal}-app-${appName}-limit-60`
                                        const isPending = actionPending[blockKey] || actionPending[limitKey]
                                        const feedback = actionFeedback[blockKey] || actionFeedback[limitKey]

                                        return (
                                            <div key={index} className="modal-app-item">
                                                <div className="modal-app-info">
                                                    <span className="modal-app-name">{app.display_name}</span>
                                                    <span className="modal-app-duration">
                                                        {formatDuration(app.duration_seconds, true)}
                                                    </span>
                                                </div>

                                                {!hasRule ? (
                                                    <div className="modal-app-actions">
                                                        <button
                                                            className={`modal-action-btn block ${isPending ? 'pending' : ''}`}
                                                            onClick={() => handleAppQuickAction(showAllAppsModal, appName, 'block')}
                                                            disabled={isPending}
                                                            title="Zablokovat aplikaci"
                                                        >
                                                            <XCircle size={14} style={{ marginRight: '4px' }} /> Blokovat
                                                        </button>
                                                        <button
                                                            className={`modal-action-btn limit ${isPending ? 'pending' : ''}`}
                                                            onClick={() => handleAppQuickAction(showAllAppsModal, appName, 'limit-60')}
                                                            disabled={isPending}
                                                            title="Nastavit limit 1 hodina"
                                                        >
                                                            <Clock size={12} style={{ marginRight: '2px' }} /> Limit 1h
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <span className="modal-has-rule"><Check size={10} style={{ marginRight: '2px' }} /> Má pravidlo</span>
                                                )}

                                                {feedback && (
                                                    <div className={`modal-feedback ${feedback.status}`}>
                                                        {feedback.message}
                                                    </div>
                                                )}
                                            </div>
                                        )
                                    })
                                )}
                            </div>

                            <div className="modal-footer">
                                <button className="modal-close-btn-full" onClick={() => setShowAllAppsModal(null)}>
                                    Zavřít
                                </button>
                            </div>
                        </div>
                    </div>
                )
            })()}


            {/* Screenshot Modal */}
            {showScreenshotModal && (() => {
                const device = devices.find(d => d.id === showScreenshotModal)
                return (
                    <div className="all-apps-modal-overlay" onClick={() => setShowScreenshotModal(null)}>
                        <div className="all-apps-modal screenshot-modal" onClick={e => e.stopPropagation()}>
                            <div className="modal-header">
                                <div>
                                    <h3><Camera size={20} /> Poslední snímek obrazovky</h3>
                                    <span className="modal-device-name">{device?.name}</span>
                                </div>
                                <button className="modal-close-btn" onClick={() => setShowScreenshotModal(null)}>
                                    <X size={20} />
                                </button>
                            </div>
                            <div className="screenshot-viewer">
                                {device?.last_screenshot ? (
                                    <img src={device.last_screenshot} alt="Snímek obrazovky" className="full-screenshot" />
                                ) : (
                                    <div className="no-screenshot">Žádný snímek k dispozici</div>
                                )}
                            </div>
                            <div className="modal-footer">
                                <button className="modal-close-btn-full" onClick={() => setShowScreenshotModal(null)}>
                                    Zavřít
                                </button>
                            </div>
                        </div>
                    </div>
                )
            })()}

        </div >
    )
}

export default StatusOverview
