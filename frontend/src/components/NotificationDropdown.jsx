import React, { useState, useEffect, useRef } from 'react'
import api from '../services/api'
import { Bell, AlertTriangle, CheckCircle, RefreshCw, X, AlertCircle, WifiOff, CircleDot } from 'lucide-react'
import DynamicIcon from './DynamicIcon'
import { webSocketService } from '../services/websocket'
import './NotificationDropdown.css'

/**
 * Translate technical alert keywords into friendly parent messages
 */
const formatAlertMessage = (keyword, deviceName, appName) => {
    // Map of technical keywords to friendly Czech messages
    const friendlyMessages = {
        // Tampering alerts
        'TAMPERING:ADB_DEBUGGING_ENABLED': {
            title: 'Pokus o obejití',
            message: 'aktivováno USB ladění (vývojářský režim)'
        },
        'TAMPERING:DEVELOPER_OPTIONS_ENABLED': {
            title: 'Pokus o obejití',
            message: 'aktivovány vývojářské možnosti'
        },
        'TAMPERING:SETTINGS_ACCESS': {
            title: 'Přístup do nastavení',
            message: 'pokus o vstup do blokovaného nastavení'
        },
        'TAMPERING:UNINSTALL_ATTEMPT': {
            title: 'Pokus o odinstalaci',
            message: 'pokus o odebrání aplikace FamilyEye'
        },
        'TAMPERING:ACCESSIBILITY_DISABLED': {
            title: 'Ochrana vypnuta',
            message: 'služba usnadnění byla deaktivována'
        },
        'TAMPERING:DEVICE_ADMIN_REMOVAL': {
            title: 'Pokus o obejití',
            message: 'pokus o odebrání administrátorských práv'
        },
        // Content alerts (Smart Shield words)
        'WORD_DETECTED': {
            title: 'Nevhodný obsah',
            message: 'detekován zakázaný výraz'
        }
    }

    // Find matching pattern (exact or prefix match)
    let match = friendlyMessages[keyword]
    if (!match) {
        // Try prefix matching for keywords like "TAMPERING:..."
        for (const [key, value] of Object.entries(friendlyMessages)) {
            if (keyword?.startsWith(key.split(':')[0])) {
                match = value
                break
            }
        }
    }

    // Build the friendly message
    if (match) {
        return {
            title: `🛡️ ${match.title}`,
            message: `${deviceName}: ${match.message}`
        }
    }

    // Fallback for unknown keywords - still make it friendly
    const cleanKeyword = keyword?.replace(/_/g, ' ').replace(/TAMPERING:/gi, '').toLowerCase() || 'neznámá aktivita'
    return {
        title: '🛡️ Bezpečnostní upozornění',
        message: `${deviceName}: ${cleanKeyword}${appName ? ` v ${appName}` : ''}`
    }
}

