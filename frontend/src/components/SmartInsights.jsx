import React, { useState } from 'react';
import {
    Brain, Lightbulb, Info, X,
    Scale, Search, Moon, Sunrise, XCircle
} from 'lucide-react'
import './SmartInsights.css';

const SmartInsights = ({ insights }) => {
    const [activeTab, setActiveTab] = useState('anomalies'); // 'anomalies', 'balance'
    const [showInfo, setShowInfo] = useState(false);

    console.log('SmartInsights Rendering, insights:', insights);

    if (!insights) return <div className="bento-card">Načítám analýzu...</div>;

    const formatDecimalHour = (decimal) => {
        if (decimal == null) return '?';
        const hours = Math.floor(decimal);
        const minutes = Math.round((decimal - hours) * 60);
        return `${hours}:${minutes.toString().padStart(2, '0')}`;
    };

    const renderAnomalies = () => {
        const { anomalies } = insights;
        const items = [];

        if (anomalies.is_night_owl) {
            items.push({ icon: <Moon size={16} />, text: `Noční sova: Aktivita po 22:00!`, type: 'error' });
        }
        if (anomalies.is_early_start) {
            const timeStr = formatDecimalHour(anomalies.avg_start_hour);
            items.push({ icon: <Sunrise size={16} />, text: `Dnes začal dříve (běžně kolem ${timeStr})`, type: 'warning' });
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


            {activeTab === 'anomalies' && renderAnomalies()}
            {activeTab === 'balance' && renderBalance()}

            <button className="insight-info-trigger" onClick={() => setShowInfo(!showInfo)}>
                {showInfo ? <><X size={14} style={{ marginRight: '4px' }} /> Zavřít info</> : <><Info size={14} style={{ marginRight: '4px' }} /> Jak to funguje?</>}
            </button>

            {showInfo && (
                <div className="insight-educational-panel">
                    <div className="edu-section">
                        <h4><Scale size={16} style={{ marginRight: '6px' }} /> Digitální Bilance</h4>
                        <p>Opírá se o doporučení <a href="https://www.who.int/news/item/24-04-2019-to-grow-up-healthy-children-need-to-sit-less-and-play-more" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-color)', textDecoration: 'underline' }}>WHO</a> a <a href="https://www.aap.org/en/patient-care/media-and-children/" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-color)', textDecoration: 'underline' }}>AAP</a>. Pro školní věk je 2h rekreačního času limit pro zachování zdravého spánku a psychické pohody.</p>
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
