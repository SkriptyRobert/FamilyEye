import React from 'react'
import { Smartphone, X, XCircle, Clock, Check } from 'lucide-react'
import DynamicIcon from '../DynamicIcon'
import { formatDuration, formatRelativeTime } from '../../utils/formatting'
import './AllAppsModal.css'

/**
 * Modal showing all apps for a device with quick actions
 * Extracted from StatusOverview.jsx
 * 
 * @param {Object} props
 * @param {Object} props.device - Device object
 * @param {Array} props.apps - List of apps to display
 * @param {Array} props.rules - Device rules for checking existing rules
 * @param {Date} props.lastFetch - Last data fetch time
 * @param {Object} props.actionPending - Pending actions state
 * @param {Object} props.actionFeedback - Action feedback state
 * @param {Function} props.onAppAction - Handler for app actions (block, limit)
 * @param {Function} props.onClose - Handler to close modal
 */
const AllAppsModal = ({
    device,
    apps = [],
    rules = [],
    lastFetch,
    actionPending = {},
    actionFeedback = {},
    onAppAction,
    onClose
}) => {
    if (!device) return null

    return (
        <div className="all-apps-modal-overlay" onClick={onClose}>
            <div className="all-apps-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <div>
                        <h3><Smartphone size={20} /> Detailní přehled aplikací</h3>
                        <p className="modal-description">
                            Top 100 aplikací seřazených podle délky používání dnes (od 00:00).
                        </p>
                        <span className="modal-device-name">{device?.name}</span>
                    </div>
                    <button className="modal-close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <div className="modal-subtitle">
                    <span>Aktualizováno {lastFetch ? formatRelativeTime(lastFetch) : 'teď'}</span>
                    <span className="apps-count">{apps.length} aplikací</span>
                </div>

                <div className="modal-apps-list">
                    {apps.length === 0 ? (
                        <div className="no-apps-message">
                            Zatím žádné aplikace nebyly použity
                        </div>
                    ) : (
                        apps.map((app, index) => {
                            const appName = app.app_name || app.display_name
                            const hasRule = rules.some(r =>
                                r.app_name?.toLowerCase() === appName?.toLowerCase()
                            )
                            const blockKey = `${device.id}-app-${appName}-block`
                            const limitKey = `${device.id}-app-${appName}-limit-60`
                            const isPending = actionPending[blockKey] || actionPending[limitKey]
                            const feedback = actionFeedback[blockKey] || actionFeedback[limitKey]

                            return (
                                <div key={index} className="modal-app-item">
                                    <div className="modal-app-info">
                                        <span className="modal-app-name">{app.display_name}</span>
                                        <span className="modal-app-duration">
                                            {formatDuration(app.duration_seconds, true)}
                                        </span>
                                    </div>

                                    {!hasRule ? (
                                        <div className="modal-app-actions">
                                            <button
                                                className={`modal-action-btn block ${isPending ? 'pending' : ''}`}
                                                onClick={() => onAppAction(device.id, appName, 'block')}
                                                disabled={isPending}
                                                title="Zablokovat aplikaci"
                                            >
                                                <XCircle size={14} style={{ marginRight: '4px' }} /> Blokovat
                                            </button>
                                            <button
                                                className={`modal-action-btn limit ${isPending ? 'pending' : ''}`}
                                                onClick={() => onAppAction(device.id, appName, 'limit-60')}
                                                disabled={isPending}
                                                title="Nastavit limit 1 hodina"
                                            >
                                                <Clock size={12} style={{ marginRight: '2px' }} /> Limit 1h
                                            </button>
                                        </div>
                                    ) : (
                                        <span className="modal-has-rule">
                                            <Check size={10} style={{ marginRight: '2px' }} /> Má pravidlo
                                        </span>
                                    )}

                                    {feedback && (
                                        <div className={`modal-feedback ${feedback.status}`}>
                                            {feedback.message}
                                        </div>
                                    )}
                                </div>
                            )
                        })
                    )}
                </div>

                <div className="modal-footer">
                    <button className="modal-close-btn-full" onClick={onClose}>
                        Zavřít
                    </button>
                </div>
            </div>
        </div>
    )
}

export default AllAppsModal