const NotificationDropdown = () => {
    const [isOpen, setIsOpen] = useState(false)
    const [notifications, setNotifications] = useState([])
    const [dismissedIds, setDismissedIds] = useState(() => {
        const stored = localStorage.getItem('familyeye_dismissed_notifications')
        return stored ? JSON.parse(stored) : []
    })
    const [loading, setLoading] = useState(false)
    const dropdownRef = useRef(null)

    useEffect(() => {
        // Clear stale dismissed notifications (older than 24 hours)
        const clearStaleDismissals = () => {
            const stored = localStorage.getItem('familyeye_dismissed_notifications')
            if (stored) {
                try {
                    const parsed = JSON.parse(stored)
                    // Keep only today's dismissals (by checking if ID contains today's date)
                    const todayStr = new Date().toISOString().split('T')[0]
                    const filtered = parsed.filter(id => id.includes(todayStr))
                    if (filtered.length !== parsed.length) {
                        localStorage.setItem('familyeye_dismissed_notifications', JSON.stringify(filtered))
                        setDismissedIds(filtered)
                    }
                } catch (e) {
                    // If corrupted, clear it
                    localStorage.removeItem('familyeye_dismissed_notifications')
                    setDismissedIds([])
                }
            }
        }
        clearStaleDismissals()

        fetchNotifications()

        // Subscribe to Real-time Alerts
        const unsubscribe = webSocketService.subscribe((data) => {
            if (data.type === 'shield_alert') {

                // Add new alert immediately
                setNotifications(prev => {
                    const friendly = formatAlertMessage(data.keyword, data.device_name, data.app_name)
                    const newAlert = {
                        id: `shield-${Date.now()}`, // Unique ID for instant alert
                        type: 'error',
                        iconName: 'shield-alert',
                        title: friendly.title,
                        message: friendly.message,
                        deviceId: data.device_id,
                        deviceName: data.device_name,
                        priority: -1, // Highest priority
                        isRealTime: true,
                        timestamp: new Date().toISOString()
                    }

                    // User said: "always appear even if delete all"
                    // So we ignore dismissedIds for this incoming event essentially because it has a new ID
                    return [newAlert, ...prev]
                })
            }
        })

        const interval = setInterval(fetchNotifications, 30000)
        return () => {
            clearInterval(interval)
            unsubscribe()
        }
    }, [])

    useEffect(() => {
        localStorage.setItem('familyeye_dismissed_notifications', JSON.stringify(dismissedIds))
    }, [dismissedIds])

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const fetchNotifications = async () => {
        try {
            setLoading(true)
            const response = await api.get('/api/devices/')
            const devices = response.data

            const allNotifications = []
            const todayStr = new Date().toISOString().split('T')[0]

            // Fetch summary for each device
            for (const device of devices) {
                try {
                    const summaryRes = await api.get(`/api/reports/device/${device.id}/summary`)
                    const summary = summaryRes.data

                    // Check for exceeded limits
                    if (summary.apps_with_limits) {
                        summary.apps_with_limits.forEach(app => {
                            const id = `${device.id}-${app.app_name}-exceeded-${todayStr}`
                            if (app.percentage_used >= 100) {
                                allNotifications.push({
                                    id,
                                    type: 'error',
                                    iconName: 'scroll',
                                    title: `${app.app_name} - limit překročen`,
                                    message: `${device.name}: Použito ${Math.round(app.usage_minutes)}/${app.limit_minutes} min`,
                                    deviceId: device.id,
                                    deviceName: device.name,
                                    priority: 1,
                                    timestamp: new Date().toISOString()
                                })
                            } else if (app.percentage_used >= 80) {
                                const idWarn = `${device.id}-${app.app_name}-warning-${todayStr}`
                                allNotifications.push({
                                    id: idWarn,
                                    type: 'warning',
                                    iconName: 'scroll',
                                    title: `${app.app_name} - blízko limitu`,
                                    message: `${device.name}: Zbývá ${Math.round(app.remaining_minutes)} min`,
                                    deviceId: device.id,
                                    deviceName: device.name,
                                    priority: 2,
                                    timestamp: new Date().toISOString()
                                })
                            }
                        })
                    }

                    // Check daily limit
                    if (summary.daily_limit) {
                        const usedMinutes = Math.round((summary.today_usage_seconds || 0) / 60)
                        const limitMinutes = summary.daily_limit.limit_minutes
                        const percentage = (usedMinutes / limitMinutes) * 100

                        if (percentage >= 100) {
                            allNotifications.push({
                                id: `${device.id}-daily-exceeded-${todayStr}`,
                                type: 'error',
                                iconName: 'scroll',
                                title: 'Denní limit vyčerpán',
                                message: `${device.name}: ${usedMinutes}/${limitMinutes} min`,
                                deviceId: device.id,
                                name: device.name,
                                priority: 0,
                                timestamp: new Date().toISOString()
                            })
                        } else if (percentage >= 80) {
                            allNotifications.push({
                                id: `${device.id}-daily-warning-${todayStr}`,
                                type: 'warning',
                                iconName: 'scroll',
                                title: 'Denní limit se blíží',
                                message: `${device.name}: Zbývá ${limitMinutes - usedMinutes} min`,
                                deviceId: device.id,
                                deviceName: device.name,
                                priority: 1,
                                timestamp: new Date().toISOString()
                            })
                        }
                    }

                    // Check if device is offline
                    if (summary.last_seen) {
                        const lastSeen = new Date(summary.last_seen)
                        const now = new Date()
                        const diffMinutes = (now - lastSeen) / 60000

                        // Be less aggressive with offline - 10 min threshold for notification
                        if (diffMinutes > 10) {
                            // Hour-based ID for offline so it resurfaces if it stays offline
                            const hourStr = now.getHours()
                            allNotifications.push({
                                id: `${device.id}-offline-${todayStr}-${hourStr}`,
                                type: 'info',
                                iconName: 'wifi-off',
                                title: 'Zařízení offline',
                                message: `${device.name}: Neaktivní ${Math.round(diffMinutes)} min`,
                                deviceId: device.id,
                                deviceName: device.name,
                                priority: 3,
                                timestamp: new Date().toISOString()
                            })
                        }
                    }

                    // --- NEW: Fetch Smart Shield Alerts ---
                    try {
                        const shieldRes = await api.get(`/api/shield/alerts/${device.id}?limit=5`)
                        const alerts = shieldRes.data || []
                        const today = new Date().setHours(0, 0, 0, 0)

                        alerts.forEach(alert => {
                            // Only show alerts from today (or very recent unread)
                            const alertDate = new Date(alert.timestamp)
                            if (alertDate >= today && !alert.is_read) {
                                const friendly = formatAlertMessage(alert.keyword, device.name, alert.app_name)
                                allNotifications.push({
                                    id: `shield-${alert.id}-${todayStr}`,
                                    type: 'error',
                                    iconName: 'shield-alert',
                                    title: friendly.title,
                                    message: friendly.message,
                                    deviceId: device.id,
                                    deviceName: device.name,
                                    priority: 0, // Highest priority
                                    timestamp: alert.timestamp
                                })
                            }
                        })
                    } catch (e) {
                        console.error('Failed to fetch shield alerts', e)
                    }
                } catch (err) {
                    console.error(`Error fetching summary for device ${device.id}:`, err)
                }
            }

            // Filter out dismissed notifications
            const visibleNotifications = allNotifications.filter(n => !dismissedIds.includes(n.id))

            // Sort by priority
            visibleNotifications.sort((a, b) => a.priority - b.priority)
            setNotifications(visibleNotifications)
        } catch (err) {
            console.error('Error fetching notifications:', err)
        } finally {
            setLoading(false)
        }
    }

    const dismissNotification = (id) => {
        setDismissedIds(prev => [...prev, id])
        setNotifications(prev => prev.filter(n => n.id !== id))
    }

    const clearAll = () => {
        const allIds = notifications.map(n => n.id)
        setDismissedIds(prev => [...prev, ...allIds])
        setNotifications([])
    }

    const criticalCount = notifications.filter(n => n.type === 'error').length
    const warningCount = notifications.filter(n => n.type === 'warning').length
    const totalCount = notifications.length

    return (
        <div className="notification-dropdown" ref={dropdownRef}>
            <button
                className={`notification-bell ${totalCount > 0 ? 'has-notifications' : ''}`}
                onClick={() => setIsOpen(!isOpen)}
                title="Upozornění"
            >
                <Bell size={20} />
                {criticalCount > 0 && (
                    <span className="notification-badge critical">{criticalCount}</span>
                )}
                {criticalCount === 0 && warningCount > 0 && (
                    <span className="notification-badge warning">{warningCount}</span>
                )}
            </button>

            {isOpen && (
                <div className="notification-panel">
                    <div className="notification-header">
                        <div className="header-left">
                            <h3><Bell size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Upozornění</h3>
                            {totalCount > 0 && (
                                <span className="notification-count">{totalCount}</span>
                            )}
                        </div>
                        <button
                            className="refresh-button"
                            onClick={(e) => {
                                e.stopPropagation();
                                fetchNotifications();
                            }}
                            title="Aktualizovat"
                            disabled={loading}
                        >
                            {loading ? '...' : <RefreshCw size={16} />}
                        </button>
                    </div>

                    <div className="notification-list">
                        {loading && notifications.length === 0 ? (
                            <div className="notification-loading">Načítání...</div>
                        ) : notifications.length === 0 ? (
                            <div className="notification-empty">
                                <CheckCircle size={24} className="empty-icon" color="var(--success-color, #10b981)" />
                                <span className="empty-text">Žádná upozornění</span>
                            </div>
                        ) : (
                            notifications.map(notification => (
                                <div
                                    key={notification.id}
                                    className={`notification-item ${notification.type}`}
                                >
                                    <span className="notification-icon"><DynamicIcon name={notification.iconName} size={18} /></span>
                                    <div className="notification-content">
                                        <div className="notification-header-row">
                                            <span className="notification-title">{notification.title}</span>
                                            {notification.timestamp && (
                                                <span className="notification-time">
                                                    {new Date(notification.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                </span>
                                            )}
                                        </div>
                                        <span className="notification-message">{notification.message}</span>
                                    </div>
                                    <button
                                        className="dismiss-button"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            dismissNotification(notification.id);
                                        }}
                                        title="Smazat"
                                    >
                                        <X size={14} />
                                    </button>
                                </div>
                            ))
                        )}
                    </div>

                    {notifications.length > 0 && (
                        <div className="notification-footer">
                            <span className="notification-summary">
                                {criticalCount > 0 && <span className="summary-critical"><CircleDot size={12} color="#ef4444" /> {criticalCount} kritických</span>}
                                {warningCount > 0 && <span className="summary-warning"><AlertTriangle size={12} color="#f59e0b" /> {warningCount} varování</span>}
                            </span>
                            <button className="clear-all-button" onClick={clearAll}>
                                Smazat vše
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default NotificationDropdown
