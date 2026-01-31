package com.familyeye.agent.utils

import java.util.Calendar

/**
 * Centralized time utility functions for secure, consistent time handling.
 * 
 * This utility class provides all time-related operations used across the agent,
 * eliminating duplicate time parsing code and ensuring consistent behavior.
 */
object TimeUtils {

    /**
     * Parse a time string in "HH:mm" format to minutes since midnight.
     * 
     * @param timeStr Time string in format "HH:mm" (e.g., "14:30")
     * @return Minutes since midnight (0-1439), or -1 if parsing fails
     */
    fun parseMinutes(timeStr: String): Int {
        return try {
            val parts = timeStr.trim().split(":")
            if (parts.size != 2) return -1
            val hours = parts[0].toIntOrNull() ?: return -1
            val minutes = parts[1].toIntOrNull() ?: return -1
            if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) return -1
            hours * 60 + minutes
        } catch (e: Exception) {
            -1
        }
    }

    /**
     * Get the current time as minutes since midnight.
     * 
     * @return Current time as minutes since midnight (0-1439)
     */
    fun getCurrentMinutes(): Int {
        val now = Calendar.getInstance()
        return now.get(Calendar.HOUR_OF_DAY) * 60 + now.get(Calendar.MINUTE)
    }

    /**
     * Check if the current time falls within a specified time range.
     * Handles day-wrapping (e.g., 22:00 - 06:00 means overnight).
     * 
     * @param startStr Start time in "HH:mm" format
     * @param endStr End time in "HH:mm" format
     * @return true if current time is within the range, false otherwise
     */
    fun isCurrentTimeInRange(startStr: String, endStr: String): Boolean {
        val currentMinutes = getCurrentMinutes()
        val startMinutes = parseMinutes(startStr)
        val endMinutes = parseMinutes(endStr)

        // Invalid parsing
        if (startMinutes < 0 || endMinutes < 0) return false

        // Handle day wrapping (e.g., 22:00 - 06:00)
        return if (endMinutes < startMinutes) {
            // Overnight range: current either after start OR before end
            currentMinutes >= startMinutes || currentMinutes < endMinutes
        } else {
            // Same-day range: current must be between start and end
            currentMinutes in startMinutes until endMinutes
        }
    }

    /**
     * Check if a given time in minutes falls within a specified range.
     * Useful for testing with mock times.
     * 
     * @param checkMinutes The time to check (minutes since midnight)
     * @param startMinutes Range start (minutes since midnight)
     * @param endMinutes Range end (minutes since midnight)
     * @return true if checkMinutes is within the range
     */
    fun isTimeInRange(checkMinutes: Int, startMinutes: Int, endMinutes: Int): Boolean {
        if (checkMinutes < 0 || startMinutes < 0 || endMinutes < 0) return false

        return if (endMinutes < startMinutes) {
            // Overnight range
            checkMinutes >= startMinutes || checkMinutes < endMinutes
        } else {
            // Same-day range
            checkMinutes in startMinutes until endMinutes
        }
    }

    /**
     * Get the timestamp for the start of the current day (midnight).
     * 
     * @return Epoch milliseconds for 00:00:00.000 of the current day
     */
    fun getStartOfDay(): Long {
        val calendar = Calendar.getInstance()
        calendar.set(Calendar.HOUR_OF_DAY, 0)
        calendar.set(Calendar.MINUTE, 0)
        calendar.set(Calendar.SECOND, 0)
        calendar.set(Calendar.MILLISECOND, 0)
        return calendar.timeInMillis
    }

    /**
     * Get the timestamp for the start of a specific day.
     * 
     * @param timestamp Any timestamp within the desired day
     * @return Epoch milliseconds for 00:00:00.000 of that day
     */
    fun getStartOfDay(timestamp: Long): Long {
        val calendar = Calendar.getInstance()
        calendar.timeInMillis = timestamp
        calendar.set(Calendar.HOUR_OF_DAY, 0)
        calendar.set(Calendar.MINUTE, 0)
        calendar.set(Calendar.SECOND, 0)
        calendar.set(Calendar.MILLISECOND, 0)
        return calendar.timeInMillis
    }

    /**
     * Get the current day of week as index (0 = Monday, 6 = Sunday).
     * This matches the format used in schedule rules.
     * 
     * @return Day index (0-6, Monday to Sunday)
     */
    fun getCurrentDayOfWeek(): Int {
        val calendar = Calendar.getInstance()
        // Calendar.DAY_OF_WEEK: Sunday=1, Monday=2, ..., Saturday=7
        // We need: Monday=0, Tuesday=1, ..., Sunday=6
        return (calendar.get(Calendar.DAY_OF_WEEK) + 5) % 7
    }

    /**
     * Format milliseconds duration as human-readable time.
     * 
     * @param milliseconds Duration in milliseconds
     * @return Formatted string like "2h 30m" or "45s"
     */
    fun formatDuration(milliseconds: Long): String {
        val totalSeconds = milliseconds / 1000
        val hours = totalSeconds / 3600
        val minutes = (totalSeconds % 3600) / 60
        val seconds = totalSeconds % 60

        return when {
            hours > 0 -> "${hours}h ${minutes}m"
            minutes > 0 -> "${minutes}m ${seconds}s"
            else -> "${seconds}s"
        }
    }

    /**
     * Format seconds duration as human-readable time.
     * 
     * @param seconds Duration in seconds
     * @return Formatted string like "2h 30m" or "45s"
     */
    fun formatDurationSeconds(seconds: Int): String {
        return formatDuration(seconds * 1000L)
    }
}
