import React from 'react'
import { ChevronRight, X } from 'lucide-react'

const CATEGORIES = {
    bullying: {
        label: 'Šikana',
        color: '#f97316',
        bgColor: 'rgba(249, 115, 22, 0.1)',
        borderColor: 'rgba(249, 115, 22, 0.3)'
    },
    drugs: {
        label: 'Drogy',
        color: '#ef4444',
        bgColor: 'rgba(239, 68, 68, 0.1)',
        borderColor: 'rgba(239, 68, 68, 0.3)'
    },
    violence: {
        label: 'Násilí',
        color: '#a855f7',
        bgColor: 'rgba(168, 85, 247, 0.1)',
        borderColor: 'rgba(168, 85, 247, 0.3)'
    },
    custom: {
        label: 'Vlastní',
        color: '#06b6d4',
        bgColor: 'rgba(6, 182, 212, 0.1)',
        borderColor: 'rgba(6, 182, 212, 0.3)'
    }
}

const CategorySection = ({
    categoryKey,
    keywords,
    isExpanded,
    onToggle,
    onDeleteKeyword
}) => {
    const config = CATEGORIES[categoryKey]
    if (!config) return null

    const CategoryIcon = require('lucide-react')[
        categoryKey === 'bullying' ? 'Users' :
            categoryKey === 'drugs' ? 'Pill' :
                categoryKey === 'violence' ? 'Swords' : 'Settings'
    ]

    return (
        <div className="category-section" style={{ '--category-color': config.color }}>
            <button
                className="category-header"
                onClick={onToggle}
                style={{ borderColor: config.borderColor }}
            >
                <div className="category-header-left">
                    <div className="category-icon-box" style={{ background: config.bgColor, color: config.color }}>
                        <CategoryIcon size={18} />
                    </div>
                    <span className="category-label">{config.label}</span>
                    <span className="category-count" style={{ background: config.bgColor, color: config.color }}>
                        {keywords.length}
                    </span>
                </div>
                <div className={`category-chevron ${isExpanded ? 'expanded' : ''}`}>
                    <ChevronRight size={18} />
                </div>
            </button>

            {isExpanded && (
                <div className="category-content" style={{ borderColor: config.borderColor }}>
                    {keywords.length === 0 ? (
                        <div className="category-empty">
                            <CategoryIcon size={24} style={{ color: config.color, opacity: 0.5 }} />
                            <p>Žádná sledovaná slova v této kategorii</p>
                        </div>
                    ) : (
                        <div className="keyword-chips-grid">
                            {keywords.map(kw => (
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
                                        onClick={() => onDeleteKeyword(kw.id)}
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

export { CATEGORIES }
export default CategorySection
