/**
 * Formatting utilities for user-friendly display
 * All functions are designed to output "parent-friendly" text without technical jargon
 */

/**
 * Format seconds to human-readable duration
 * @param {number} seconds - Duration in seconds
 * @param {boolean} short - Use short format (1h 30m vs 1 hodina 30 minut)
 * @returns {string} - Human readable duration
 */
export const formatDuration = (seconds, short = false) => {
    if (!seconds || seconds <= 0) return short ? '0m' : '0 minut'

    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)

    if (hours === 0) {
        if (mins === 0) return short ? '<1m' : 'méně než minuta'
        return short ? `${mins}m` : `${mins} ${mins === 1 ? 'minuta' : mins < 5 ? 'minuty' : 'minut'}`
    }

    if (short) {
        return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
    }

    const hoursText = `${hours} ${hours === 1 ? 'hodina' : hours < 5 ? 'hodiny' : 'hodin'}`
    if (mins === 0) return hoursText
    const minsText = `${mins} ${mins === 1 ? 'minuta' : mins < 5 ? 'minuty' : 'minut'}`
    return `${hoursText} ${minsText}`
}

/**
 * Format a timestamp to relative time (e.g., "před 2 minutami")
 * @param {string|Date} timestamp - The timestamp to format
 * @returns {string} - Relative time string
 */
export const formatRelativeTime = (timestamp) => {
    if (!timestamp) return 'nikdy'

    let date = timestamp instanceof Date ? timestamp : parseTimestamp(timestamp)
    if (!date || isNaN(date.getTime())) return 'neznámý čas'

    const now = new Date()
    const diffMs = now - date
    const diffSeconds = Math.floor(diffMs / 1000)
    const diffMinutes = Math.floor(diffSeconds / 60)
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)

    // Future dates
    if (diffMs < 0) {
        const futureMins = Math.abs(Math.floor(diffMs / 60000))
        if (futureMins < 60) return `za ${futureMins} min`
        const futureHours = Math.floor(futureMins / 60)
        return `za ${futureHours} h`
    }

    if (diffSeconds < 30) return 'právě teď'
    if (diffSeconds < 60) return 'před chvílí'
    if (diffMinutes === 1) return 'před minutou'
    if (diffMinutes < 5) return `před ${diffMinutes} minutami`
    if (diffMinutes < 60) return `před ${diffMinutes} min`
    if (diffHours === 1) return 'před hodinou'
    if (diffHours < 24) return `před ${diffHours} h`
    if (diffDays === 1) return 'včera'
    if (diffDays < 7) return `před ${diffDays} dny`

    return date.toLocaleDateString('cs-CZ', { day: 'numeric', month: 'short' })
}

/**
 * Parse timestamp string to Date object, handling various formats
 * @param {string} timestamp - Timestamp string from backend
 * @returns {Date|null} - Parsed Date object or null
 */
export const parseTimestamp = (timestamp) => {
    if (!timestamp) return null

    let dateStr = timestamp

    // Fix format: replace space with T if T is missing
    if (dateStr.includes(' ') && !dateStr.includes('T')) {
        dateStr = dateStr.replace(' ', 'T')
    }

    // Ensure the date string is treated as UTC if no timezone specified
    if (!dateStr.endsWith('Z') && !dateStr.includes('+') && !/-\d{2}:\d{2}$/.test(dateStr)) {
        dateStr = `${dateStr}Z`
    }

    return new Date(dateStr)
}

/**
 * Format timestamp to user-friendly date/time
 * @param {string} timestamp - Timestamp from backend
 * @param {string} format - 'full', 'date', 'time', 'datetime'
 * @returns {string} - Formatted string
 */
