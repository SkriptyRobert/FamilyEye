import React from 'react'
import { XCircle, CircleDot, CheckCircle } from 'lucide-react'
import './LimitChip.css'

/**
 * Compact limit status chip for device cards
 * Shows app name, usage/limit ratio, and status indicator
 * 
 * @param {Object} props
 * @param {string} props.appName - Name of the app
 * @param {number} props.usedSeconds - Time used in seconds
 * @param {number} props.limitMinutes - Limit in minutes
 * @param {string} props.status - Status: 'ok', 'warning', 'critical', 'exceeded'
 * @param {string} props.color - Color class: 'green', 'orange', 'red'
 * @param {Function} props.onClick - Optional click handler
 */
const LimitChip = ({
    appName,
    usedSeconds,
    limitMinutes,
    status = 'ok',
    color = 'green',
    onClick
}) => {
    const usedMinutes = Math.min(Math.floor(usedSeconds / 60), limitMinutes)

    const getStatusIcon = () => {
        switch (status) {
            case 'exceeded':
                return <XCircle size={10} color="#ef4444" />
            case 'critical':
            case 'warning':
                return <CircleDot size={10} color="#f59e0b" />
            default:
                return <CheckCircle size={10} color="#10b981" />
        }
    }

    return (
        <div
            className={`limit-chip ${color}`}
            onClick={onClick}
            role={onClick ? 'button' : undefined}
            tabIndex={onClick ? 0 : undefined}
        >
            <span className="limit-chip-name">{appName}</span>
            <span className="limit-chip-value">
                {usedMinutes}/{limitMinutes}m
            </span>
            <span className="limit-chip-indicator">
                {getStatusIcon()}
            </span>
        </div>
    )
}

export default LimitChip
