import React from 'react'
import { X, Plus, BarChart3 } from 'lucide-react'
import { DEFAULT_SUGGESTED_APPS } from './constants'

/**
 * Reusable app picker component with autocomplete.
 * Shows selected apps as chips and suggests apps from usage data.
 */
const AppPicker = ({
  selectedApps,
  onAddApp,
  onRemoveApp,
  inputValue,
  onInputChange,
  frequentApps = [],
  allApps = []
}) => {

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      onAddApp(inputValue)
    }
  }

  const handleSuggestedClick = (app) => {
    onAddApp(app.keyword)
  }

  const getSuggestedApps = () => {
    // If user is typing, show filtered matches from ALL apps
    if (inputValue.trim().length > 0) {
      const search = inputValue.toLowerCase()
      return allApps
        .filter(app =>
          app.display_name?.toLowerCase().includes(search) ||
          app.app_name?.toLowerCase().includes(search)
        )
        .slice(0, 15)
        .map(app => ({
          name: app.display_name || 'Neznámá aplikace',
          keyword: app.app_name || ''
        }))
    }

    // Default view: Show top usage apps + defaults
    const allAppsList = [...frequentApps]

    DEFAULT_SUGGESTED_APPS.forEach(defaultApp => {
      const exists = allAppsList.some(
        app => (app.keyword?.toLowerCase() || '') === (defaultApp.keyword?.toLowerCase() || '')
      )
      if (!exists) {
        allAppsList.push(defaultApp)
      }
    })

    return allAppsList.slice(0, 12)
  }

  const suggestedApps = getSuggestedApps()
  const isSearchMode = inputValue.trim().length > 0

  return (
    <div className="app-picker">
      {/* Selected Apps Chips */}
      {selectedApps.length > 0 && (
        <div className="selected-apps-chips">
          {selectedApps.map(app => (
            <span key={app} className="app-chip">
              {app}
              <X
                size={14}
                onClick={() => onRemoveApp(app)}
                style={{ cursor: 'pointer', marginLeft: '4px' }}
              />
            </span>
          ))}
        </div>
      )}

      <input
        type="text"
        value={inputValue}
        onChange={(e) => onInputChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={selectedApps.length > 0 ? "Přidat další aplikaci..." : "Název (např. Epic, Chrome, Minecraft)"}
        className="input"
      />

      <div className="suggested-apps" style={{ marginTop: '10px' }}>
        <small style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>
          {isSearchMode
            ? <><Plus size={12} style={{ marginRight: '4px' }} /> Nalezené aplikace:</>
            : frequentApps.length > 0
              ? <><BarChart3 size={12} style={{ marginRight: '4px' }} /> Nejpoužívanější aplikace:</>
              : 'Časté aplikace:'
          }
        </small>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
          {suggestedApps.map((app, idx) => (
            <button
              key={`${app.keyword}-${idx}`}
              type="button"
              className={`tag-button ${selectedApps.includes(app.keyword?.toLowerCase() || '') ? 'selected' : ''}`}
              onClick={() => handleSuggestedClick(app)}
              title={app.duration ? `Použito: ${Math.round(app.duration / 60)} min` : app.keyword}
              disabled={selectedApps.includes(app.keyword?.toLowerCase() || '')}
            >
              {app.name}
            </button>
          ))}
          {isSearchMode && suggestedApps.length === 0 && (
            <span style={{ fontSize: '0.85em', color: 'var(--text-tertiary)', fontStyle: 'italic' }}>
              Žádná aplikace nebyla nalezena. Můžete ji přidat tlačítkem Enter.
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default AppPicker
