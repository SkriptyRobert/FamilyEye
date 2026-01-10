import React from 'react'
import { Clock, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'
import { formatDuration, formatLimitText } from '../../utils/formatting'
import './LimitProgressBar.css'

/**
 * Progress bar showing app limit usage with status badges
 * Extracted from StatusOverview.jsx expanded section
 * 
 * @param {Object} props
 * @param {string} props.appName - Name of the app
 * @param {number} props.usedSeconds - Time used in seconds
 * @param {number} props.limitMinutes - Limit in minutes
 * @param {string} props.status - Status: 'ok', 'warning', 'critical', 'exceeded'
 * @param {string} props.color - Color class: 'green', 'orange', 'red'
 * @param {number} props.percentage - Usage percentage (0-100+)
 * @param {boolean} props.showAdjustButtons - Whether to show +/- buttons
 * @param {boolean} props.isPending - Whether an action is pending
 * @param {Object} props.feedback - Feedback object { status, message }
 * @param {Function} props.onAdjust - Handler for limit adjustment (minutes delta)
 */
const LimitProgressBar = ({
    appName,
    usedSeconds,
    limitMinutes,
    status = 'ok',
    color = 'green',
    percentage = 0,
    showAdjustButtons = false,
    isPending = false,
    feedback = null,
    onAdjust
}) => {
    const getStatusBadge = () => {
        switch (status) {
            case 'exceeded':
                return (
                    <span className="limit-exceeded-badge">
                        <XCircle size={14} /> Limit dosažen
                    </span>
                )
            case 'critical':
                return (
                    <span className="limit-critical-badge">
                        <AlertTriangle size={14} /> Téměř vyčerpán
                    </span>
                )
            case 'warning':
                return (
                    <span className="limit-warning-badge">
                        <Clock size={14} /> Blízko limitu
                    </span>
                )
            default:
                return (
                    <span className="limit-ok-badge">
                        <CheckCircle size={14} /> Zbývá {Math.max(0, limitMinutes - Math.floor(usedSeconds / 60))} min
                    </span>
                )
        }
    }

    return (
        <div className={`limit-progress-bar ${color}`}>
            <div className="limit-header">
                <span className="limit-app-name">{appName}</span>
                <span className={`limit-text ${color}`}>
                    {formatLimitText(usedSeconds, limitMinutes)}
                </span>
            </div>

            <div className="limit-bar-container">
                <div
                    className={`limit-bar ${color}`}
                    style={{ width: `${Math.min(100, percentage)}%` }}
                />
            </div>

            <div className="limit-footer">
                {getStatusBadge()}
            </div>

            {showAdjustButtons && (
                <div className="limit-quick-actions">
                    <button
                        className={`limit-action-btn subtract ${isPending ? 'pending' : ''}`}
                        onClick={() => onAdjust(-15)}
                        disabled={isPending}
                        title="Odebrat 15 minut"
                    >
                        -15m
                    </button>
                    <button
                        className={`limit-action-btn add ${isPending ? 'pending' : ''}`}
                        onClick={() => onAdjust(15)}
                        disabled={isPending}
                        title="Přidat 15 minut"
                    >
                        +15m
                    </button>
                    <button
                        className={`limit-action-btn add-more ${isPending ? 'pending' : ''}`}
                        onClick={() => onAdjust(30)}
                        disabled={isPending}
                        title="Přidat 30 minut"
                    >
                        +30m
                    </button>
                </div>
            )}

            {feedback && (
                <div className={`limit-action-feedback ${feedback.status}`}>
                    {feedback.message}
                </div>
            )}
        </div>
    )
}

export default LimitProgressBar
