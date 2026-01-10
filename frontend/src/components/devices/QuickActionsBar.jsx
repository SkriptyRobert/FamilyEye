import React from 'react'
import { Lock, WifiOff, Camera, Maximize2 } from 'lucide-react'
import './QuickActionsBar.css'

/**
 * Quick action buttons for device control
 * Extracted from StatusOverview.jsx
 * 
 * @param {Object} props
 * @param {Object} props.device - Device object { id, status, ... }
 * @param {Object} props.actionPending - Pending actions state { [actionKey]: boolean }
 * @param {Object} props.actionFeedback - Action feedback { [actionKey]: { status, message } }
 * @param {Function} props.onDeviceAction - Handler for device actions (lock, pause-internet, screenshot)
 * @param {Function} props.onShowScreenshot - Handler to open screenshot modal
 */
const QuickActionsBar = ({
    device,
    actionPending,
    actionFeedback,
    onDeviceAction, // (deviceId, action)
    onShowScreenshot
}) => {
    // Helper to check if specific action is pending
    const isPending = (action) => actionPending[`${device.id}-${action}`]

    // Helper to check feedback for specific action
    const getFeedback = (action) => actionFeedback[`${device.id}-${action}`]

    // Check if screenshot was just successful to highlight view button
    const screenshotFeedback = getFeedback('screenshot')
    const isScreenshotReady = screenshotFeedback?.status === 'success'

    return (
        <div className={`quick-actions ${device.status === 'offline' ? 'offline' : ''}`}>
            {device.status === 'offline' ? (
                <p className="offline-notice">Zařízení je offline - rychlé akce nejsou dostupné</p>
            ) : (
                <>
                    <div className="action-group">
                        <button
                            className={`action-btn lock ${isPending('lock') ? 'pending' : ''}`}
                            onClick={() => onDeviceAction(device.id, 'lock')}
                            disabled={isPending('lock')}
                        >
                            <Lock size={16} /> Zamknout
                        </button>

                        <button
                            className={`action-btn internet ${isPending('pause-internet') ? 'pending' : ''}`}
                            onClick={() => onDeviceAction(device.id, 'pause-internet')} // Default 1h
                            disabled={isPending('pause-internet')}
                        >
                            <WifiOff size={16} /> Internet
                        </button>

                        <button
                            className={`action-btn screenshot ${isPending('screenshot') ? 'pending' : ''}`}
                            onClick={() => onDeviceAction(device.id, 'screenshot')}
                            disabled={isPending('screenshot')}
                            title="Pořídit aktuální snímek obrazovky"
                        >
                            <Monitor size={16} /> Vyfotit obrazovku
                        </button>
                    </div>

                    <div className="action-group-secondary">
                        <button
                            className={`view-screenshot-btn ${isScreenshotReady ? 'pulse-attention' : ''}`}
                            onClick={() => onShowScreenshot(device.id)}
                            title="Zobrazit poslední snímek"
                        >
                            Zobrazit snímek <ExternalLink size={14} />
                        </button>
                    </div>
                </>
            )}

            {/* Display feedback for any action that has it */}
            {['lock', 'unlock', 'pause-internet', 'resume-internet', 'screenshot'].map(action => {
                const fb = getFeedback(action)
                if (!fb) return null
                return (
                    <div key={action} className={`action-feedback ${fb.status}`}>
                        {fb.message}
                    </div>
                )
            })}
        </div>
    )
}

export default QuickActionsBar
