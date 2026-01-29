import React, { memo } from 'react'
import {
    getDeviceState,
    getDeviceTypeInfo,
    getLimitStatus,
    filterSystemApps
} from '../../utils/formatting'
import './DeviceCard.css'

// Platform specific components
import WindowsDeviceCard from './platforms/WindowsDeviceCard'
import AndroidDeviceCard from './platforms/AndroidDeviceCard'

/**
 * Device card dispatcher component
 * Decides which platform card to render based on device type
 */
const DeviceCard = memo((props) => {
    const { device, summary, rules = [] } = props

    // Core data preparation shared by both platforms
    const state = getDeviceState(device, summary)
    const typeInfo = getDeviceTypeInfo(device.device_type)

    // Use elapsed time for "Dnes aktivní" display
    const todayUsage = summary?.elapsed_today_seconds || summary?.today_usage_seconds || 0
    const topApps = filterSystemApps(summary?.top_apps || [], { deviceId: device?.id })

    // Get apps with limits - Shared logic
    const getAppsWithLimits = () => {
        const backendAppsWithLimits = summary?.apps_with_limits || []

        if (backendAppsWithLimits.length > 0) {
            return backendAppsWithLimits.map(app => {
                const usedSeconds = app.usage_seconds || 0
                const limitMinutes = app.limit_minutes || 0
                const limitStatus = getLimitStatus(usedSeconds, limitMinutes)

                return {
                    appName: app.app_name,
                    usedSeconds,
                    limitMinutes,
                    ...limitStatus
                }
            })
        }

        // Fallback: calculate from rules
        return rules
            .filter(rule =>
                (rule.rule_type === 'time_limit' || rule.rule_type === 'app_time_limit') &&
                (rule.enabled !== false && rule.is_active !== false) &&
                (rule.limit_minutes > 0 || rule.time_limit > 0)
            )
            .map(rule => {
                const ruleAppName = rule.target || rule.app_name || ''
                const limitMinutes = rule.limit_minutes || rule.time_limit || 0

                const appUsage = (summary?.top_apps || []).find(a => {
                    const ruleTargetLower = ruleAppName.toLowerCase()
                    const appNameLower = a.app_name?.toLowerCase() || ''
                    const displayNameLower = a.display_name?.toLowerCase() || ''

                    return appNameLower === ruleTargetLower ||
                        displayNameLower === ruleTargetLower ||
                        (ruleTargetLower.length >= 3 &&
                            (appNameLower.includes(ruleTargetLower) || displayNameLower.includes(ruleTargetLower)))
                })

                const usedSeconds = appUsage?.duration_seconds || 0
                const limitStatus = getLimitStatus(usedSeconds, limitMinutes)

                return {
                    appName: ruleAppName,
                    usedSeconds,
                    limitMinutes,
                    ...limitStatus
                }
            })
    }

    const appsWithLimits = getAppsWithLimits()

    // Pass all props + calculated data
    const componentProps = {
        ...props,
        typeInfo,
        state,
        todayUsage,
        topApps,
        appsWithLimits
    }

    // Dispatch based on standardized ID from formatting.js
    if (typeInfo.id === 'android') {
        return <AndroidDeviceCard {...componentProps} />
    }

    // Default to Windows
    return <WindowsDeviceCard {...componentProps} />
})

DeviceCard.displayName = 'DeviceCard'

export default DeviceCard
