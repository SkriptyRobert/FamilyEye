import { useState, useCallback } from 'react'
import api from '../services/api'

/**
 * Custom hook for managing quick actions on devices
 * Handles action pending states, feedback, and API calls
 * Extracted from StatusOverview.jsx for reusability
 * 
 * @param {Function} onSuccess - Optional callback after successful action
 * @returns {Object} - { pending, feedback, handleDeviceAction, handleAppAction, handleAdjustLimit, clearFeedback }
 */
export function useQuickActions(onSuccess = null) {
    const [pending, setPending] = useState({})
    const [feedback, setFeedback] = useState({})

    const clearFeedback = useCallback((key) => {
        setFeedback(prev => ({ ...prev, [key]: null }))
    }, [])

    const setFeedbackWithTimeout = useCallback((key, data, timeout = 3000) => {
        setFeedback(prev => ({ ...prev, [key]: data }))
        setTimeout(() => clearFeedback(key), timeout)
    }, [clearFeedback])

    /**
     * Handle device-level quick actions (lock, unlock, pause-internet, etc.)
     */
    const handleDeviceAction = useCallback(async (deviceId, action) => {
        const actionKey = `${deviceId}-${action}`
        setPending(prev => ({ ...prev, [actionKey]: true }))
        setFeedback(prev => ({ ...prev, [actionKey]: { status: 'sending', message: 'Odesílám příkaz...' } }))

        try {
            let endpoint = ''
            let successMessage = ''

            switch (action) {
                case 'lock':
                    endpoint = `/api/devices/${deviceId}/lock`
                    successMessage = 'Zařízení zamčeno'
                    break
                case 'unlock':
                    endpoint = `/api/devices/${deviceId}/unlock`
                    successMessage = 'Zařízení odemčeno'
                    break
                case 'pause-internet':
                    endpoint = `/api/devices/${deviceId}/pause-internet?duration_minutes=60`
                    successMessage = 'Internet pozastaven'
                    break
                case 'resume-internet':
                    endpoint = `/api/devices/${deviceId}/resume-internet`
                    successMessage = 'Internet obnoven'
                    break
                case 'screenshot':
                    endpoint = `/api/devices/${deviceId}/request-screenshot`
                    successMessage = 'Požadavek na screenshot odeslán'
                    break
                default:
                    return
            }

            await api.post(endpoint)
            setFeedbackWithTimeout(actionKey, { status: 'success', message: successMessage })

            if (onSuccess) {
                setTimeout(() => onSuccess(), 500)
            }
        } catch (err) {
            setFeedbackWithTimeout(
                actionKey,
                { status: 'error', message: err.response?.data?.detail || 'Příkaz selhal' },
                5000
            )
        } finally {
            setPending(prev => ({ ...prev, [actionKey]: false }))
        }
    }, [onSuccess, setFeedbackWithTimeout])

    /**
     * Handle app-level quick actions (block, limit-30, limit-60, etc.)
     */
    const handleAppAction = useCallback(async (deviceId, appName, action, rules, summaries) => {
        const actionKey = `${deviceId}-app-${appName}-${action}`
        setPending(prev => ({ ...prev, [actionKey]: true }))

        const actionMessages = {
            'block': 'Blokuji aplikaci...',
            'limit-30': 'Nastavuji limit +30 min...',
            'limit-60': 'Nastavuji limit +60 min...',
            'limit-120': 'Nastavuji limit +2 hodiny...'
        }
        setFeedback(prev => ({ ...prev, [actionKey]: { status: 'sending', message: actionMessages[action] || 'Zpracovávám...' } }))

        try {
            let ruleData = {
                device_id: deviceId,
                app_name: appName,
                enabled: true
            }

            // Find existing rule first to avoid duplicates
            const deviceRules = rules[deviceId] || []
            const existingRule = deviceRules.find(r =>
                (r.rule_type === 'time_limit' || r.rule_type === 'app_time_limit' || r.rule_type === 'app_block') &&
                (r.app_name?.toLowerCase() === appName.toLowerCase() || r.target?.toLowerCase() === appName.toLowerCase())
            )

            if (existingRule) {
                // Update existing rule
                if (action === 'block') {
                    await api.put(`/api/rules/${existingRule.id}`, {
                        ...existingRule,
                        rule_type: 'app_block',
                        enabled: true
                    })
                    ruleData = { ...existingRule, rule_type: 'app_block' }
                } else {
                    const addMinutes = parseInt(action.split('-')[1]) || 60
                    const currentLimit = (existingRule.rule_type === 'app_block') ? 0 : (existingRule.time_limit || existingRule.limit_minutes || 0)
                    const newLimit = currentLimit + addMinutes

                    await api.put(`/api/rules/${existingRule.id}`, {
                        ...existingRule,
                        rule_type: 'time_limit',
                        time_limit: newLimit,
                        enabled: true
                    })
                    ruleData = { ...existingRule, rule_type: 'time_limit', time_limit: newLimit }
                }
            } else {
                // Create new rule
                if (action === 'block') {
                    ruleData.rule_type = 'app_block'
                } else {
                    const summary = summaries?.[deviceId]
                    const topApps = summary?.top_apps || []
                    const appUsage = topApps.find(a =>
                        a.app_name?.toLowerCase() === appName.toLowerCase() ||
                        a.display_name?.toLowerCase() === appName.toLowerCase()
                    )
                    const currentUsageMinutes = Math.ceil((appUsage?.duration_seconds || 0) / 60)
                    const addMinutes = parseInt(action.split('-')[1]) || 60
                    const totalLimitMinutes = currentUsageMinutes + addMinutes

                    ruleData.rule_type = 'time_limit'
                    ruleData.time_limit = totalLimitMinutes
                }

                await api.post('/api/rules/', ruleData)
            }

            const successMessages = {
                'block': `${appName} zablokována`,
                'limit-30': `+30 min pro ${appName} (celkem ${ruleData.time_limit}m)`,
                'limit-60': `+60 min pro ${appName} (celkem ${ruleData.time_limit}m)`,
                'limit-120': `+2h pro ${appName} (celkem ${ruleData.time_limit}m)`
            }
            setFeedbackWithTimeout(actionKey, { status: 'success', message: successMessages[action] || 'Hotovo' })

            if (onSuccess) {
                setTimeout(() => onSuccess(), 500)
            }
        } catch (err) {
            console.error('Error with app action:', err)
            setFeedbackWithTimeout(
                actionKey,
                { status: 'error', message: 'Chyba při nastavení pravidla' },
                5000
            )
        } finally {
            setPending(prev => ({ ...prev, [actionKey]: false }))
        }
    }, [onSuccess, setFeedbackWithTimeout])

    /**
     * Handle limit adjustment (add/subtract time)
     */
    const handleAdjustLimit = useCallback(async (deviceId, appName, adjustMinutes, rules) => {
        const actionKey = `${deviceId}-adjust-${appName}`
        setPending(prev => ({ ...prev, [actionKey]: true }))
        setFeedback(prev => ({ ...prev, [actionKey]: { status: 'sending', message: 'Upravuji limit...' } }))

        try {
            const deviceRules = rules[deviceId] || []
            const existingRule = deviceRules.find(r =>
                (r.rule_type === 'time_limit' || r.rule_type === 'app_time_limit') &&
                (r.app_name?.toLowerCase() === appName.toLowerCase() ||
                    r.target?.toLowerCase() === appName.toLowerCase())
            )

            if (existingRule) {
                const newLimit = Math.max(5, (existingRule.time_limit || existingRule.limit_minutes || 30) + adjustMinutes)
                await api.put(`/api/rules/${existingRule.id}`, {
                    ...existingRule,
                    time_limit: newLimit,
                    limit_minutes: newLimit
                })
                setFeedbackWithTimeout(actionKey, {
                    status: 'success',
                    message: `Limit ${adjustMinutes > 0 ? 'prodloužen' : 'zkrácen'} na ${newLimit} min`
                })
            } else {
                await api.post('/api/rules/', {
                    device_id: deviceId,
                    rule_type: 'time_limit',
                    app_name: appName,
                    time_limit: Math.max(5, 30 + adjustMinutes),
                    enabled: true
                })
                setFeedbackWithTimeout(actionKey, { status: 'success', message: 'Nový limit vytvořen' })
            }

            if (onSuccess) {
                setTimeout(() => onSuccess(), 500)
            }
        } catch (err) {
            console.error('Error adjusting limit:', err)
            setFeedbackWithTimeout(
                actionKey,
                { status: 'error', message: 'Chyba při úpravě limitu' },
                5000
            )
        } finally {
            setPending(prev => ({ ...prev, [actionKey]: false }))
        }
    }, [onSuccess, setFeedbackWithTimeout])

    return {
        pending,
        feedback,
        handleDeviceAction,
        handleAppAction,
        handleAdjustLimit,
        clearFeedback
    }
}

export default useQuickActions
