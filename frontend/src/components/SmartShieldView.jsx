import React, { useState, useEffect } from 'react'
import api from '../services/api'
import SmartShield from './SmartShield'
import { ChevronDown, Smartphone, AlertTriangle, Info } from 'lucide-react'
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
                    <h1 className="text-2xl font-bold flex items-center gap-3">
                        <div className="relative">
                            <span className="text-3xl relative z-10 block">🛡️</span>
                            <div className="absolute inset-0 bg-blue-500/30 blur-lg rounded-full animate-pulse z-0"></div>
                        </div>
                        Smart Shield
                        <span className="text-xs bg-gradient-to-r from-indigo-500 to-purple-500 text-white px-3 py-1 rounded-full font-semibold shadow-lg shadow-indigo-500/20">Beta</span>
                        <div className="group relative ml-2">
                            <Info size={16} className="text-gray-500 cursor-help hover:text-indigo-400 transition-colors" />
                            <div className="absolute left-1/2 -translate-x-1/2 top-full mt-2 w-72 p-3 bg-slate-800 border border-slate-700 rounded-lg shadow-xl text-xs text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                                <p className="italic">
                                    Využívá pokročilý heuristický algoritmus a NLP modely pro detekci kontextuálního nebezpečí v reálném čase.
                                </p>
                            </div>
                        </div>
                    </h1>
                    <p className="text-gray-400 mt-2 text-sm">Pokročilá detekce obsahu a prevence • <span className="italic opacity-70">Chraňte své dítě před nevhodným obsahem</span></p>
                </div>

                <div className="device-selector-wrapper relative">
                    <select
                        value={selectedDeviceId || ''}
                        onChange={(e) => setSelectedDeviceId(parseInt(e.target.value))}
                        className="appearance-none bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] pl-4 pr-10 py-2.5 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500/50 hover:bg-slate-800 transition-all cursor-pointer min-w-[200px]"
                    >
                        {devices.map(device => (
                            <option key={device.id} value={device.id}>
                                {device.name}
                            </option>
                        ))}
                    </select>
                    <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
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
