import React from 'react'
import { createPortal } from 'react-dom'
import DynamicIcon from '../DynamicIcon'
import './ActivityTimeline.css'
import { formatTime, formatDuration } from '../../utils/formatting'

const ActivityTimeline = ({ timeline, date }) => {
    if (!timeline || timeline.length === 0) {
        return (
            <div className="activity-timeline-container empty">
                <p>Žádná aktivita pro tento den</p>
            </div>
        )
    }

    // Calculate day boundaries based on the first event or the selected date
    // Assuming timeline data timestamps are in seconds (UNIX)

    // Normalize to 00:00–23:59 of the day of the first event.
    const firstEventDate = new Date(timeline[0].start_ts * 1000)
    const dayStart = new Date(firstEventDate)
    dayStart.setHours(0, 0, 0, 0)
    const dayStartTs = dayStart.getTime() / 1000

    const dayEnd = new Date(dayStart)
    dayEnd.setHours(23, 59, 59, 999)
    const dayEndTs = dayEnd.getTime() / 1000

    const dayDuration = dayEndTs - dayStartTs

    // Color palette for apps (consistent hashing or round-robin)
    const getAppColor = (appName) => {
        let hash = 0;
        for (let i = 0; i < appName.length; i++) {
            hash = appName.charCodeAt(i) + ((hash << 5) - hash);
        }
        const c = (hash & 0x00FFFFFF).toString(16).toUpperCase();
        return '#' + "00000".substring(0, 6 - c.length) + c;
    }

    const predefinedColors = [
        '#6366f1', '#a855f7', '#ec4899', '#f97316', '#10b981', '#06b6d4', '#3b82f6', '#8b5cf6'
    ]
    const colorMap = {}

    const [hoveredSegment, setHoveredSegment] = React.useState(null)

    return (
        <div className="activity-timeline-container">

            <div className="timeline-track">
                {/* Hour markers background */}
                <div className="timeline-grid">
                    {[0, 6, 12, 18, 24].map(h => (
                        <div key={h} className="grid-line" style={{ left: `${(h / 24) * 100}%` }}>
                            <span className="grid-label">{h}:00</span>
                        </div>
                    ))}
                </div>

                {/* Activity Segments */}
                {timeline.map((segment, idx) => {
                    // Create a persistent color for this app
                    if (!colorMap[segment.app_name]) {
                        colorMap[segment.app_name] = predefinedColors[Object.keys(colorMap).length % predefinedColors.length]
                    }
                    const color = colorMap[segment.app_name]

                    const left = ((segment.start_ts - dayStartTs) / dayDuration) * 100
                    const width = (segment.duration / dayDuration) * 100

                    // Min width for visibility
                    const style = {
                        left: `${Math.max(0, Math.min(100, left))}%`,
                        width: `${Math.max(0.2, width)}%`, // At least 0.2% width to be visible
                        backgroundColor: color
                    }

                    return (
                        <div
                            key={idx}
                            className="timeline-segment"
                            style={style}
                            onMouseEnter={(e) => {
                                const rect = e.currentTarget.getBoundingClientRect()
                                setHoveredSegment({ ...segment, rect, color })
                            }}
                            onMouseLeave={() => setHoveredSegment(null)}
                        />
                    )
                })}
            </div>

            {/* Legend (Top 5 apps) */}
            <div className="timeline-legend">
                {Object.keys(colorMap).slice(0, 6).map(appName => (
                    <div key={appName} className="legend-item">
                        <span className="legend-dot" style={{ backgroundColor: colorMap[appName] }}></span>
                        <span className="legend-text">{appName}</span>
                    </div>
                ))}
            </div>

            {/* Portal Tooltip */}
            {hoveredSegment && hoveredSegment.rect && createPortal(
                <div
                    className="timeline-tooltip-portal"
                    style={{
                        position: 'fixed',
                        top: hoveredSegment.rect.top - 10,
                        left: hoveredSegment.rect.left + hoveredSegment.rect.width / 2,
                        transform: 'translate(-50%, -100%)',
                        zIndex: 9999,
                        pointerEvents: 'none'
                    }}
                >
                    <div className="tooltip-header">
                        <DynamicIcon name={hoveredSegment.icon_type || 'app'} size={14} />
                        <span className="tooltip-app">{hoveredSegment.app_name}</span>
                    </div>
                    <span className="tooltip-time">
                        {formatTime(hoveredSegment.start_ts)} - {formatTime(hoveredSegment.end_ts)} ({formatDuration(hoveredSegment.duration, true)})
                    </span>
                </div>,
                document.body
            )}
        </div>
    )
}

export default ActivityTimeline
