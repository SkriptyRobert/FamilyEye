import React, { useState, useCallback } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { getDataFreshness, getDeviceTypeInfo } from '../utils/formatting'

// Hooks
import useDevices from '../hooks/useDevices'
import useQuickActions from '../hooks/useQuickActions'

// Components
import DynamicIcon from './DynamicIcon'
import DeviceCard from './devices/DeviceCard'
import GlobalStats from './overview/GlobalStats'
import DeviceFilter from './overview/DeviceFilter'
import AllAppsModal from './modals/AllAppsModal'
import ScreenshotModal from './modals/ScreenshotModal'

import './StatusOverview.css'

const StatusOverview = () => {
    // 1. Fetch data using hook
    const {
        devices,
        summaries,
        rules,
        loading,
        error,
        lastFetch,
        refetch
    } = useDevices({ pollingInterval: 10000 })

    // 2. Setup actions hook
    const {
        pending: actionPending,
        feedback: actionFeedback,
        handleDeviceAction,
        handleAppAction,
        handleAdjustLimit,
        handleHideApp
    } = useQuickActions(refetch)

    // 3. Local UI state
    const [expandedDevice, setExpandedDevice] = useState(null)
    const [deviceFilter, setDeviceFilter] = useState('all') // all, pc, phone
    const [showAllAppsModal, setShowAllAppsModal] = useState(null) // deviceId or null
    const [showScreenshotModal, setShowScreenshotModal] = useState(null) // deviceId or null

    // 4. Derived state
    const freshness = getDataFreshness(lastFetch)

    // Filter devices
    const filteredDevices = devices.filter(d => {
        if (deviceFilter === 'all') return true

        const typeInfo = getDeviceTypeInfo(d.device_type)
        const isPc = typeInfo.label === 'Počítač' || typeInfo.label === 'Notebook'

        if (deviceFilter === 'pc') return isPc
        if (deviceFilter === 'phone') return !isPc
        return true
    })

    // Calculate counts for filter
    const pcCount = devices.filter(d => {
        const t = getDeviceTypeInfo(d.device_type)
        return t.label === 'Počítač' || t.label === 'Notebook'
    }).length

    const counts = {
        total: devices.length,
        pc: pcCount,
        mobile: devices.length - pcCount
    }

    // Handlers
    const toggleDevice = useCallback((deviceId) => {
        setExpandedDevice(prev => prev === deviceId ? null : deviceId)
    }, [])

    const onAppActionWrapper = useCallback((deviceId, appName, action) => {
        handleAppAction(deviceId, appName, action, rules, summaries)
    }, [handleAppAction, rules, summaries])

    const onAdjustLimitWrapper = useCallback((deviceId, appName, adjustment) => {
        handleAdjustLimit(deviceId, appName, adjustment, rules)
    }, [handleAdjustLimit, rules])


    // 5. Render Loading State
    if (loading && !devices.length) {
        return (
            <div className="status-overview">
                <div className="loading-state">
                    <div className="loading-spinner"></div>
                    <p>Načítání přehledu...</p>
                </div>
            </div>
        )
    }

    // 6. Render Error State
    if (error && !devices.length) {
        return (
            <div className="status-overview">
                <div className="error-state">
                    <span className="error-icon"><AlertTriangle size={24} /></span>
                    <p>{error}</p>
                    <button onClick={() => refetch(true)} className="retry-button">
                        Zkusit znovu
                    </button>
                    {lastFetch && <span className="error-timestamp">Poslední úspěšná aktualizace: {lastFetch.toLocaleTimeString()}</span>}
                </div>
            </div>
        )
    }

    // 7. Render Empty State
    if (!loading && devices.length === 0) {
        return (
            <div className="status-overview">
                <div className="empty-state">
                    <div className="empty-icon"><DynamicIcon name="smartphone" size={48} color="var(--text-muted)" /></div>
                    <h3>Žádná zařízení</h3>
                    <p>Přidejte první zařízení pomocí záložky "Přidat"</p>
                </div>
            </div>
        )
    }

    // 8. Render Main Content
    return (
        <div className="status-overview">
            {/* Data freshness indicator */}
            {!loading && (
                <div className={`freshness-indicator ${freshness.color}`} onClick={() => refetch(false)} title="Kliknutím aktualizovat" style={{ cursor: 'pointer' }}>
                    <span className="freshness-dot"></span>
                    <span className="freshness-text">{freshness.message}</span>
                    <RefreshCw size={12} style={{ marginLeft: 8, opacity: 0.5 }} />
                </div>
            )}

            {/* Global Stats */}
            <GlobalStats devices={devices} summaries={summaries} />

            {/* Device Filter */}
            <DeviceFilter
                filter={deviceFilter}
                onChange={setDeviceFilter}
                counts={counts}
            />

            {/* Device List */}
            <div className="device-list">
                {filteredDevices.map(device => (
                    <DeviceCard
                        key={device.id}
                        device={device}
                        summary={summaries[device.id]}
                        rules={rules[device.id] || []}
                        expanded={Number(expandedDevice) === Number(device.id)}
                        onToggle={() => toggleDevice(device.id)}
                        actionPending={actionPending}
                        actionFeedback={actionFeedback}
                        onDeviceAction={handleDeviceAction}
                        onAppAction={onAppActionWrapper}
                        onAdjustLimit={onAdjustLimitWrapper}
                        onShowAllApps={setShowAllAppsModal}
                        onShowScreenshot={setShowScreenshotModal}
                        onHideApp={(appName) => handleHideApp(appName, device.id)}
                    />
                ))}
            </div>

            {/* Modals */}
            {showAllAppsModal && (
                <AllAppsModal
                    deviceId={showAllAppsModal}
                    device={devices.find(d => d.id === showAllAppsModal)}
                    apps={summaries[showAllAppsModal]?.top_apps || []}
                    rules={rules[showAllAppsModal] || []}
                    lastFetch={lastFetch}
                    onClose={() => setShowAllAppsModal(null)}
                    actionPending={actionPending}
                    actionFeedback={actionFeedback}
                    onAppAction={onAppActionWrapper}
                />
            )}

            {showScreenshotModal && (
                <ScreenshotModal
                    deviceId={showScreenshotModal}
                    device={devices.find(d => d.id === showScreenshotModal)}
                    onClose={() => setShowScreenshotModal(null)}
                    actionPending={actionPending}
                    actionFeedback={actionFeedback}
                    onRequestScreenshot={() => handleDeviceAction(showScreenshotModal, 'screenshot')}
                />
            )}
        </div>
    )
}

export default StatusOverview
