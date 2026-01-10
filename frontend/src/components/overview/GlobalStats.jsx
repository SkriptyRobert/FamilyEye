import React, { memo } from 'react'
import { Monitor, Smartphone, Activity } from 'lucide-react'
import { formatDuration } from '../../utils/formatting'
import '../StatusOverview.css' // Keep reusing base styles for now, or move to module

const GlobalStats = memo(({ devices = [], summaries = {} }) => {
    // Calculate totals
    const totalUsageToday = Object.values(summaries).reduce(
        (sum, s) => sum + (s?.today_usage_seconds || 0), 0
    )

    const onlineDevices = devices.filter(d => d.is_online).length

    // Calculate counts
    const counts = devices.reduce((acc, device) => {
        const type = device.device_type?.toLowerCase() || ''
        if (type.includes('pc') || type.includes('desk') || type.includes('lap')) {
            acc.pc++
        } else {
            acc.mobile++
        }
        return acc
    }, { pc: 0, mobile: 0 })

    return (
        <div className="global-stats">
            <div className="global-stat">
                <span className="stat-icon" style={{ color: '#10b981' }}>
                    <Activity size={24} />
                </span>
                <div className="stat-content">
                    <span className="stat-value">{formatDuration(totalUsageToday, true)}</span>
                    <span className="stat-label">Čas online dnes</span>
                </div>
            </div>

            <div className="global-stat">
                <span className="stat-icon" style={{ color: '#3b82f6' }}>
                    <Monitor size={24} />
                </span>
                <div className="stat-content">
                    <span className="stat-value">{counts.pc}</span>
                    <span className="stat-label">Počítače</span>
                </div>
            </div>

            <div className="global-stat">
                <span className="stat-icon" style={{ color: '#8b5cf6' }}>
                    <Smartphone size={24} />
                </span>
                <div className="stat-content">
                    <span className="stat-value">{counts.mobile}</span>
                    <span className="stat-label">Mobily</span>
                </div>
            </div>

            <div className="global-stat">
                <span className="stat-icon" style={{ color: onlineDevices > 0 ? '#10b981' : '#9ca3af' }}>
                    <div className={`status-dot ${onlineDevices > 0 ? 'online' : 'offline'}`}
                        style={{ width: 12, height: 12, borderRadius: '50%', background: 'currentColor' }} />
                </span>
                <div className="stat-content">
                    <span className="stat-value">{onlineDevices} / {devices.length}</span>
                    <span className="stat-label">Web Online</span>
                </div>
            </div>
        </div>
    )
})

GlobalStats.displayName = 'GlobalStats'
export default GlobalStats
