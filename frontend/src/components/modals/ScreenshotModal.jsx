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
        const fetchImage = async () => {
            setLoading(true)
            setError(null)
            try {
                // If the URL is already absolute and points to our API, we need to fetch it with auth
                // But api.get adds baseURL. If last_screenshot is full URL, we need to handle it.
                // device.last_screenshot typically comes from backend as full URL (http://.../api/...)

                // We'll strip the base URL if needed or just use the full URL with axios
                // api.get logic: if url is absolute, axios might handle it, but our api instance has baseURL set.
                // Safer: Extract the path relative to baseURL or just use axios directly with headers.
                // Ideally, use our 'api' instance to get the interceptors (Auth header).

                // Hack: If URL starts with http, we can pass it directly. Axios usually handles absolute URLs by ignoring baseURL.

                const response = await api.get(device.last_screenshot, {
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
            if (imageUrl) URL.revokeObjectURL(imageUrl)
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
