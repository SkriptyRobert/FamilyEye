import React from 'react'
import { Lock, WifiOff, Camera, Maximize2 } from 'lucide-react'
import './QuickActionsBar.css'

/**
 * Quick action buttons for device control
 * Extracted from StatusOverview.jsx
 * 
 * @param {Object} props
 * @param {string} props.deviceId - Device ID
 * @param {boolean} props.isOnline - Whether device is online
 * @param {string} props.lastScreenshot - URL of last screenshot (optional)
 * @param {Object} props.pending - Pending actions state { [actionKey]: boolean }
 * @param {Object} props.feedback - Action feedback { [actionKey]: { status, message } }
 * @param {Function} props.onAction - Handler for device actions (lock, pause-internet, screenshot)
 * @param {Function} props.onViewScreenshot - Handler to open screenshot modal
 */
const QuickActionsBar = ({
    deviceId,
    isOnline = false,
    lastScreenshot = null,
    pending = {},
    feedback = {},
    onAction,
    onViewScreenshot
}) => {
    const lockKey = `${deviceId}-lock`
    const internetKey = `${deviceId}-pause-internet`
    const screenshotKey = `${deviceId}-screenshot`

    const currentFeedback = feedback[lockKey] || feedback[internetKey] || feedback[screenshotKey]

    if (!isOnline) {
        return (
            <div className="quick-actions offline">
                <span className="offline-notice">Zařízení není dostupné</span>
            </div>
        )
    }

    return (
        <div className="quick-actions" onClick={e => e.stopPropagation()}>
            <div className="action-group">
                <button
                    className={`action-btn lock ${pending[lockKey] ? 'pending' : ''}`}
                    onClick={() => onAction(deviceId, 'lock')}
                    disabled={pending[lockKey]}
                >
                    <Lock size={14} /> Zamknout
                </button>
                <button
                    className={`action-btn internet ${pending[internetKey] ? 'pending' : ''}`}
                    onClick={() => onAction(deviceId, 'pause-internet')}
                    disabled={pending[internetKey]}
                >
                    <WifiOff size={14} /> Internet
                </button>
                <button
                    className={`action-btn screenshot ${pending[screenshotKey] ? 'pending' : ''}`}
                    onClick={() => onAction(deviceId, 'screenshot')}
                    disabled={pending[screenshotKey]}
                    title="Pořídit screenshot"
                >
                    <Camera size={14} /> Foto
                </button>
            </div>

            {currentFeedback && (
                <div className={`action-feedback ${currentFeedback.status}`}>
                    {currentFeedback.message}
                </div>
            )}

            {lastScreenshot && (
                <button
                    className="view-screenshot-btn"
                    onClick={() => onViewScreenshot(deviceId)}
                >
                    <Maximize2 size={12} /> Poslední snímek
                </button>
            )}
        </div>
    )
}

export default QuickActionsBar
