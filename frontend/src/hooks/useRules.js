import { useState, useEffect, useCallback } from 'react'
import api from '../services/api'

/**
 * Custom hook for managing rules for a specific device
 * Extracted from RuleEditor.jsx for reusability
 * 
 * @param {string} deviceId - Device ID to fetch rules for
 * @returns {Object} - { rules, hiddenApps, frequentApps, loading, error, createRule, updateRule, deleteRule, restoreApp }
 */
export function useRules(deviceId) {
    const [rules, setRules] = useState([])
    const [hiddenApps, setHiddenApps] = useState([])
    const [frequentApps, setFrequentApps] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    // Fetch rules for device
    const fetchRules = useCallback(async () => {
        if (!deviceId) return

        try {
            const response = await api.get(`/api/rules/device/${deviceId}`)
            setRules(response.data)
        } catch (err) {
            console.error('Error fetching rules:', err)
            setError('Nepodařilo se načíst pravidla')
        }
    }, [deviceId])

    // Fetch hidden apps for device
    const fetchHiddenApps = useCallback(async () => {
        if (!deviceId) return

        try {
            const response = await api.get(`/api/devices/${deviceId}/hidden-apps`)
            setHiddenApps(response.data)
        } catch (err) {
            console.error('Error fetching hidden apps:', err)
        }
    }, [deviceId])

    // Fetch frequently used apps for suggestions
    const fetchFrequentApps = useCallback(async () => {
        if (!deviceId) return

        try {
            const response = await api.get(`/api/reports/device/${deviceId}/summary`)
            const summary = response.data

            if (summary?.top_apps) {
                const appNames = summary.top_apps
                    .slice(0, 10)
                    .map(app => ({
                        name: app.display_name || app.app_name,
                        keyword: app.app_name
                    }))
                setFrequentApps(appNames)
            }
        } catch (err) {
            console.error('Error fetching frequent apps:', err)
        }
    }, [deviceId])

    // Initial data load
    useEffect(() => {
        const loadData = async () => {
            setLoading(true)
            await Promise.all([
                fetchRules(),
                fetchHiddenApps(),
                fetchFrequentApps()
            ])
            setLoading(false)
        }

        if (deviceId) {
            loadData()
        }
    }, [deviceId, fetchRules, fetchHiddenApps, fetchFrequentApps])

    // Create a new rule
    const createRule = useCallback(async (ruleData) => {
        try {
            const response = await api.post('/api/rules/', {
                device_id: deviceId,
                ...ruleData
            })
            await fetchRules()
            return response.data
        } catch (err) {
            console.error('Error creating rule:', err)
            throw err
        }
    }, [deviceId, fetchRules])

    // Update an existing rule
    const updateRule = useCallback(async (ruleId, ruleData) => {
        try {
            const response = await api.put(`/api/rules/${ruleId}`, ruleData)
            await fetchRules()
            return response.data
        } catch (err) {
            console.error('Error updating rule:', err)
            throw err
        }
    }, [fetchRules])

    // Delete a rule
    const deleteRule = useCallback(async (ruleId) => {
        try {
            await api.delete(`/api/rules/${ruleId}`)
            await fetchRules()
        } catch (err) {
            console.error('Error deleting rule:', err)
            throw err
        }
    }, [fetchRules])

    // Restore a hidden app
    const restoreApp = useCallback(async (appName) => {
        try {
            await api.post(`/api/devices/${deviceId}/restore-app`, { app_name: appName })
            await fetchHiddenApps()
        } catch (err) {
            console.error('Error restoring app:', err)
            throw err
        }
    }, [deviceId, fetchHiddenApps])

    return {
        rules,
        hiddenApps,
        frequentApps,
        loading,
        error,
        createRule,
        updateRule,
        deleteRule,
        restoreApp,
        refetch: fetchRules
    }
}

export default useRules
