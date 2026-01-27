import React from 'react'
import { Monitor, Shield } from 'lucide-react'
import DayPicker from '../DayPicker'

/**
 * Schedule configuration form component.
 * Used for setting up time-based restrictions.
 */
const ScheduleForm = ({
  scheduleTarget,
  onScheduleTargetChange,
  startTime,
  endTime,
  selectedDays,
  onStartTimeChange,
  onEndTimeChange,
  onDaysChange
}) => {
  return (
    <div className="schedule-form">
      <label>Rozvrh platí pro:</label>
      <div className="schedule-target-selector">
        <label className={`radio-option ${scheduleTarget === 'device' ? 'selected' : ''}`}>
          <input
            type="radio"
            name="scheduleTarget"
            value="device"
            checked={scheduleTarget === 'device'}
            onChange={(e) => onScheduleTargetChange(e.target.value)}
          />
          <Monitor size={16} />
          <span>Celé zařízení</span>
        </label>
        <label className={`radio-option ${scheduleTarget === 'apps' ? 'selected' : ''}`}>
          <input
            type="radio"
            name="scheduleTarget"
            value="apps"
            checked={scheduleTarget === 'apps'}
            onChange={(e) => onScheduleTargetChange(e.target.value)}
          />
          <Shield size={16} />
          <span>Vybrané aplikace</span>
        </label>
      </div>

      <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
        <div style={{ flex: 1 }}>
          <label>Od</label>
          <input
            type="time"
            value={startTime}
            onChange={(e) => onStartTimeChange(e.target.value)}
            className="input"
          />
        </div>
        <div style={{ flex: 1 }}>
          <label>Do</label>
          <input
            type="time"
            value={endTime}
            onChange={(e) => onEndTimeChange(e.target.value)}
            className="input"
          />
        </div>
      </div>

      <label style={{ marginTop: '10px' }}>Dny v týdnu</label>
      <DayPicker
        selectedDays={selectedDays}
        onChange={onDaysChange}
      />
    </div>
  )
}

export default ScheduleForm