export const formatTimestamp = (timestamp, format = 'full') => {
    if (!timestamp) return 'nikdy'

    const date = parseTimestamp(timestamp)
    if (!date || isNaN(date.getTime())) return 'neznámý čas'

    const today = new Date()
    const isToday = date.toDateString() === today.toDateString()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    const isYesterday = date.toDateString() === yesterday.toDateString()

    const time = date.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' })

    switch (format) {
        case 'time':
            return time
        case 'date':
            if (isToday) return 'dnes'
            if (isYesterday) return 'včera'
            return date.toLocaleDateString('cs-CZ', { day: 'numeric', month: 'short' })
        case 'datetime':
            if (isToday) return `dnes ${time}`
            if (isYesterday) return `včera ${time}`
            return date.toLocaleDateString('cs-CZ', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
        case 'full':
        default:
            if (isToday) return `dnes v ${time}`
            if (isYesterday) return `včera v ${time}`
            return date.toLocaleDateString('cs-CZ', {
                day: 'numeric',
                month: 'long',
                hour: '2-digit',
                minute: '2-digit'
            })
    }
}

/**
 * Get device state in human-friendly format
 * @param {object} device - Device object
 * @param {object} summary - Device summary data
 * @returns {object} - State info { status, label, color, icon, description }
 */
export const getDeviceState = (device, summary = null) => {
    if (!device) {
        return { status: 'unknown', label: 'Neznámý', color: 'gray', iconName: 'help-circle', description: 'Stav zařízení nelze určit' }
    }

    // Check if device has lock rule active
    const hasLockRule = device.has_lock_rule || false
    const hasNetworkBlock = device.has_network_block || false

    if (!device.is_online) {
        return {
            status: 'offline',
            label: 'Nepřipojeno',
            color: 'red',
            iconName: 'wifi-off',
            description: device.last_seen
                ? `Poslední spojení ${formatRelativeTime(device.last_seen)}`
                : 'Zařízení se dosud nepřipojilo'
        }
    }

    if (hasLockRule) {
        return {
            status: 'locked',
            label: 'Zamčeno',
            color: 'orange',
            iconName: 'lock',
            description: 'Zařízení je zamčené rodičem'
        }
    }

    if (hasNetworkBlock) {
        return {
            status: 'internet_paused',
            label: 'Internet vypnut',
            color: 'amber',
            iconName: 'globe',
            description: 'Internetový přístup je pozastaven'
        }
    }

    return {
        status: 'online',
        label: 'Aktivní',
        color: 'green',
        iconName: 'check-circle',
        description: `Monitorování běží, zařízení se hlásí`
    }
}

/**
 * Calculate usage percentage with context
 * @param {number} usedSeconds - Time used in seconds
 * @param {number} limitMinutes - Limit in minutes (optional)
 * @returns {object} - { percentage, status, label }
 */
export const getUsageStatus = (usedSeconds, limitMinutes = null) => {
    if (limitMinutes === null || limitMinutes === 0) {
        // No limit set
        return {
            percentage: 0,
            status: 'unlimited',
            label: 'Bez limitu',
            color: 'blue'
        }
    }

    const limitSeconds = limitMinutes * 60
    const percentage = Math.min(100, Math.round((usedSeconds / limitSeconds) * 100))

    if (percentage >= 100) {
        return {
            percentage: 100,
            status: 'exceeded',
            label: 'Limit překročen',
            color: 'red'
        }
    }

    if (percentage >= 80) {
        return {
            percentage,
            status: 'warning',
            label: 'Blízko limitu',
            color: 'amber'
        }
    }

    if (percentage >= 50) {
        return {
            percentage,
            status: 'moderate',
            label: 'Střední využití',
            color: 'yellow'
        }
    }

    return {
        percentage,
        status: 'ok',
        label: 'V pořádku',
        color: 'green'
    }
}

/**
 * Format "monitoring since" message
 * @param {string} pairedAt - Device pairing timestamp
 * @returns {string} - Human friendly message
 */
export const formatMonitoringSince = (pairedAt) => {
    if (!pairedAt) return 'Monitorování neaktivní'

    const date = parseTimestamp(pairedAt)
    if (!date || isNaN(date.getTime())) return 'Monitorování aktivní'

    const now = new Date()
    const diffMs = now - date
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays === 0) {
        return `Monitorování od dnes ${date.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' })}`
    }

    if (diffDays === 1) {
        return `Monitorování od včera ${date.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' })}`
    }

    if (diffDays < 7) {
        return `Monitorování ${diffDays} dny`
    }

    if (diffDays < 30) {
        const weeks = Math.floor(diffDays / 7)
        return `Monitorování ${weeks} ${weeks === 1 ? 'týden' : weeks < 5 ? 'týdny' : 'týdnů'}`
    }

    return `Monitorování od ${date.toLocaleDateString('cs-CZ', { day: 'numeric', month: 'long', year: 'numeric' })}`
}

/**
 * Get data freshness info
 * @param {Date} lastFetch - When data was last fetched
 * @returns {object} - { isFresh, message, color }
 */
export const getDataFreshness = (lastFetch) => {
    if (!lastFetch) {
        return { isFresh: false, message: 'Data se načítají...', color: 'gray' }
    }

    const now = new Date()
    const diffSeconds = Math.floor((now - lastFetch) / 1000)

    if (diffSeconds < 60) {
        return { isFresh: true, message: 'Aktuální data', color: 'green' }
    }

    if (diffSeconds < 120) {
        return { isFresh: true, message: 'Data před minutou', color: 'green' }
    }

    if (diffSeconds < 300) {
        return { isFresh: true, message: `Data před ${Math.floor(diffSeconds / 60)} min`, color: 'yellow' }
    }

    return { isFresh: false, message: 'Data mohou být zastaralá', color: 'orange' }
}

