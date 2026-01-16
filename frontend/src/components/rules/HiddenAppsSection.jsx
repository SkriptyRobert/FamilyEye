import React from 'react'
import { Eye, EyeOff } from 'lucide-react'

const HiddenAppsSection = ({ hiddenApps, onRestoreApp }) => {
    return (
        <div className="hidden-apps-section">
            <h3 className="section-title">
                <EyeOff size={20} style={{ marginRight: '8px' }} />
                Skryté aplikace (z přehledu)
            </h3>
            <p className="section-description">
                Zde jsou aplikace, které jste ručně skryli z hlavního přehledu pomocí ikony oka.
            </p>
            {hiddenApps.length === 0 ? (
                <p className="empty-small">Žádné aplikace nejsou skryté.</p>
            ) : (
                <div className="hidden-apps-list">
                    {hiddenApps.map((app, idx) => (
                        <div key={idx} className="hidden-app-item">
                            <span className="hidden-app-name">{app}</span>
                            <button
                                className="restore-button"
                                onClick={() => onRestoreApp(app)}
                                title="Znovu zobrazit v přehledu"
                            >
                                <Eye size={14} style={{ marginRight: '4px' }} />
                                Zobrazit
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}

export default HiddenAppsSection
