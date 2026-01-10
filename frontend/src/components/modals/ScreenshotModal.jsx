import React from 'react'
import { Camera, X } from 'lucide-react'
import './ScreenshotModal.css'

/**
 * Modal for viewing device screenshots
 * Extracted from StatusOverview.jsx
 * 
 * @param {Object} props
 * @param {Object} props.device - Device object with last_screenshot
 * @param {Function} props.onClose - Handler to close modal
 */
const ScreenshotModal = ({ device, onClose }) => {
    if (!device) return null

    return (
        <div className="screenshot-modal-overlay" onClick={onClose}>
            <div className="screenshot-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <div>
                        <h3><Camera size={20} /> Poslední snímek obrazovky</h3>
                        <span className="modal-device-name">{device?.name}</span>
                    </div>
                    <button className="modal-close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <div className="screenshot-viewer">
                    {device?.last_screenshot ? (
                        <img
                            src={device.last_screenshot}
                            alt="Snímek obrazovky"
                            className="full-screenshot"
                        />
                    ) : (
                        <div className="no-screenshot">Žádný snímek k dispozici</div>
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

export default ScreenshotModal