/**
 * Map technical app name to friendly name
 * @param {string} appName - Technical app name
 * @param {object} config - App configuration object (optional)
 * @returns {string|null} - Friendly name or null if should be hidden
 */
export const mapAppName = (appName, config = null) => {
    if (!appName) return null

    // config.friendlyNames is an object: { "technicallower": "Friendly Name" }
    // config can be null if not loaded yet
    const friendlyNames = config?.friendlyNames || {}

    const lowerName = appName.toLowerCase().replace('.exe', '')

    // Check direct mapping
    if (friendlyNames.hasOwnProperty(lowerName)) {
        return friendlyNames[lowerName]
    }

    // Check with .exe
    if (friendlyNames.hasOwnProperty(appName.toLowerCase())) {
        return friendlyNames[appName.toLowerCase()]
    }

    // Cleanup common patterns (fallback)
    let friendlyName = appName
        .replace('.exe', '')
        .replace(/([a-z])([A-Z])/g, '$1 $2') // camelCase to spaces
        .replace(/_/g, ' ')
        .replace(/-/g, ' ')

    // Capitalize first letter
    friendlyName = friendlyName.charAt(0).toUpperCase() + friendlyName.slice(1)

    return friendlyName
}

/**
 * Filter out system apps from app list
 * Also filters apps that user has manually blacklisted via UI
 * @param {Array} apps - List of apps
 * @param {object} config - App configuration object
 * @returns {Array} - Filtered list without system apps
 */
export const filterSystemApps = (apps, config = null) => {
    if (!apps) return []

    // Import user blacklist (lazy load)
    let userBlacklist = []
    try {
        const stored = localStorage.getItem('familyeye_user_blacklist')
        userBlacklist = stored ? JSON.parse(stored) : []
    } catch (e) {
        // Ignore parse errors
    }

    const blacklistPatterns = config?.blacklistPatterns || []
    const whitelist = config?.whitelist ? Object.values(config.whitelist).flat().map(w => w.toLowerCase()) : []

    return apps.filter(app => {
        const appName = (app.app_name || app.name || '').toLowerCase().trim()
        const lowerName = appName.replace('.exe', '')

        // Check user blacklist first (manually hidden by 'eye' icon)
        const normalizedBlacklist = userBlacklist.map(n => n.toLowerCase())
        if (normalizedBlacklist.includes(appName) || normalizedBlacklist.includes(lowerName)) {
            return false
        }

        // Check WHITELIST first - these apps are ALWAYS shown
        for (const whitelisted of whitelist) {
            if (lowerName.includes(whitelisted)) return true
        }

        // Check blacklist patterns from config (only if not whitelisted)
        if (blacklistPatterns.length > 0) {
            for (const pattern of blacklistPatterns) {
                if (lowerName.includes(pattern.toLowerCase())) return false
            }
        }

        return true
    }).map(app => ({
        ...app,
        display_name: app.display_name || mapAppName(app.app_name || app.name, config) || app.app_name
    }))
}

/**
 * Get appropriate icon for an app based on its name
 * @param {string} appName - App name
 * @param {object} config - App configuration object
 * @returns {string} - Emoji icon
 */
export const getAppIcon = (appName, config = null) => {
    if (!appName) return 'smartphone'
    if (!config || !config.iconMapping || !config.whitelist) return 'smartphone'

    const lowerName = appName.toLowerCase().replace('.exe', '')

    // Check whitelist categories for icon mapping
    for (const [category, apps] of Object.entries(config.whitelist)) {
        if (apps.some(app => lowerName.includes(app.toLowerCase()))) {
            return config.iconMapping[category] || 'smartphone'
        }
    }

    return 'smartphone'
}

/**
 * Advanced app filtering for parent-friendly display
 * - Filters out system processes by blacklist patterns
 * - Filters out apps with < 60 seconds usage (noise)
 * - Cleans up app names (removes .exe, formats nicely)
 * - Adds icons based on app category
 * 
 * @param {Array} apps - Raw app list from API
 * @param {Object} options - Filtering options (includes config)
 * @returns {Array} - Filtered and formatted app list
 */
