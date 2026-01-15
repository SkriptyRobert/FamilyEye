import React, { useState, useEffect, useMemo } from 'react'
import api from '../services/api'
import {
    Shield, AlertTriangle, Eye, Plus, Trash2, X, Globe, Smartphone,
    ChevronDown, ChevronRight, Users, Pill, Swords, Settings, Filter
} from 'lucide-react'
import { formatTimestamp } from '../utils/formatting'
import './SmartShield.css'

// Category configuration with colors and icons
const CATEGORIES = {
    bullying: {
        label: 'Šikana',
        icon: Users,
        color: '#f97316', // Orange
        bgColor: 'rgba(249, 115, 22, 0.1)',
        borderColor: 'rgba(249, 115, 22, 0.3)'
    },
    drugs: {
        label: 'Drogy',
        icon: Pill,
        color: '#ef4444',
        bgColor: 'rgba(239, 68, 68, 0.1)',
        borderColor: 'rgba(239, 68, 68, 0.3)'
    },
    violence: {
        label: 'Násilí',
        icon: Swords,
        color: '#a855f7', // Purple
        bgColor: 'rgba(168, 85, 247, 0.1)',
        borderColor: 'rgba(168, 85, 247, 0.3)'
    },
    custom: {
        label: 'Vlastní',
        icon: Settings,
        color: '#06b6d4', // Cyan
        bgColor: 'rgba(6, 182, 212, 0.1)',
        borderColor: 'rgba(6, 182, 212, 0.3)'
    }
}

const SEVERITY_CONFIG = {
    critical: { color: '#ef4444', label: 'Kritické' },
    high: { color: '#f97316', label: 'Vysoké' },
    medium: { color: '#eab308', label: 'Střední' },
    low: { color: '#22c55e', label: 'Nízké' }
}

