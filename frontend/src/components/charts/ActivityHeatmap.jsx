import React, { useState, useEffect, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { BarChart3, Flame } from 'lucide-react'
import api from '../../services/api'
import './ActivityHeatmap.css'

/**
 * ActivityHeatmap - Activity heatmap component (Elasticsearch/Kibana style)
 * 
 * Features:
 * - Grid: days (rows) × hours 0-23 (columns)
 * - Color scale: green → yellow → orange → red
 * - Tooltip with details
 * - Responsive
 * - Dark/Light mode support
 */
const ActivityHeatmap = ({ deviceId, days = 7, onDaysChange, largerDots = false }) => {
    const [data, setData] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [hoveredCell, setHoveredCell] = useState(null)

    useEffect(() => {
        if (deviceId) {
            fetchData()
        }
    }, [deviceId, days])

    const fetchData = async () => {
        try {
            setLoading(true)
            setError(null)
            const response = await api.get(
                `/api/reports/device/${deviceId}/usage-by-hour?days=${days}`
            )
            // Handle response - API returns { device_id, days_analyzed, data: [...] }
            const responseData = response.data?.data || response.data
            if (Array.isArray(responseData)) {
                setData(responseData)
            } else {
                console.warn('Unexpected response format:', response.data)
                setData([])
            }
        } catch (err) {
            console.error('Error fetching heatmap data:', err)
            setError('Nepodařilo se načíst data')
            setData([])  // Clear data on error
        } finally {
            setLoading(false)
        }
    }

    // Transform data into grid format: { date: { hour: value } }
    const heatmapGrid = useMemo(() => {
        if (!data || data.length === 0) return { dates: [], grid: {} }

        const grid = {}
        const datesSet = new Set()

        data.forEach(item => {
            if (!item.date) return
            datesSet.add(item.date)
            if (!grid[item.date]) {
                grid[item.date] = {}
            }
            grid[item.date][item.hour] = {
                duration_seconds: item.duration_seconds,
                duration_minutes: item.duration_minutes,
                apps_count: item.apps_count,
                sessions_count: item.sessions_count
            }
        })

        // Sort dates (newest first for display)
        const dates = Array.from(datesSet).sort().reverse()

        return { dates, grid }
    }, [data])

    // Find max value for color scaling
    const maxDuration = useMemo(() => {
        if (!data || data.length === 0) return 1
        return Math.max(...data.map(d => d.duration_seconds || 0), 1)
    }, [data])

    // Get color based on intensity (0-1)
    const getColor = (intensity) => {
        if (intensity === 0) return 'var(--heatmap-empty)'
        if (intensity < 0.25) return 'var(--heatmap-low)'
        if (intensity < 0.5) return 'var(--heatmap-medium)'
        if (intensity < 0.75) return 'var(--heatmap-high)'
        return 'var(--heatmap-max)'
    }

    // Format date for display
    const formatDate = (dateStr) => {
        const date = new Date(dateStr)
        const days = ['Ne', 'Po', 'Út', 'St', 'Čt', 'Pá', 'So']
        return `${days[date.getDay()]} ${date.getDate()}.${date.getMonth() + 1}.`
    }

    // Format duration for tooltip
    const formatDuration = (seconds) => {
        if (!seconds || seconds === 0) return '0 min'
        const hours = Math.floor(seconds / 3600)
        const minutes = Math.floor((seconds % 3600) / 60)
        if (hours > 0) return `${hours}h ${minutes}m`
        return `${minutes} min`
    }

    if (loading) {
        return (
            <div className="heatmap-container">
                <div className="heatmap-loading">
                    <div className="loading-spinner"></div>
                    <span>Načítání heatmapy...</span>
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="heatmap-container">
                <div className="heatmap-error">{error}</div>
            </div>
        )
    }

    if (!data || data.length === 0) {
        return (
            <div className="heatmap-container">
                <div className="heatmap-empty">
                    <div className="empty-icon"><BarChart3 size={48} color="var(--text-muted)" /></div>
                    <span>Žádná data pro zobrazení</span>
                </div>
            </div>
        )
    }

    const hours = Array.from({ length: 24 }, (_, i) => i)

    return (
        <div className={`heatmap-container ${largerDots ? 'larger-dots' : ''}`}>
            <div className="heatmap-header">
                <h4><Flame size={18} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> Aktivita podle hodin</h4>
                <div className="heatmap-controls">
                    {onDaysChange && (
                        <select
                            value={days}
                            onChange={(e) => onDaysChange(parseInt(e.target.value))}
                            className="period-select"
                        >
                            <option value={7}>7 dní</option>
                            <option value={14}>14 dní</option>
                        </select>
                    )}
                </div>
            </div>

            <div className="heatmap-wrapper">
                {/* Hour labels (top) */}
                <div className="heatmap-hours-row">
                    <div className="heatmap-date-label"></div>
                    {hours.map(hour => (
                        <div key={hour} className="heatmap-hour-label">
                            {hour % 3 === 0 ? `${hour}:00` : ''}
                        </div>
                    ))}
                </div>

                {/* Grid rows */}
                {heatmapGrid.dates.map(date => (
                    <div key={date} className="heatmap-row">
                        <div className="heatmap-date-label">{formatDate(date)}</div>
                        {hours.map(hour => {
                            const cellData = heatmapGrid.grid[date]?.[hour]
                            const duration = cellData?.duration_seconds || 0
                            const intensity = duration / maxDuration

                            return (
                                <div
                                    key={`${date}-${hour}`}
                                    className="heatmap-cell"
                                    style={{ backgroundColor: getColor(intensity) }}
                                    onMouseEnter={(e) => {
                                        const rect = e.currentTarget.getBoundingClientRect()
                                        setHoveredCell({ date, hour, ...cellData, rect })
                                    }}
                                    onMouseLeave={() => setHoveredCell(null)}
                                />
                            )
                        })}
                    </div>
                ))}
            </div>

            {/* Legend */}
            <div className="heatmap-legend">
                <span className="legend-label">Méně</span>
                <div className="legend-scale">
                    <div className="legend-cell" style={{ backgroundColor: 'var(--heatmap-empty)' }}></div>
                    <div className="legend-cell" style={{ backgroundColor: 'var(--heatmap-low)' }}></div>
                    <div className="legend-cell" style={{ backgroundColor: 'var(--heatmap-medium)' }}></div>
                    <div className="legend-cell" style={{ backgroundColor: 'var(--heatmap-high)' }}></div>
                    <div className="legend-cell" style={{ backgroundColor: 'var(--heatmap-max)' }}></div>
                </div>
                <span className="legend-label">Více</span>
            </div>

            {/* Floating Tooltip via Portal to avoid overflow/stacking issues */}
            {hoveredCell && hoveredCell.rect && createPortal(
                <div
                    className="heatmap-tooltip"
                    style={{
                        position: 'fixed',
                        top: hoveredCell.rect.top - 10,
                        left: hoveredCell.rect.left + hoveredCell.rect.width / 2,
                        transform: 'translate(-50%, -100%)',
                    }}
                >
                    <div className="tooltip-time">{formatDate(hoveredCell.date)} {hoveredCell.hour}:00-{hoveredCell.hour + 1}:00</div>
                    <div className="tooltip-duration">
                        <strong>{formatDuration(hoveredCell.duration_seconds || 0)}</strong>
                    </div>
                    {hoveredCell.sessions_count !== undefined && (
                        <div className="tooltip-detail">
                            {hoveredCell.apps_count || 0} aplikací
                        </div>
                    )}
                </div>,
                document.body
            )}
        </div>
    )
}

export default ActivityHeatmap
