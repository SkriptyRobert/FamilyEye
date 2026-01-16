import React, { useState, useEffect } from 'react'
import api from '../services/api'
import SmartShield from './SmartShield'
import './SmartShield.css'
import { Smartphone, AlertTriangle, Info } from 'lucide-react'
import DynamicIcon from './DynamicIcon'

const SmartShieldView = () => {
    const [devices, setDevices] = useState([])
    const [selectedDeviceId, setSelectedDeviceId] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const fetchDevices = async () => {
            try {
                const res = await api.get('/api/devices/')
                // Filter only Android devices ? Or all that support Shield?
                // Smart Shield is currently Android only.
                const androidDevices = res.data.filter(d => d.device_type === 'android')
                setDevices(androidDevices)

                if (androidDevices.length > 0) {
                    setSelectedDeviceId(androidDevices[0].id)
                }
            } catch (err) {
                console.error("Failed to fetch devices", err)
            } finally {
                setLoading(false)
            }
        }
        fetchDevices()
    }, [])

    const selectedDevice = devices.find(d => d.id === parseInt(selectedDeviceId))

    if (loading) return <div className="p-8 text-center text-gray-500">Načítání zařízení...</div>

    if (devices.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-full p-8 text-center">
                <Smartphone size={48} className="text-gray-300 mb-4" />
                <h2 className="text-xl font-semibold mb-2">Žádná podporovaná zařízení</h2>
                <p className="text-gray-500 max-w-md">
                    Smart Shield je momentálně dostupný pouze pro Android zařízení.
                    Prosím spárujte Android zařízení pro využití této funkce.
                </p>
            </div>
        )
    }

    return (
        <div className="smart-shield-view h-full flex flex-col">
            {/* Header / Selector */}
            <div className="shield-view-header">
                <div>
                    <h1 className="shield-view-title">
                        <div className="shield-icon-container">
                            <span className="shield-icon">🛡️</span>
                            <div className="shield-icon-pulse"></div>
                        </div>
                        Smart Shield
                        <span className="shield-beta-badge">Beta</span>
                        <div className="shield-info-wrapper">
                            <Info size={16} className="shield-info-icon" />
                            <div className="shield-info-tooltip">
                                <p>
                                    Využívá pokročilý heuristický algoritmus a NLP modely pro detekci kontextuálního nebezpečí v reálném čase.
                                </p>
                            </div>
                        </div>
                    </h1>
                    <p className="shield-subtitle">Pokročilá detekce obsahu a prevence • <span>Chraňte své dítě před hrozbami dříve než nastanou</span></p>
                    <p className="shield-description-text">
                        Nástroj monitoruje aktivitu při procházení webu, kliknutí na odkazy a detekuje klíčová slova v komunikačních aplikacích.
                    </p>
                </div>

                <div className="device-selector-wrapper">
                    <select
                        value={selectedDeviceId || ''}
                        onChange={(e) => setSelectedDeviceId(parseInt(e.target.value))}
                        className="device-select"
                    >
                        {devices.map(device => (
                            <option key={device.id} value={device.id}>
                                {device.name}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Content */}
            <div className="view-content flex-1 p-6 overflow-y-auto bg-[var(--bg-primary)]">
                {selectedDevice ? (
                    <SmartShield device={selectedDevice} />
                ) : (
                    <div className="text-center p-12 text-gray-500">Vyberte zařízení</div>
                )}
            </div>
        </div>
    )
}

export default SmartShieldView
