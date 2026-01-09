import React, { useState, useEffect, useMemo } from 'react'
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    Cell
} from 'recharts'
import { Calendar } from 'lucide-react'
import api from '../../services/api'
import './WeeklyPatternChart.css'

/**
 * WeeklyPatternChart - Bar chart showing average usage by day of week
 * 
 * Features:
 * - 7 bars (Monday-Sunday)
 * - Peak hour indicator
 * - Responsive
 */
const WeeklyPatternChart = ({ deviceId, weeks = 4 }) => {
    const [data, setData] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (deviceId) {
            fetchData()
        }
    }, [deviceId, weeks])

    const fetchData = async () => {
        try {
            setLoading(true)
            setError(null)
            const response = await api.get(
                `/api/reports/device/${deviceId}/weekly-pattern?weeks=${weeks}`
            )
            // Ensure we have an array
            if (Array.isArray(response.data)) {
                setData(response.data)
            } else {
                console.warn('Unexpected response format:', response.data)
                setData([])
            }
        } catch (err) {
            console.error('Error fetching weekly pattern:', err)
            setError('Nepodařilo se načíst data')
            setData([])
        } finally {
            setLoading(false)
        }
    }

    // Transform data for chart
    const chartData = useMemo(() => {
        if (!data || data.length === 0) return []

        return data.map(item => ({
            day: item.day_name.substring(0, 2),
            dayFull: item.day_name,
            hours: item.avg_duration_hours,
            sessions: item.avg_sessions_count,
            peakHour: item.peak_hour,
            isWeekend: item.day_of_week >= 5
        }))
    }, [data])

    // Find max for highlighting
    const maxHours = useMemo(() => {
        if (!chartData || chartData.length === 0) return 0
        return Math.max(...chartData.map(d => d.hours || 0))
    }, [chartData])

    // Custom bar colors
    const getBarColor = (entry) => {
        if (entry.hours === maxHours && maxHours > 0) return '#ef4444'  // Max day
        if (entry.isWeekend) return '#a855f7'  // Weekend
        return '#6366f1'  // Weekday
    }

    // Custom tooltip
    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const item = payload[0]?.payload
            return (
                <div className="weekly-tooltip">
                    <div className="tooltip-header">{item?.dayFull}</div>
                    <div className="tooltip-row">
                        <span className="tooltip-label">Průměr:</span>
                        <span className="tooltip-value primary">{item?.hours?.toFixed(1)} h/den</span>
                    </div>
                    {item?.peakHour !== null && (
                        <div className="tooltip-row">
                            <span className="tooltip-label">Nejaktivnější:</span>
                            <span className="tooltip-value">{item?.peakHour}:00</span>
                        </div>
                    )}
                </div>
            )
        }
        return null
    }

    // Custom bar shape with rounded corners
    const CustomBar = (props) => {
        const { x, y, width, height, payload } = props
        const fill = getBarColor(payload)
        const radius = 6

        return (
            <g>
                <rect
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    rx={radius}
                    ry={radius}
                    fill={fill}
                />
                {/* Peak hour indicator */}
                {payload.peakHour !== null && height > 20 && (
                    <text
                        x={x + width / 2}
                        y={y + height - 8}
                        textAnchor="middle"
                        fontSize="10"
                        fill="white"
                        fontWeight="bold"
                    >
                        {payload.peakHour}:00
                    </text>
                )}
            </g>
        )
    }

    if (loading) {
        return (
            <div className="weekly-container">
                <div className="weekly-loading">
                    <div className="loading-spinner"></div>
                    <span>Načítání týdenních vzorů...</span>
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="weekly-container">
                <div className="weekly-error">{error}</div>
            </div>
        )
    }

    if (!data || data.length === 0) {
        return (
            <div className="weekly-container">
                <div className="weekly-empty">
                    <div className="empty-icon"><Calendar size={48} color="var(--text-muted)" /></div>
                    <span>Žádná data pro zobrazení</span>
                </div>
            </div>
        )
    }

    return (
        <div className="weekly-container">
            <div className="weekly-header">
                <h4><Calendar size={18} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> Vzory v týdnu</h4>
                <span className="weekly-period">Průměr za {weeks} týdny</span>
            </div>

            <div className="weekly-chart">
                <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                        <XAxis
                            dataKey="day"
                            tick={{ fontSize: 12, fill: 'var(--text-primary)', fontWeight: 600 }}
                            tickLine={false}
                            axisLine={{ stroke: 'var(--border-color)' }}
                        />
                        <YAxis
                            tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                            tickLine={false}
                            axisLine={false}
                            unit="h"
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(99, 102, 241, 0.1)' }} />
                        <Bar
                            dataKey="hours"
                            shape={<CustomBar />}
                            maxBarSize={50}
                        />
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* Legend */}
            <div className="weekly-legend">
                <div className="legend-item">
                    <div className="legend-dot" style={{ backgroundColor: '#6366f1' }}></div>
                    <span>Pracovní dny</span>
                </div>
                <div className="legend-item">
                    <div className="legend-dot" style={{ backgroundColor: '#a855f7' }}></div>
                    <span>Víkend</span>
                </div>
                <div className="legend-item">
                    <div className="legend-dot" style={{ backgroundColor: '#ef4444' }}></div>
                    <span>Nejvíce aktivní</span>
                </div>
            </div>
        </div>
    )
}

export default WeeklyPatternChart
