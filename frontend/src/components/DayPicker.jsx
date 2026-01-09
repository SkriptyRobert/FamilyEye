import React, { useState, useEffect } from 'react'
import './DayPicker.css'

/**
 * Visual day picker component for schedule selection.
 * Replaces technical "0-6" text input with user-friendly toggle buttons.
 * 
 * @param {string} selectedDays - Comma-separated day indices (e.g., "0,1,2,3,4")
 * @param {function} onChange - Callback when selection changes, receives new string
 */
const DayPicker = ({ selectedDays = '', onChange }) => {
    // Day configuration (Monday = 0, Sunday = 6)
    const days = [
        { index: 0, short: 'Po', full: 'Pondělí' },
        { index: 1, short: 'Út', full: 'Úterý' },
        { index: 2, short: 'St', full: 'Středa' },
        { index: 3, short: 'Čt', full: 'Čtvrtek' },
        { index: 4, short: 'Pá', full: 'Pátek' },
        { index: 5, short: 'So', full: 'Sobota' },
        { index: 6, short: 'Ne', full: 'Neděle' }
    ]

    // Quick preset configurations
    const presets = [
        { label: 'Pracovní dny', days: [0, 1, 2, 3, 4] },
        { label: 'Víkend', days: [5, 6] },
        { label: 'Celý týden', days: [0, 1, 2, 3, 4, 5, 6] }
    ]

    // Parse selected days string to Set
    const parseSelectedDays = (daysString) => {
        if (!daysString || daysString.trim() === '') return new Set()

        const daySet = new Set()
        const parts = daysString.split(',')

        for (const part of parts) {
            const trimmed = part.trim()
            // Handle range format (e.g., "0-6")
            if (trimmed.includes('-')) {
                const [start, end] = trimmed.split('-').map(Number)
                if (!isNaN(start) && !isNaN(end)) {
                    for (let i = start; i <= end; i++) {
                        if (i >= 0 && i <= 6) daySet.add(i)
                    }
                }
            } else {
                const num = parseInt(trimmed, 10)
                if (!isNaN(num) && num >= 0 && num <= 6) {
                    daySet.add(num)
                }
            }
        }

        return daySet
    }

    // Convert Set to sorted output string
    const formatSelectedDays = (daySet) => {
        return Array.from(daySet).sort((a, b) => a - b).join(',')
    }

    const [selected, setSelected] = useState(() => parseSelectedDays(selectedDays))

    // Sync with external value changes
    useEffect(() => {
        setSelected(parseSelectedDays(selectedDays))
    }, [selectedDays])

    // Toggle individual day
    const toggleDay = (index) => {
        const newSelected = new Set(selected)
        if (newSelected.has(index)) {
            newSelected.delete(index)
        } else {
            newSelected.add(index)
        }
        setSelected(newSelected)
        onChange?.(formatSelectedDays(newSelected))
    }

    // Apply preset
    const applyPreset = (presetDays) => {
        const newSelected = new Set(presetDays)
        setSelected(newSelected)
        onChange?.(formatSelectedDays(newSelected))
    }

    // Check if preset is currently active
    const isPresetActive = (presetDays) => {
        if (selected.size !== presetDays.length) return false
        return presetDays.every(d => selected.has(d))
    }

    return (
        <div className="day-picker">
            <div className="day-picker-buttons">
                {days.map((day) => (
                    <button
                        key={day.index}
                        type="button"
                        className={`day-toggle ${selected.has(day.index) ? 'selected' : ''}`}
                        onClick={() => toggleDay(day.index)}
                        title={day.full}
                        aria-pressed={selected.has(day.index)}
                    >
                        {day.short}
                    </button>
                ))}
            </div>

            <div className="day-presets">
                {presets.map((preset) => (
                    <button
                        key={preset.label}
                        type="button"
                        className={`day-preset-link ${isPresetActive(preset.days) ? 'active' : ''}`}
                        onClick={() => applyPreset(preset.days)}
                    >
                        {preset.label}
                    </button>
                ))}
            </div>
        </div>
    )
}

export default DayPicker
