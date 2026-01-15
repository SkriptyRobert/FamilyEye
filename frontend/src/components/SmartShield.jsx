import React, { useState, useEffect } from 'react'
import api from '../services/api'
import {
    Shield, AlertTriangle, Eye, Settings, Plus, Trash2, Check, X
} from 'lucide-react'
import DynamicIcon from './DynamicIcon'
import { formatTimestamp } from '../utils/formatting'
import ScreenshotModal from './modals/ScreenshotModal' // Reuse if possible or create new logic
import './SmartShield.css'

const SmartShield = ({ device }) => {
    const [activeTab, setActiveTab] = useState('alerts') // alerts | settings
    const [alerts, setAlerts] = useState([])
    const [keywords, setKeywords] = useState([])
    const [loading, setLoading] = useState(true)
    const [viewingScreenshot, setViewingScreenshot] = useState(null)

    // New Keyword Form
    const [newKeyword, setNewKeyword] = useState('')
    const [newCategory, setNewCategory] = useState('custom')

    useEffect(() => {
        if (activeTab === 'alerts') fetchAlerts()
        if (activeTab === 'settings') fetchKeywords()
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

    const handleAddKeyword = async (e) => {
        e.preventDefault()
        if (!newKeyword.trim()) return

        try {
            await api.post('/api/shield/keywords', {
                device_id: device.id,
                keyword: newKeyword.trim(),
                category: newCategory,
                severity: 'high' // Default to high for custom
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

    return (
        <div className="smart-shield-container">
            {/* Header */}
            <div className="shield-header">
                <div className="shield-title">
                    <Shield size={24} className="text-primary" />
                    <h2>Smart Shield (Beta)</h2>
                </div>
                <div className="shield-tabs">
                    <button
                        className={`tab-btn ${activeTab === 'alerts' ? 'active' : ''}`}
                        onClick={() => setActiveTab('alerts')}
                    >
                        Alerty
                    </button>
                    <button
                        className={`tab-btn ${activeTab === 'settings' ? 'active' : ''}`}
                        onClick={() => setActiveTab('settings')}
                    >
                        Nastavení slov
                    </button>
                </div>
            </div>

            <div className="shield-content">
                {loading ? (
                    <div className="loading">Načítání...</div>
                ) : activeTab === 'alerts' ? (
                    <div className="alerts-list">
                        {alerts.length === 0 ? (
                            <div className="empty-state">
                                <Check size={48} className="text-success" />
                                <p>Žádné bezpečnostní incidenty. Vše vypadá v pořádku.</p>
                            </div>
                        ) : (
                            alerts.map(alert => (
                                <div key={alert.id} className={`alert-card severity-${alert.severity}`}>
                                    <div className="alert-icon">
                                        <AlertTriangle size={24} />
                                    </div>
                                    <div className="alert-details">
                                        <div className="alert-meta">
                                            <span className="alert-app">{alert.app_name}</span>
                                            <span className="alert-time">{formatTimestamp(alert.timestamp)}</span>
                                        </div>
                                        <h4 className="alert-keyword">
                                            Detekováno: <strong>"{alert.keyword}"</strong>
                                        </h4>
                                        {alert.detected_text && (
                                            <p className="alert-context">"...{alert.detected_text}..."</p>
                                        )}
                                    </div>
                                    {alert.screenshot_url && (
                                        <button
                                            className="view-screenshot-btn"
                                            onClick={() => setViewingScreenshot(alert.screenshot_url)}
                                        >
                                            <Eye size={16} /> Důkaz
                                        </button>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                ) : (
                    <div className="settings-panel">
                        <div className="add-keyword-card premium-card">
                            <h3>Přidat sledované slovo</h3>
                            <form onSubmit={handleAddKeyword} className="keyword-form">
                                <input
                                    type="text"
                                    placeholder="Např. drogy, sebevražda..."
                                    value={newKeyword}
                                    onChange={e => setNewKeyword(e.target.value)}
                                    className="input"
                                />
                                <select
                                    value={newCategory}
                                    onChange={e => setNewCategory(e.target.value)}
                                    className="input category-select"
                                >
                                    <option value="custom">Vlastní</option>
                                    <option value="drugs">Drogy</option>
                                    <option value="violence">Násilí</option>
                                    <option value="bullying">Šikana</option>
                                </select>
                                <button type="submit" className="button button-primary">Přidat</button>
                            </form>
                        </div>

                        <div className="keywords-list">
                            <h3>Aktivní slova</h3>
                            {keywords.map(kw => (
                                <div key={kw.id} className="keyword-item">
                                    <span className={`category-tag ${kw.category}`}>{kw.category}</span>
                                    <span className="keyword-text">{kw.keyword}</span>
                                    <button
                                        className="delete-btn"
                                        onClick={() => handleDeleteKeyword(kw.id)}
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Simplified Screenshot Modal for reuse */}
            {viewingScreenshot && (
                <div className="modal-overlay" onClick={() => setViewingScreenshot(null)}>
                    <div className="modal-content relative" onClick={e => e.stopPropagation()}>
                        <button className="close-btn" onClick={() => setViewingScreenshot(null)}><X /></button>
                        <img src={viewingScreenshot} alt="Evidence" style={{ maxWidth: '100%', maxHeight: '80vh' }} />
                    </div>
                </div>
            )}
        </div>
    )
}

export default SmartShield
