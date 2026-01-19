import React, { useState, useEffect } from 'react'
import { Camera, X, Loader } from 'lucide-react'
import api from '../../services/api'
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
    const [imageUrl, setImageUrl] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (!device?.last_screenshot) return

        let mounted = true
        const screenshotPath = device.last_screenshot

        // Check if it's a base64 data URI (legacy format)
        if (screenshotPath.startsWith('data:image/')) {
            setImageUrl(screenshotPath)
            return
        }

        const fetchImage = async () => {
            setLoading(true)
            setError(null)
            try {
                // If it's a relative path like "screenshots/xxx/file.jpg", prepend /api/files/
                // If it's already a full URL, use as-is
                let fetchUrl = screenshotPath
                if (!screenshotPath.startsWith('http') && !screenshotPath.startsWith('/api/')) {
                    fetchUrl = `/api/files/${screenshotPath}`
                } else if (screenshotPath.startsWith('http')) {
                    // Full URL from backend - extract path part if needed
                    // e.g., http://...../api/files/screenshots/xxx/file.jpg
                    const pathMatch = screenshotPath.match(/\/api\/files\/(.+)$/)
                    if (pathMatch) {
                        fetchUrl = `/api/files/${pathMatch[1]}`
                    }
                }

                const response = await api.get(fetchUrl, {
                    responseType: 'blob'
                })

                if (mounted) {
                    const url = URL.createObjectURL(response.data)
                    setImageUrl(url)
                }
            } catch (err) {
                console.error("Failed to load screenshot", err)
                if (mounted) setError("Nepodařilo se načíst snímek (Auth error?)")
            } finally {
                if (mounted) setLoading(false)
            }
        }

        fetchImage()

        return () => {
            mounted = false
            if (imageUrl && !imageUrl.startsWith('data:')) URL.revokeObjectURL(imageUrl)
        }
    }, [device?.last_screenshot])

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
                    {loading ? (
                        <div className="loading-screenshot">
                            <Loader className="spin" size={32} />
                            <span>Načítání zabezpečeného snímku...</span>
                        </div>
                    ) : error ? (
                        <div className="error-screenshot">
                            <X size={32} color="red" />
                            <span>{error}</span>
                        </div>
                    ) : imageUrl ? (
                        <img
                            src={imageUrl}
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
