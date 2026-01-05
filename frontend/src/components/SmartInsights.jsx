import React, { useState } from 'react';
import api from '../services/api'
import {
    Brain, Lightbulb, Info, X, Target,
    Scale, Search, Moon, Sunrise, XCircle
} from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import './SmartInsights.css';

const SmartInsights = ({ insights }) => {
    const [activeTab, setActiveTab] = useState('focus'); // 'focus', 'anomalies', 'balance'
    const [showInfo, setShowInfo] = useState(false);

    console.log('SmartInsights Rendering, insights:', insights);

    if (!insights) return <div className="bento-card">Načítám analýzu...</div>;

    const renderFocus = () => {
        const flowData = [
            { name: 'Flow', value: Math.max(1, insights.focus.flow_index) },
            { name: 'Other', value: 100 - Math.max(1, insights.focus.flow_index) }
        ];
        const COLORS = ['#a29bfe', 'rgba(255, 255, 255, 0.05)'];

        return (
            <div className="insight-content focus-mode">
                <div className="focus-layout">
                    <div className="focus-chart-container">
                        <ResponsiveContainer width="100%" height={120}>
                            <PieChart>
                                <Pie
                                    data={flowData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={35}
                                    outerRadius={50}
                                    paddingAngle={0}
                                    dataKey="value"
                                    startAngle={90}
                                    endAngle={-270}
                                    stroke="none"
                                >
                                    {flowData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                            </PieChart>
                        </ResponsiveContainer>
                        <div className="chart-center-label">
                            {Math.round(insights.focus.flow_index)}%
                        </div>
                    </div>
                    <div className="focus-details">
                        <div className="stat-box-small">
                            <span className="stat-value-small">{insights.focus.deep_work_minutes}m</span>
                            <span className="stat-label-small">Hluboká práce</span>
                        </div>
                        <div className="stat-box-small">
                            <span className="stat-value-small">{insights.focus.context_switches}x</span>
                            <span className="stat-label-small">Přepnutí</span>
                        </div>
                    </div>
                </div>
                <div className="stat-subtext-centered">
                    <strong>Flow Index (Průtok):</strong> Podíl sezení delších než 15 min. <br />
                    <small>Krátká odskočení (do 60s) pozornost nenarušují.</small>
                </div>
            </div>
        );
    };

    const renderAnomalies = () => {
        const { anomalies } = insights;
        const items = [];

        if (anomalies.is_night_owl) {
            items.push({ icon: <Moon size={16} />, text: `Noční sova: Aktivita po 22:00!`, type: 'error' });
        }
        if (anomalies.is_early_start) {
            items.push({ icon: <Sunrise size={16} />, text: `Dnes začal o hodně dříve (${anomalies.avg_start_hour}h obvykle)`, type: 'warning' });
        }
        if (anomalies.new_apps && anomalies.new_apps.length > 0) {
            items.push({ icon: <Info size={16} />, text: `Nové aplikace: ${anomalies.new_apps.join(', ')}`, type: 'info' });
        }
        if (anomalies.total_violations > 0) {
            items.push({ icon: <XCircle size={16} />, text: `Dnes ${anomalies.total_violations}x překročen limit!`, type: 'error' });
        }

        const isLearning = (insights.days_of_history || 0) < 3;

        return (
            <div className="insight-content anomaly-mode">
                {isLearning && (
                    <div className="learning-banner">
                        <span className="learning-icon"><Brain size={16} /></span>
                        <div className="learning-content">
                            <strong>Učím se návyky... ({insights.days_of_history || 0}/3 dny)</strong>
                            <p>Anomálie budou přesnější po týdnu používání.</p>
                        </div>
                    </div>
                )}
                {items.length === 0 && !isLearning ? (
                    <div className="no-anomalies">Dnes nezjištěny žádné výkyvy.</div>
                ) : (
                    <div className="anomaly-list">
                        {items.map((item, idx) => (
                            <div key={idx} className={`anomaly-item ${item.type || ''}`}>
                                <span className="anomaly-icon">{item.icon}</span>
                                <span className="anomaly-text">{item.text}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        );
    };

    const renderBalance = () => {
        const score = insights.balance.wellness_score;
        const color = score > 75 ? '#55efc4' : score > 40 ? '#fdcb6e' : '#ff7675';

        return (
            <div className="insight-content balance-mode">
                <div className="balance-content-refined">
                    <div className="gauge-container">
                        <div className="gauge-outer">
                            <div
                                className="gauge-inner"
                                style={{
                                    width: `${score}%`,
                                    background: color,
                                    boxShadow: `0 0 15px ${color}44`
                                }}
                            ></div>
                        </div>
                        <span className="gauge-score" style={{ color }}>{score}%</span>
                    </div>
                    <div className="balance-info">
                        <span className="wellness-label">Digitální Balance</span>
                        <div className={`intensity-badge-new ${insights.balance.usage_intensity.toLowerCase()}`}>
                            Zátěž: {insights.balance.usage_intensity === 'High' ? 'Vysoká' : insights.balance.usage_intensity === 'Moderate' ? 'Střední' : 'Nízká'}
                        </div>
                    </div>
                    <div className="balance-threshold-note">
                        Po 2h pokles skóre o 20 bodů/hod. Penalizace za noc a překročení limitů.
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="bento-card smart-insights-card">
            <div className="insights-header">
                <h3><Lightbulb size={20} style={{ marginRight: '8px', color: 'var(--accent-color)' }} /> Chytrý přehled</h3>
                <div className="insights-tabs">
                    <button
                        className={`insight-tab ${activeTab === 'focus' ? 'active' : ''}`}
                        onClick={() => setActiveTab('focus')}
                    >
                        Soustředění
                    </button>
                    <button
                        className={`insight-tab ${activeTab === 'anomalies' ? 'active' : ''}`}
                        onClick={() => setActiveTab('anomalies')}
                    >
                        Anomálie
                    </button>
                    <button
                        className={`insight-tab ${activeTab === 'balance' ? 'active' : ''}`}
                        onClick={() => setActiveTab('balance')}
                    >
                        Bilance
                    </button>
                </div>
            </div>

            {activeTab === 'focus' && renderFocus()}
            {activeTab === 'anomalies' && renderAnomalies()}
            {activeTab === 'balance' && renderBalance()}

            <button className="insight-info-trigger" onClick={() => setShowInfo(!showInfo)}>
                {showInfo ? <><X size={14} style={{ marginRight: '4px' }} /> Zavřít info</> : <><Info size={14} style={{ marginRight: '4px' }} /> Jak to funguje?</>}
            </button>

            {showInfo && (
                <div className="insight-educational-panel">
                    <div className="edu-section">
                        <h4><Target size={16} style={{ marginRight: '6px' }} /> Soustředění (Deep Work)</h4>
                        <p>Vychází ze studií <strong>Cala Newporta</strong>. Mozek potřebuje cca 15 minut na plné „ponoření“ do úkolu. Časté přepínání (Attention Residue) podle <strong>Sophie Leroy</strong> snižuje kognitivní výkon až o 20 %.</p>
                    </div>
                    <div className="edu-section">
                        <h4><Scale size={16} style={{ marginRight: '6px' }} /> Digitální Bilance</h4>
                        <p>Opírá se o doporučení <strong>WHO</strong> a <strong>AAP</strong>. Pro školní věk je 2h rekreačního času limit pro zachování zdravého spánku a psychické pohody.</p>
                    </div>
                    <div className="edu-section">
                        <h4><Search size={16} style={{ marginRight: '6px' }} /> Anomálie</h4>
                        <p>Systém využívá statistickou analýzu k detekci vybočení z běžných trendů (čas startu, nové aplikace, noční aktivita).</p>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SmartInsights;
