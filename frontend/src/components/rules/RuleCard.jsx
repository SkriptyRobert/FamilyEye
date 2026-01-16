import React from 'react'
import { Globe, Edit2 } from 'lucide-react'

const RULE_TYPE_LABELS = {
    'app_block': 'Blokace aplikace',
    'time_limit': 'Časový limit',
    'daily_limit': 'Denní limit',
    'website_block': 'Blokace webu',
    'web_block': 'Blokace webu',
    'schedule': 'Časový rozvrh'
}

const formatDays = (daysString) => {
    if (!daysString) return 'Každý den'
    const dayMap = { '0': 'Po', '1': 'Út', '2': 'St', '3': 'Čt', '4': 'Pá', '5': 'So', '6': 'Ne' }
    return daysString.split(',').map(d => dayMap[d.trim()] || d).join(', ')
}

const RuleCard = ({ rule, onEdit, onDelete }) => {
    return (
        <div className="rule-card">
            <div className="rule-card-header">
                <h4>
                    {rule.name ? (
                        <span style={{ fontWeight: '800', marginRight: '6px' }}>{rule.name}</span>
                    ) : null}
                    <span style={{ fontWeight: 'normal', opacity: 0.8, fontSize: '0.9em' }}>
                        ({RULE_TYPE_LABELS[rule.rule_type] || rule.rule_type})
                    </span>
                </h4>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <button
                        onClick={() => onEdit(rule)}
                        className="icon-button"
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)', padding: 4 }}
                        title="Upravit"
                    >
                        <Edit2 size={16} />
                    </button>
                    <span className={`status-badge ${rule.enabled ? 'active' : 'inactive'}`}>
                        {rule.enabled ? 'Aktivní' : 'Neaktivní'}
                    </span>
                </div>
            </div>
            <div className="rule-card-body">
                {rule.app_name && <p><strong>Aplikace:</strong> {rule.app_name}</p>}
                {rule.website_url && <p><strong>Web:</strong> {rule.website_url}</p>}
                {rule.time_limit && <p><strong>Limit:</strong> {rule.time_limit} minut</p>}
                {(rule.schedule_start_time && rule.schedule_end_time) && (
                    <p><strong>Rozvrh:</strong> {rule.schedule_start_time} - {rule.schedule_end_time}</p>
                )}
                {rule.schedule_days && <p><strong>Dny:</strong> {formatDays(rule.schedule_days)}</p>}
                {rule.block_network && <p className="network-blocked"><Globe size={14} style={{ marginRight: '4px' }} /> Síť blokována</p>}
            </div>
            <button
                onClick={() => onDelete(rule.id)}
                className="delete-button"
            >
                Smazat
            </button>
        </div>
    )
}

export default RuleCard
