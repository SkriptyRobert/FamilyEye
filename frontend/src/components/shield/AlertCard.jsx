import React from 'react'
import { AlertTriangle, Eye, Trash2, Globe, Smartphone, Plus } from 'lucide-react'
import { formatTimestamp } from '../../utils/formatting'

const SEVERITY_CONFIG = {
    critical: { color: '#ef4444', label: 'Kritické' },
    high: { color: '#f97316', label: 'Vysoké' },
    medium: { color: '#eab308', label: 'Střední' },
    low: { color: '#22c55e', label: 'Nízké' }
}

const AlertCard = ({
    alert,
    isSelected,
    isExpanded,
    onSelect,
    onToggleExpand,
    onDelete,
    onViewScreenshot
}) => {
    const severity = alert.severity || 'high'
    const detectedText = alert.detected_text || ''
    const shouldTruncate = detectedText.length > 150

    return (
        <div
            className={`shield-alert-card ${severity} ${isSelected ? 'selected' : ''}`}
            onClick={onSelect}
        >
            {/* Selection Overlay/Checkbox */}
            <div className="alert-select-indicator">
                <div className={`select-checkbox ${isSelected ? 'checked' : ''}`}>
                    {isSelected && <Plus size={10} style={{ transform: 'rotate(45deg)' }} />}
                </div>
            </div>

            {/* Severity indicator stripe */}
            <div
                className="alert-severity-stripe"
                style={{ background: SEVERITY_CONFIG[severity]?.color || '#f97316' }}
            />

            <div className="alert-card-content">
                <div className="alert-card-header">
                    <div className="alert-icon-box" style={{
                        background: `${SEVERITY_CONFIG[severity]?.color}20`,
                        color: SEVERITY_CONFIG[severity]?.color
                    }}>
                        <AlertTriangle size={22} />
                    </div>

                    <div className="alert-meta">
                        <div className="alert-app-info">
                            {alert.app_name?.includes('chrome') ? <Globe size={14} /> : <Smartphone size={14} />}
                            <span>{alert.app_name?.split('.').pop() || 'Aplikace'}</span>
                        </div>
                        <span className="alert-timestamp">{formatTimestamp(alert.timestamp)}</span>
                    </div>

                    <button
                        className="alert-delete-btn"
                        onClick={(e) => onDelete(alert.id, e)}
                        title="Smazat záznam"
                    >
                        <Trash2 size={16} />
                    </button>
                </div>

                <div className="alert-body">
                    <div className="alert-keyword-row">
                        <span className="alert-label">Detekováno:</span>
                        <span className="alert-keyword-badge">"{alert.keyword}"</span>
                    </div>

                    {detectedText && (
                        <div className="alert-detected-text-container">
                            <p className={`alert-detected-text ${!isExpanded && shouldTruncate ? 'truncated' : ''}`}>
                                "{isExpanded || !shouldTruncate ? detectedText : detectedText.slice(0, 150) + '...'}"
                            </p>
                            {shouldTruncate && (
                                <button
                                    className="expand-text-btn"
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        onToggleExpand(alert.id)
                                    }}
                                >
                                    {isExpanded ? 'Skrýt' : 'Zobrazit vše'}
                                </button>
                            )}
                        </div>
                    )}
                </div>

                {alert.screenshot_url && (
                    <button
                        className="shield-proof-btn"
                        onClick={(e) => {
                            e.stopPropagation()
                            onViewScreenshot(alert.screenshot_url)
                        }}
                    >
                        <Eye size={16} />
                        <span>Zobrazit důkaz</span>
                    </button>
                )}
            </div>
        </div>
    )
}

export default AlertCard
