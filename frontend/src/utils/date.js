/**
 * Date utility for handling backend timestamps (UTC) and converting them to local time.
 */

/**
 * Format a UTC date string to local locale string.
 * @param {string} utcDateString - ISO date string from backend (e.g., "2025-12-28T12:00:00" or "2025-12-28T12:00:00Z")
 * @returns {string} - Localized date string
 */
export const formatToLocalTime = (utcDateString) => {
    if (!utcDateString) return 'Nikdy'

    let dateStr = utcDateString;
    // Fix format: replace space with T if T is missing
    if (dateStr.includes(' ') && !dateStr.includes('T')) {
        dateStr = dateStr.replace(' ', 'T');
    }

    // Ensure the date string is treated as UTC
    // If it doesn't end with Z and doesn't have a timezone offset (+/-), append Z
    if (!dateStr.endsWith('Z') && !dateStr.includes('+') && !/(-\d{2}:\d{2})$/.test(dateStr)) {
        dateStr = `${dateStr}Z`;
    }

    const date = new Date(dateStr)
    return date.toLocaleString('cs-CZ')
}

/**
 * Get start of current day in Local time, but represented as ISO string
 * used for filtering logs if needed.
 */
export const getLocalStartOfDay = () => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    return now;
}
