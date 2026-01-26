import React, { useState, useEffect, useMemo } from 'react'
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'
import { Calendar, MapPin } from 'lucide-react'
import api from '../../services/api'
import './WeeklyBarChart.css'

/**
 * WeeklyBarChart - Bar chart showing daily usage for the current week
 * Today's bar is highlighted in a different color
 */
const WeeklyBarChart = ({ deviceId, onDateSelect, selectedDate }) => {
    const [data, setData] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (deviceId) {
            fetchData()
        }
    }, [deviceId])

    const fetchData = async () => {
        try {
            setLoading(true)
            setError(null)
            const response = await api.get(
                `/api/reports/device/${deviceId}/weekly-current`
            )
            // Ensure we have an array
            if (Array.isArray(response.data)) {
                setData(response.data)
            } else {
                setData([])
            }
        } catch (err) {
            console.error('Error fetching weekly data:', err)
            setError('Nepodařilo se načíst data')
            setData([])
        } finally {
            setLoading(false)
        }
    }

    // Get current day index (0 = Monday, 6 = Sunday)
    const todayIndex = useMemo(() => {
        const day = new Date().getDay()
        return day === 0 ? 6 : day - 1 // Convert Sunday=0 to index 6
    }, [])

    // Transform data for chart - ensure we have all 7 days
    const chartData = useMemo(() => {
        const dayNames = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne']
        const fullDayNames = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle']

        // Create array with all days
        const result = dayNames.map((name, idx) => {
            const date = new Date()
            date.setDate(date.getDate() + (idx - todayIndex))
            const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

            return {
                day: name,
                fullDay: fullDayNames[idx],
                hours: 0,
                isToday: idx === todayIndex,
                isWeekend: idx >= 5,
                dateStr
            }
        })

        // Fill in data from API
        if (data && data.length > 0) {
            data.forEach(item => {
                const dayIndex = item.day_of_week
                if (dayIndex >= 0 && dayIndex < 7) {
                    result[dayIndex].hours = item.total_hours || 0
                }
            })
        }

        return result
    }, [data, todayIndex])

    // Custom tooltip
    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const item = payload[0]?.payload
            return (
                <div className="weekly-bar-tooltip">
                    <div className="tooltip-day">{item?.fullDay}</div>
                    <div className="tooltip-hours">
                        <strong>{item?.hours?.toFixed(1)}h</strong>
                    </div>
                    {item?.isToday && <div className="tooltip-today"><MapPin size={10} style={{ marginRight: '4px' }} /> Dnes</div>}
                </div>
            )
        }
        return null
    }

    if (loading) {
        return (
            <div className="weekly-bar-container">
                <div className="weekly-bar-loading">
                    <div className="loading-spinner"></div>
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="weekly-bar-container">
                <div className="weekly-bar-error">{error}</div>
            </div>
        )
    }

    // Calculate max for better scaling
    const maxHours = Math.max(...chartData.map(d => d.hours), 1)

    return (
        <div className="weekly-bar-container">
            <div className="weekly-bar-header">
                <h3><Calendar size={20} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> Tento týden</h3>
                <span className="weekly-total">
                    Celkem: {chartData.reduce((sum, d) => sum + d.hours, 0).toFixed(1)}h
                </span>
            </div>

            <div className="weekly-bar-chart">
                <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }} barCategoryGap="15%">
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" horizontal={true} vertical={false} opacity={0.5} />
                        <XAxis
                            dataKey="day"
                            tick={{ fontSize: 13, fill: 'var(--text-primary)', fontWeight: 700 }}
                            tickLine={false}
                            axisLine={{ stroke: 'var(--border-color)' }}
                        />
                        <YAxis
                            tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                            tickLine={false}
                            axisLine={false}
                            unit="h"
                            domain={[0, Math.ceil(maxHours * 1.2)]}
                            width={35}
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(99, 102, 241, 0.1)' }} />
                        <Bar
                            dataKey="hours"
                            radius={[8, 8, 0, 0]}
                            barSize={50}
                        >
                            {chartData.map((entry, index) => {
                                const isSelected = selectedDate === entry.dateStr
                                return (
                                    <Cell
                                        key={`cell-${index}`}
                                        cursor="pointer"
                                        fill={isSelected ? '#f97316' : (entry.isToday ? '#10b981' : entry.isWeekend ? '#a855f7' : '#6366f1')}
                                        opacity={isSelected || entry.isToday ? 1 : 0.6}
                                        stroke={isSelected ? '#f97316' : (entry.isToday ? '#10b981' : 'none')}
                                        strokeWidth={isSelected || entry.isToday ? 2 : 0}
                                        onClick={() => onDateSelect && onDateSelect(entry.dateStr)}
                                    />
                                )
                            })}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* Day Legend */}
            <div className="weekly-bar-legend">
                <div className="legend-item">
                    <span className="legend-dot" style={{ backgroundColor: '#6366f1' }}></span>
                    <span>Pracovní dny</span>
                </div>
                <div className="legend-item">
                    <span className="legend-dot" style={{ backgroundColor: '#a855f7' }}></span>
                    <span>Víkend</span>
                </div>
                <div className="legend-item">
                    <span className="legend-dot" style={{ backgroundColor: '#10b981' }}></span>
                    <span>Dnes</span>
                </div>
            </div>
        </div>
    )
}

export default WeeklyBarChart
