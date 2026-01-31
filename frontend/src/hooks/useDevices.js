import { useState, useEffect, useCallback, useRef } from 'react'
import api from '../services/api'

/**
 * Custom hook for managing devices, their summaries, and rules
 * Extracted from StatusOverview.jsx for reusability
 * 
 * @param {Object} options - Hook options
 * @param {number} options.pollingInterval - Interval in ms for auto-refresh (default: 30000)
 * @param {boolean} options.autoFetch - Whether to fetch on mount (default: true)
 * @returns {Object} - { devices, summaries, rules, loading, error, lastFetch, refetch }
 */
export function useDevices(options = {}) {
    const { pollingInterval = 30000, autoFetch = true } = options

    const [devices, setDevices] = useState([])
    const [summaries, setSummaries] = useState({})
    const [rules, setRules] = useState({})
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [lastFetch, setLastFetch] = useState(null)

    const fetchIntervalRef = useRef(null)

    const fetchData = useCallback(async (showLoading = false) => {
        if (showLoading) setLoading(true)
        setError(null)

        try {
            const devicesResponse = await api.get('/api/devices/')
            const devicesList = devicesResponse.data
            setDevices(devicesList)

            // Fetch summaries and rules for all devices in parallel
            const summaryPromises = devicesList.map(device =>
                api.get(`/api/reports/device/${device.id}/summary`)
                    .then(res => ({ deviceId: device.id, data: res.data }))
                    .catch(() => ({ deviceId: device.id, data: null }))
            )

            const rulesPromises = devicesList.map(device =>
                api.get(`/api/rules/device/${device.id}`)
                    .then(res => ({ deviceId: device.id, data: res.data }))
                    .catch(() => ({ deviceId: device.id, data: [] }))
            )

            const [summaryResults, rulesResults] = await Promise.all([
                Promise.all(summaryPromises),
                Promise.all(rulesPromises)
            ])

            const summariesData = {}
            summaryResults.forEach(result => {
                if (result.data) summariesData[result.deviceId] = result.data
            })
            setSummaries(summariesData)

            const rulesData = {}
            rulesResults.forEach(result => {
                rulesData[result.deviceId] = result.data || []
            })
            setRules(rulesData)

            setLastFetch(new Date())
        } catch (err) {
            console.error('Error fetching devices:', err)
            setError('Nepodařilo se načíst data ze serveru')
        } finally {
            setLoading(false)
        }
    }, [])

    // Initial fetch and polling setup
    useEffect(() => {
        if (autoFetch) {
            fetchData(true)
        }

        if (pollingInterval > 0) {
            fetchIntervalRef.current = setInterval(() => fetchData(false), pollingInterval)
        }

        return () => {
            if (fetchIntervalRef.current) {
                clearInterval(fetchIntervalRef.current)
            }
        }
    }, [fetchData, autoFetch, pollingInterval])

    return {
        devices,
        summaries,
        rules,
        loading,
        error,
        lastFetch,
        refetch: fetchData
    }
}

export default useDevices
