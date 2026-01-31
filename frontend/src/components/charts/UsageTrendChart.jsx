import React, { useState, useEffect, useMemo } from 'react'
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'
import { TrendingUp } from 'lucide-react'
import api from '../../services/api'
import './UsageTrendChart.css'

/**
 * UsageTrendChart - Line chart component for usage trends
 * 
 * Features:
 * - Time axis (7/30 days)
 * - Multiple metrics toggle
 * - Tooltip with details
 * - Responsive
 */
const UsageTrendChart = ({ deviceId, period = 'week', onPeriodChange }) => {
    const [data, setData] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [showApps, setShowApps] = useState(false)

    useEffect(() => {
        if (deviceId) {
            fetchData()
        }
    }, [deviceId, period])

    const fetchData = async () => {
        try {
            setLoading(true)
            setError(null)
            const response = await api.get(
                `/api/reports/device/${deviceId}/usage-trends?period=${period}`
            )
            setData(response.data)
        } catch (err) {
            console.error('Error fetching trends data:', err)
            setError('Nepodařilo se načíst data')
        } finally {
            setLoading(false)
        }
    }

    // Transform data for chart
    const chartData = useMemo(() => {
        if (!data || data.length === 0) return []

        return data.map(item => ({
            date: formatDateShort(item.date),
            fullDate: item.date,
            hours: item.total_hours,
            apps: item.apps_count,
            sessions: item.sessions_count,
            peakHour: item.peak_hour,
            firstActivity: item.first_activity,
            lastActivity: item.last_activity
        }))
    }, [data])

    // Format date for x-axis
    function formatDateShort(dateStr) {
        if (!dateStr) return ''
        const date = new Date(dateStr)
        return `${date.getDate()}.${date.getMonth() + 1}.`
    }

    // Custom tooltip
    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            const item = payload[0]?.payload
            return (
                <div className="trend-tooltip">
                    <div className="tooltip-header">{item?.fullDate}</div>
                    <div className="tooltip-row">
                        <span className="tooltip-label">Aktivita:</span>
                        <span className="tooltip-value primary">{item?.hours?.toFixed(1)} hodin</span>
                    </div>
                    {showApps && (
                        <div className="tooltip-row">
                            <span className="tooltip-label">Aplikací:</span>
                            <span className="tooltip-value">{item?.apps}</span>
                        </div>
                    )}
                    {item?.peakHour !== null && (
                        <div className="tooltip-row">
                            <span className="tooltip-label">Nejaktivnější:</span>
                            <span className="tooltip-value">{item?.peakHour}:00</span>
                        </div>
                    )}
                    {item?.firstActivity && item?.lastActivity && (
                        <div className="tooltip-row">
                            <span className="tooltip-label">Rozmezí:</span>
                            <span className="tooltip-value">{item?.firstActivity} - {item?.lastActivity}</span>
                        </div>
                    )}
                </div>
            )
        }
        return null
    }

    if (loading) {
        return (
            <div className="trend-container">
                <div className="trend-loading">
                    <div className="loading-spinner"></div>
                    <span>Načítání trendů...</span>
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="trend-container">
                <div className="trend-error">{error}</div>
            </div>
        )
    }

    if (!data || data.length === 0) {
        return (
            <div className="trend-container">
                <div className="trend-empty">
                    <div className="empty-icon"><TrendingUp size={48} color="var(--text-muted)" /></div>
                    <span>Žádná data pro zobrazení</span>
                </div>
            </div>
        )
    }

    return (
        <div className="trend-container">
            <div className="trend-header">
                <h4><TrendingUp size={18} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> Trendy použití</h4>
                <div className="trend-controls">
                    {onPeriodChange && (
                        <select
                            value={period}
                            onChange={(e) => onPeriodChange(e.target.value)}
                            className="period-select"
                        >
                            <option value="week">Týden</option>
                            <option value="month">Měsíc</option>
                        </select>
                    )}
                    <label className="toggle-label">
                        <input
                            type="checkbox"
                            checked={showApps}
                            onChange={(e) => setShowApps(e.target.checked)}
                        />
                        <span>Počet aplikací</span>
                    </label>
                </div>
            </div>

            <div className="trend-chart">
                <ResponsiveContainer width="100%" height={280}>
                    <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                        <XAxis
                            dataKey="date"
                            tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                            tickLine={false}
                            axisLine={{ stroke: 'var(--border-color)' }}
                        />
                        <YAxis
                            tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                            tickLine={false}
                            axisLine={{ stroke: 'var(--border-color)' }}
                            unit="h"
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Line
                            type="monotone"
                            dataKey="hours"
                            name="Hodiny"
                            stroke="#6366f1"
                            strokeWidth={3}
                            dot={{ fill: '#6366f1', strokeWidth: 2, r: 4 }}
                            activeDot={{ r: 6, stroke: '#6366f1', strokeWidth: 2 }}
                        />
                        {showApps && (
                            <Line
                                type="monotone"
                                dataKey="apps"
                                name="Aplikace"
                                stroke="#10b981"
                                strokeWidth={2}
                                strokeDasharray="5 5"
                                dot={{ fill: '#10b981', strokeWidth: 2, r: 3 }}
                            />
                        )}
                    </LineChart>
                </ResponsiveContainer>
            </div>

            {/* Stats summary */}
            <div className="trend-stats">
                <div className="trend-stat">
                    <span className="stat-value">
                        {(chartData.reduce((sum, d) => sum + (d.hours || 0), 0) / chartData.length).toFixed(1)}h
                    </span>
                    <span className="stat-label">Průměr/den</span>
                </div>
                <div className="trend-stat">
                    <span className="stat-value">
                        {Math.max(...chartData.map(d => d.hours || 0)).toFixed(1)}h
                    </span>
                    <span className="stat-label">Maximum</span>
                </div>
                <div className="trend-stat">
                    <span className="stat-value">
                        {Math.round(chartData.reduce((sum, d) => sum + (d.apps || 0), 0) / chartData.length)}
                    </span>
                    <span className="stat-label">Ø aplikací</span>
                </div>
            </div>
        </div>
    )
}

export default UsageTrendChart