const SmartShield = ({ device }) => {
    const [activeTab, setActiveTab] = useState('alerts')
    const [alerts, setAlerts] = useState([])
    const [keywords, setKeywords] = useState([])
    const [loading, setLoading] = useState(true)
    const [viewingScreenshot, setViewingScreenshot] = useState(null)
    const [expandedAlerts, setExpandedAlerts] = useState(new Set())
    const [filterCategory, setFilterCategory] = useState('all')

    // Keyword form states
    const [newKeyword, setNewKeyword] = useState('')
    const [newKeywordCategory, setNewKeywordCategory] = useState('custom') // Renamed from newCategory
    const [expandedCategories, setExpandedCategories] = useState(new Set())

    useEffect(() => {
        // Always fetch keywords as they are needed for filtering categories in alerts tab
        fetchKeywords()
        if (activeTab === 'alerts') fetchAlerts()
    }, [activeTab, device.id])

    const fetchAlerts = async () => {
        setLoading(true)
        try {
            const res = await api.get(`/api/shield/alerts/${device.id}`)
            setAlerts(res.data)
        } catch (err) {
            console.error("Failed to fetch alerts", err)
        } finally {
            setLoading(false)
        }
    }

    const fetchKeywords = async () => {
        setLoading(true)
        try {
            const res = await api.get(`/api/shield/keywords/${device.id}`)
            setKeywords(res.data)
        } catch (err) {
            console.error("Failed to fetch keywords", err)
        } finally {
            setLoading(false)
        }
    }

    const handleAddKeyword = async (e, categoryOverride = null) => {
        e.preventDefault()
        const category = categoryOverride || newKeywordCategory // Use newKeywordCategory
        if (!newKeyword.trim()) return

        try {
            await api.post('/api/shield/keywords', {
                device_id: device.id,
                keyword: newKeyword.trim(),
                category: category,
                severity: 'high'
            })
            setNewKeyword('')
            fetchKeywords()
        } catch (err) {
            alert("Chyba při přidávání slova")
        }
    }

    const handleDeleteKeyword = async (id) => {
        if (!confirm("Opravdu smazat toto klíčové slovo?")) return
        try {
            await api.delete(`/api/shield/keywords/${id}`)
            fetchKeywords()
        } catch (err) {
            alert("Chyba při mazání")
        }
    }

    const toggleAlertExpand = (alertId) => {
        setExpandedAlerts(prev => {
            const next = new Set(prev)
            if (next.has(alertId)) {
                next.delete(alertId)
            } else {
                next.add(alertId)
            }
            return next
        })
    }

    const toggleCategoryExpand = (category) => {
        setExpandedCategories(prev => {
            const next = new Set(prev)
            if (next.has(category)) {
                next.delete(category)
            } else {
                next.add(category)
            }
            return next
        })
    }

    // --- Alert Management ---
    const [selectedAlerts, setSelectedAlerts] = useState(new Set())

    const toggleAlertSelection = (alertId) => {
        setSelectedAlerts(prev => {
            const next = new Set(prev)
            if (next.has(alertId)) {
                next.delete(alertId)
            } else {
                next.add(alertId)
            }
            return next
        })
    }

    const selectAllAlerts = () => {
        if (selectedAlerts.size === filteredAlerts.length) {
            setSelectedAlerts(new Set())
        } else {
            setSelectedAlerts(new Set(filteredAlerts.map(a => a.id)))
        }
    }

    const handleDeleteAlert = async (id, event) => {
        event?.stopPropagation()
        if (!confirm("Opravdu smazat tento alert?")) return

        try {
            await api.delete(`/api/shield/alerts/${id}`)
            setAlerts(prev => prev.filter(a => a.id !== id))
            setSelectedAlerts(prev => {
                const next = new Set(prev)
                next.delete(id)
                return next
            })
        } catch (err) {
            console.error(err)
            alert("Chyba při mazání")
        }
    }

    const handleBatchDelete = async () => {
        if (selectedAlerts.size === 0) return
        if (!confirm(`Opravdu smazat ${selectedAlerts.size} vybraných alertů?`)) return

        try {
            await api.post('/api/shield/alerts/batch-delete', {
                alert_ids: Array.from(selectedAlerts)
            })
            // Optimistic update
            setAlerts(prev => prev.filter(a => !selectedAlerts.has(a.id)))
            setSelectedAlerts(new Set())
        } catch (err) {
            console.error(err)
            alert("Chyba při hromadném mazání")
        }
    }

    // Group keywords by category
    const keywordsByCategory = useMemo(() => {
        const grouped = { bullying: [], drugs: [], violence: [], custom: [] }
        keywords.forEach(kw => {
            const cat = kw.category || 'custom'
            if (grouped[cat]) {
                grouped[cat].push(kw)
            } else {
                grouped.custom.push(kw)
            }
        })
        return grouped
    }, [keywords])

    // Filter alerts by category
    const filteredAlerts = useMemo(() => {
        if (filterCategory === 'all') return alerts
        // Match alerts by their associated keyword's category if available
        return alerts.filter(alert => {
            const matchingKeyword = keywords.find(k => k.keyword.toLowerCase() === alert.keyword?.toLowerCase())
            return matchingKeyword?.category === filterCategory
        })
    }, [alerts, filterCategory, keywords])

    const renderAlertCard = (alert) => {
        const severity = alert.severity || 'high'
        const isExpanded = expandedAlerts.has(alert.id)
        const detectedText = alert.detected_text || ''
        const shouldTruncate = detectedText.length > 150

        return (
            <div
                key={alert.id}
                className={`shield-alert-card ${severity} ${selectedAlerts.has(alert.id) ? 'selected' : ''}`}
                onClick={() => toggleAlertSelection(alert.id)}
            >
                {/* Selection Overlay/Checkbox */}
                <div className="alert-select-indicator">
                    <div className={`select-checkbox ${selectedAlerts.has(alert.id) ? 'checked' : ''}`}>
                        {selectedAlerts.has(alert.id) && <Plus size={10} style={{ transform: 'rotate(45deg)' }} />}
                    </div>
                </div>

                {/* Severity indicator stripe */}
                <div className="alert-severity-stripe" style={{ background: SEVERITY_CONFIG[severity]?.color || '#f97316' }} />

                <div className="alert-card-content">
                    <div className="alert-card-header">
                        <div className="alert-icon-box" style={{
                            background: `${SEVERITY_CONFIG[severity]?.color}20`,
                            color: SEVERITY_CONFIG[severity]?.color
                        }}>
                            <AlertTriangle size={22} />
                        </div>

                        <div className="alert-meta">
                            <div className="alert-app-info">
                                {alert.app_name?.includes('chrome') ? <Globe size={14} /> : <Smartphone size={14} />}
                                <span>{alert.app_name?.split('.').pop() || 'Aplikace'}</span>
                            </div>
                            <span className="alert-timestamp">{formatTimestamp(alert.timestamp)}</span>
                        </div>

                        <button
                            className="alert-delete-btn"
                            onClick={(e) => handleDeleteAlert(alert.id, e)}
                            title="Smazat záznam"
                        >
                            <Trash2 size={16} />
                        </button>
                    </div>

                    <div className="alert-body">
                        <div className="alert-keyword-row">
                            <span className="alert-label">Detekováno:</span>
                            <span className="alert-keyword-badge">"{alert.keyword}"</span>
                        </div>

                        {detectedText && (
                            <div className="alert-detected-text-container">
                                <p className={`alert-detected-text ${!isExpanded && shouldTruncate ? 'truncated' : ''}`}>
                                    "{isExpanded || !shouldTruncate ? detectedText : detectedText.slice(0, 150) + '...'}"
                                </p>
                                {shouldTruncate && (
                                    <button
                                        className="expand-text-btn"
                                        onClick={() => toggleAlertExpand(alert.id)}
                                    >
                                        {isExpanded ? 'Skrýt' : 'Zobrazit vše'}
                                    </button>
                                )}
                            </div>
                        )}
                    </div>

                    {alert.screenshot_url && (
                        <button
                            className="shield-proof-btn"
                            onClick={() => setViewingScreenshot(alert.screenshot_url)}
                        >
                            <Eye size={16} />
                            <span>Zobrazit důkaz</span>
                        </button>
                    )}
                </div>
            </div>
        )
    }

    const renderCategorySection = (categoryKey) => {
        const config = CATEGORIES[categoryKey]
        const CategoryIcon = config.icon
        const categoryKeywords = keywordsByCategory[categoryKey] || []
        const isExpanded = expandedCategories.has(categoryKey)

        return (
            <div key={categoryKey} className="category-section" style={{ '--category-color': config.color }}>
                <button
                    className="category-header"
                    onClick={() => toggleCategoryExpand(categoryKey)}
                    style={{ borderColor: config.borderColor }}
                >
                    <div className="category-header-left">
                        <div className="category-icon-box" style={{ background: config.bgColor, color: config.color }}>
                            <CategoryIcon size={18} />
                        </div>
                        <span className="category-label">{config.label}</span>
                        <span className="category-count" style={{ background: config.bgColor, color: config.color }}>
                            {categoryKeywords.length}
                        </span>
                    </div>
                    <div className={`category-chevron ${isExpanded ? 'expanded' : ''}`}>
                        <ChevronRight size={18} />
                    </div>
                </button>

                {isExpanded && (
                    <div className="category-content" style={{ borderColor: config.borderColor }}>
                        {categoryKeywords.length === 0 ? (
                            <div className="category-empty">
                                <CategoryIcon size={24} style={{ color: config.color, opacity: 0.5 }} />
                                <p>Žádná sledovaná slova v této kategorii</p>
                            </div>
                        ) : (
                            <div className="keyword-chips-grid">
                                {categoryKeywords.map(kw => (
                                    <div
                                        key={kw.id}
                                        className="keyword-chip-modern"
                                        style={{
                                            background: config.bgColor,
                                            borderColor: config.borderColor
                                        }}
                                    >
                                        <span className="chip-text">{kw.keyword}</span>
                                        <button
                                            className="chip-delete"
                                            onClick={() => handleDeleteKeyword(kw.id)}
                                            style={{ color: config.color }}
                                        >
                                            <X size={14} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        )
    }

    return (
        <div className="smart-shield-container">
            {/* Tab Navigation */}
            <div className="shield-header">
                <div className="shield-tabs">
                    <button
                        className={`shield-tab ${activeTab === 'alerts' ? 'active' : ''}`}
                        onClick={() => setActiveTab('alerts')}
                    >
                        <AlertTriangle size={16} />
                        Alerty
                    </button>
                    <button
                        className={`shield-tab ${activeTab === 'settings' ? 'active' : ''}`}
                        onClick={() => setActiveTab('settings')}
                    >
                        <Settings size={16} />
                        Nastavení slov
                    </button>
                </div>
            </div>

            <div className="shield-content">
                {loading ? (
                    <div className="shield-loading">
                        <div className="loading-spinner" />
                        <span>Načítání...</span>
                    </div>
                ) : activeTab === 'alerts' ? (
                    <div className="alerts-section">
                        {/* Bulk Actions & Filters */}
                        <div className="alerts-controls-row">
                            <div className="filter-chips-row">
                                <Filter size={16} className="filter-icon" />
                                <button
                                    className={`filter-chip ${filterCategory === 'all' ? 'active' : ''}`}
                                    onClick={() => setFilterCategory('all')}
                                >
                                    Vše
                                </button>
                                {Object.entries(CATEGORIES).map(([key, config]) => (
                                    <button
                                        key={key}
                                        className={`filter-chip ${filterCategory === key ? 'active' : ''}`}
                                        onClick={() => setFilterCategory(key)}
                                        style={{
                                            '--chip-color': config.color,
                                            '--chip-bg': config.bgColor
                                        }}
                                    >
                                        {config.label}
                                    </button>
                                ))}
                            </div>

                            <div className="bulk-actions">
                                <button
                                    className={`select-all-btn ${selectedAlerts.size === filteredAlerts.length && filteredAlerts.length > 0 ? 'active' : ''}`}
                                    onClick={selectAllAlerts}
                                    disabled={filteredAlerts.length === 0}
                                >
                                    {selectedAlerts.size === filteredAlerts.length && filteredAlerts.length > 0 ? 'Zrušit výběr' : 'Vybrat vše'}
                                </button>

                                {selectedAlerts.size > 0 && (
                                    <button
                                        className="bulk-delete-btn"
                                        onClick={handleBatchDelete}
                                    >
                                        <Trash2 size={16} />
                                        <span>Smazat ({selectedAlerts.size})</span>
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className="alerts-grid">
                            {filteredAlerts.length === 0 ? (
                                <div className="shield-empty-state">
                                    <div className="empty-icon-container">
                                        <Shield size={64} />
                                    </div>
                                    <h3>Vše v pořádku</h3>
                                    <p>Žádné bezpečnostní incidenty za posledních 24 hodin.</p>
                                </div>
                            ) : (
                                filteredAlerts.map(alert => renderAlertCard(alert))
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="keywords-section">
                        <div className="keywords-header">
                            <h3>Sledovaná klíčová slova</h3>
                            <p className="keywords-subtitle">
                                Slova jsou organizována podle kategorie.
                                <br />
                                <span className="keywords-info-highlight">Vlastní slova přidejte pomocí volby Rychlé přidání. Vyberte kategorii a zadejte monitorované slovo.</span>
                            </p>
                        </div>

                        {/* Global Add Section - Prioritized */}
                        <div className="global-add-section">
                            <h4>Rychlé přidání</h4>
                            <form className="global-add-form" onSubmit={(e) => handleAddKeyword(e, newKeywordCategory)}>
                                <input
                                    type="text"
                                    value={newKeyword}
                                    onChange={(e) => setNewKeyword(e.target.value)}
                                    placeholder="Např. drogy, sebevražda..."
                                    className="global-add-input"
                                />
                                <select
                                    value={newKeywordCategory}
                                    onChange={(e) => setNewKeywordCategory(e.target.value)}
                                    className="global-add-select"
                                >
                                    {Object.entries(CATEGORIES).map(([key, config]) => (
                                        <option key={key} value={key}>{config.label}</option>
                                    ))}
                                </select>
                                <button type="submit" className="global-add-btn">
                                    <Plus size={18} />
                                    Přidat
                                </button>
                            </form>
                        </div>

                        <div className="categories-grid">
                            {Object.keys(CATEGORIES).map(key => renderCategorySection(key))}
                        </div>
                    </div>
                )}
            </div>

            {/* Screenshot Modal */}
            {viewingScreenshot && (
                <div className="shield-modal-overlay" onClick={() => setViewingScreenshot(null)}>
                    <div className="shield-modal-content" onClick={e => e.stopPropagation()}>
                        <button className="shield-modal-close" onClick={() => setViewingScreenshot(null)}>
                            <X size={20} />
                        </button>
                        <img src={viewingScreenshot} alt="Evidence" />
                    </div>
                </div>
            )}
        </div>
    )
}

export default SmartShield
