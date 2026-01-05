import React, { useState, useEffect, useMemo } from 'react'
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    LineChart, Line
} from 'recharts'
import api from '../../services/api'
import { getAppIcon } from '../../utils/formatting'
import { Smartphone, Clock, Calendar, X } from 'lucide-react'
import DynamicIcon from '../DynamicIcon'
import './AppDetailsModal.css'

/**
 * AppDetailsModal - Modal with detailed app usage analysis
 * 
 * Features:
 * - Summary stats
 * - 24h usage chart
 * - Trends over time
 * - Responsive
 */
const AppDetailsModal = ({ deviceId, appName, onClose }) => {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [activeTab, setActiveTab] = useState('hours') // 'hours' or 'days'

    useEffect(() => {
        if (deviceId && appName) {
            fetchData()
        }
    }, [deviceId, appName])

    const fetchData = async () => {
        try {
            setLoading(true)
            setError(null)
            const response = await api.get(
                `/api/reports/device/${deviceId}/app-details?app_name=${encodeURIComponent(appName)}&days=14`
            )
            setData(response.data)
        } catch (err) {
            console.error('Error fetching app details:', err)
            setError('Nepodařilo se načíst data')
        } finally {
            setLoading(false)
        }
    }

    // Format app name nicely
    const formatAppName = (name) => {
        if (!name) return ''
        return name.replace('.exe', '').charAt(0).toUpperCase() + name.replace('.exe', '').slice(1)
    }

    // Format duration
    const formatDuration = (seconds) => {
        if (!seconds || seconds === 0) return '0 min'
        const hours = Math.floor(seconds / 3600)
        const minutes = Math.floor((seconds % 3600) / 60)
        if (hours > 0) return `${hours}h ${minutes}m`
        return `${minutes} min`
    }

    // Find peak hour
    const peakHour = useMemo(() => {
        if (!data?.usage_by_hour) return null
        let maxHour = 0
        let maxValue = 0
        data.usage_by_hour.forEach(h => {
            if (h.duration_seconds > maxValue) {
                maxValue = h.duration_seconds
                maxHour = h.hour
            }
        })
        return maxValue > 0 ? maxHour : null
    }, [data])

    // Handle click outside
    const handleBackdropClick = (e) => {
        if (e.target.className === 'app-details-backdrop') {
            onClose()
        }
    }

    // Handle escape key
    useEffect(() => {
        const handleEscape = (e) => {
            if (e.key === 'Escape') onClose()
        }
        document.addEventListener('keydown', handleEscape)
        return () => document.removeEventListener('keydown', handleEscape)
    }, [onClose])

    if (loading) {
        return (
            <div className="app-details-backdrop" onClick={handleBackdropClick}>
                <div className="app-details-modal">
                    <div className="modal-loading">
                        <div className="loading-spinner"></div>
                        <span>Načítání detailů...</span>
                    </div>
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="app-details-backdrop" onClick={handleBackdropClick}>
                <div className="app-details-modal">
                    <div className="modal-header">
                        <h3>Chyba</h3>
                        <button className="modal-close" onClick={onClose}><X size={20} /></button>
                    </div>
                    <div className="modal-error">{error}</div>
                </div>
            </div>
        )
    }

    if (!data) return null

    return (
        <div className="app-details-backdrop" onClick={handleBackdropClick}>
            <div className="app-details-modal">
                {/* Header */}
                <div className="modal-header">
                    <div className="header-info">
                        <div className="app-icon"><DynamicIcon name={getAppIcon(appName)} size={24} /></div>
                        <h3>{formatAppName(appName)}</h3>
                    </div>
                    <button className="modal-close" onClick={onClose}><X size={20} /></button>
                </div>

                {/* Summary stats */}
                <div className="modal-summary">
                    <div className="summary-stat">
                        <span className="stat-value">{formatDuration(data.total_duration_seconds)}</span>
                        <span className="stat-label">Celkem (14 dní)</span>
                    </div>
                    <div className="summary-stat">
                        <span className="stat-value">{data.days_active || data.usage_by_day?.filter(d => d.duration_seconds > 0).length || 0}</span>
                        <span className="stat-label">Dní aktivní</span>
                    </div>
                    <div className="summary-stat">
                        <span className="stat-value">{formatDuration(Math.round(data.total_duration_seconds / Math.max(1, data.days_active || data.usage_by_day?.filter(d => d.duration_seconds > 0).length || 1)))}</span>
                        <span className="stat-label">Ø denně</span>
                    </div>
                    {peakHour !== null && (
                        <div className="summary-stat highlight">
                            <span className="stat-value">{peakHour}:00</span>
                            <span className="stat-label">Nejaktivnější</span>
                        </div>
                    )}
                </div>

                {/* Tab navigation */}
                <div className="modal-tabs">
                    <button
                        className={`tab-btn ${activeTab === 'hours' ? 'active' : ''}`}
                        onClick={() => setActiveTab('hours')}
                    >
                        <Clock size={16} /> Podle hodin
                    </button>
                    <button
                        className={`tab-btn ${activeTab === 'days' ? 'active' : ''}`}
                        onClick={() => setActiveTab('days')}
                    >
                        <Calendar size={16} /> Podle dnů
                    </button>
                </div>

                {/* Charts */}
                <div className="modal-chart">
                    {activeTab === 'hours' ? (
                        <>
                            <h4>Aktivita podle hodin dne</h4>
                            <ResponsiveContainer width="100%" height={200}>
                                <BarChart data={data.usage_by_hour} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                                    <XAxis
                                        dataKey="hour"
                                        tick={{ fontSize: 10, fill: 'var(--text-secondary)' }}
                                        tickFormatter={(h) => h % 3 === 0 ? `${h}:00` : ''}
                                        tickLine={false}
                                        axisLine={{ stroke: 'var(--border-color)' }}
                                    />
                                    <YAxis
                                        tick={{ fontSize: 10, fill: 'var(--text-secondary)' }}
                                        tickLine={false}
                                        axisLine={false}
                                        tickFormatter={(v) => `${Math.round(v / 60)}m`}
                                    />
                                    <Tooltip
                                        formatter={(value) => [formatDuration(value), 'Čas']}
                                        labelFormatter={(label) => `${label}:00 - ${label + 1}:00`}
                                        contentStyle={{
                                            background: 'var(--bg-primary)',
                                            border: '1px solid var(--border-color)',
                                            borderRadius: '8px'
                                        }}
                                    />
                                    <Bar
                                        dataKey="duration_seconds"
                                        fill="#6366f1"
                                        radius={[4, 4, 0, 0]}
                                        maxBarSize={20}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        </>
                    ) : (
                        <>
                            <h4>Trend za posledních 14 dní</h4>
                            <ResponsiveContainer width="100%" height={200}>
                                <LineChart data={data.usage_by_day} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                                    <XAxis
                                        dataKey="date"
                                        tick={{ fontSize: 10, fill: 'var(--text-secondary)' }}
                                        tickFormatter={(d) => {
                                            const date = new Date(d)
                                            return `${date.getDate()}.${date.getMonth() + 1}.`
                                        }}
                                        tickLine={false}
                                        axisLine={{ stroke: 'var(--border-color)' }}
                                    />
                                    <YAxis
                                        tick={{ fontSize: 10, fill: 'var(--text-secondary)' }}
                                        tickLine={false}
                                        axisLine={false}
                                        tickFormatter={(v) => `${Math.round(v / 60)}m`}
                                    />
                                    <Tooltip
                                        formatter={(value) => [formatDuration(value), 'Čas']}
                                        labelFormatter={(label) => label}
                                        contentStyle={{
                                            background: 'var(--bg-primary)',
                                            border: '1px solid var(--border-color)',
                                            borderRadius: '8px'
                                        }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="duration_seconds"
                                        stroke="#6366f1"
                                        strokeWidth={2}
                                        dot={{ fill: '#6366f1', strokeWidth: 2, r: 3 }}
                                        activeDot={{ r: 5 }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </>
                    )}
                </div>

                {/* Footer info */}
                <div className="modal-footer">
                    {data.first_use_date && (
                        <span>První použití: {data.first_use_date}</span>
                    )}
                    {data.last_use_date && (
                        <span>Poslední použití: {data.last_use_date}</span>
                    )}
                </div>
            </div>
        </div>
    )
}

export default AppDetailsModal