export const filterAppsForDisplay = (apps, options = {}) => {
    if (!apps) return []

    const { minDurationSeconds = 60, limit = 10, config = null } = options

    // Backend already filters "trackable" apps.
    // We only need to filter by duration and noise.

    return apps
        // Filter by minimum duration (remove noise)
        .filter(app => (app.duration_seconds || app.duration || 0) >= minDurationSeconds)
        // Map to display format - PREFER BACKEND METADATA
        .map(app => {
            const rawName = app.app_name || app.name || ''

            // Use backend provided metadata if available
            const displayName = app.friendly_name || mapAppName(rawName, config) || rawName
            const icon = app.icon_type || getAppIcon(rawName, config)
            const category = app.category || null

            return {
                ...app,
                display_name: displayName,
                icon: icon,
                category: category
            }
        })
        .sort((a, b) => (b.duration_seconds || b.duration || 0) - (a.duration_seconds || a.duration || 0))
        .slice(0, limit)
}

/**
 * Clean up app name for display
 * @param {string} name - Raw app name
 * @returns {string} - Cleaned name
 */
const cleanAppName = (name) => {
    if (!name) return 'Unknown'

    return name
        .replace(/\.exe$/i, '')           // Remove .exe
        .replace(/([a-z])([A-Z])/g, '$1 $2') // camelCase to spaces
        .replace(/[_-]/g, ' ')            // Underscores/dashes to spaces
        .replace(/\s+/g, ' ')             // Multiple spaces to single
        .trim()
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ')
}

/**
 * Get device type icon and label
 * @param {string} deviceType - Device type from backend
 * @returns {object} - { icon, label }
 */
export const getDeviceTypeInfo = (deviceType) => {
    const type = (deviceType || '').toLowerCase()

    if (type.includes('phone') || type.includes('android') || type.includes('ios') || type.includes('mobile')) {
        return { iconName: 'smartphone', label: 'Telefon' }
    }

    if (type.includes('tablet') || type.includes('ipad')) {
        return { iconName: 'smartphone', label: 'Tablet' }
    }

    if (type.includes('laptop') || type.includes('notebook')) {
        return { iconName: 'monitor', label: 'Notebook' }
    }

    // Default to desktop/PC
    return { iconName: 'monitor', label: 'Počítač' }
}

/**
 * Calculate limit status with percentage and color
 * @param {number} usedSeconds - Time used in seconds
 * @param {number} limitMinutes - Limit in minutes
 * @returns {object} - { percentage, overMinutes, color, status, label }
 */
export const getLimitStatus = (usedSeconds, limitMinutes) => {
    if (!limitMinutes || limitMinutes <= 0) {
        return {
            percentage: 0,
            overMinutes: 0,
            color: 'gray',
            status: 'unlimited',
            label: 'Bez limitu',
            hasLimit: false
        }
    }

    const usedMinutes = Math.floor(usedSeconds / 60)
    const percentage = Math.round((usedSeconds / (limitMinutes * 60)) * 100)
    const overMinutes = Math.max(0, usedMinutes - limitMinutes)

    let color = 'green'
    let status = 'ok'
    let label = 'V pořádku'

    // Barevné rozsahy: zelená < 65%, oranžová 65-84%, červená >= 85%
    // Status "exceeded" pouze při skutečném dosažení 100%!
    if (percentage >= 100) {
        color = 'red'
        status = 'exceeded'
        label = overMinutes > 0 ? `Překročeno o ${overMinutes} min` : 'Limit dosažen'
    } else if (percentage >= 85) {
        color = 'red'
        status = 'critical'
        label = 'Téměř vyčerpán'
    } else if (percentage >= 65) {
        color = 'orange'
        status = 'warning'
        label = 'Blízko limitu'
    } else {
        color = 'green'
        status = 'ok'
        label = 'V pořádku'
    }

    return {
        percentage: Math.min(100, percentage),
        actualPercentage: percentage,
        overMinutes,
        color,
        status,
        label,
        hasLimit: true,
        usedMinutes,
        limitMinutes
    }
}

/**
 * Format limit display text
 * @param {number} usedSeconds - Time used
 * @param {number} limitMinutes - Limit in minutes
 * @returns {string} - "25 / 60 min" format
 */
export const formatLimitText = (usedSeconds, limitMinutes) => {
    const usedMins = Math.floor(usedSeconds / 60)
    // Cap displayed value at limit for professional appearance
    const displayMins = Math.min(usedMins, limitMinutes)
    return `${displayMins} / ${limitMinutes} min`
}

// ============================================
// NOTE: CONFIG-BASED FILTERING MOVED TO BACKEND
// The appConfigLoader.js and related functions have been removed.
// All filtering is now handled by backend/app/services/app_filter.py
// Frontend just displays what backend sends.
// ============================================
