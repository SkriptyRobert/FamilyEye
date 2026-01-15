import React, { useState, useEffect } from 'react'
import api from '../services/api'
import SmartShield from './SmartShield'
import { Smartphone, AlertTriangle } from 'lucide-react'
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
            <div className="view-header p-6 border-b border-[var(--border-color)] flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2">
                        🛡️ Smart Shield <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">Beta</span>
                    </h1>
                    <p className="text-gray-500 mt-1">Pokročilá detekce obsahu a prevence</p>
                </div>

                <div className="device-selector flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-600">Zařízení:</span>
                    <div className="relative">
                        <select
                            value={selectedDeviceId || ''}
                            onChange={(e) => setSelectedDeviceId(parseInt(e.target.value))}
                            className="appearance-none bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] py-2 pl-4 pr-10 rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--primary-color)] font-medium min-w-[200px]"
                        >
                            {devices.map(device => (
                                <option key={device.id} value={device.id}>
                                    {device.name}
                                </option>
                            ))}
                        </select>
                        <div className="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none text-gray-500">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                        </div>
                    </div>
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
