import React, { memo } from 'react'
import { Monitor, Smartphone, Grid } from 'lucide-react'

const DeviceFilter = memo(({ filter, onChange, counts }) => {
    return (
        <div className="device-filter">
            <button
                className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
                onClick={() => onChange('all')}
            >
                <Grid size={14} style={{ marginRight: '6px' }} />
                Všechna ({counts.total})
            </button>
            {counts.pc > 0 && (
                <button
                    className={`filter-btn ${filter === 'pc' ? 'active' : ''}`}
                    onClick={() => onChange('pc')}
                >
                    <Monitor size={14} style={{ marginRight: '6px' }} />
                    Počítače ({counts.pc})
                </button>
            )}
            {counts.mobile > 0 && (
                <button
                    className={`filter-btn ${filter === 'phone' ? 'active' : ''}`}
                    onClick={() => onChange('phone')}
                >
                    <Smartphone size={14} style={{ marginRight: '6px' }} />
                    Mobily ({counts.mobile})
                </button>
            )}
        </div>
    )
})

DeviceFilter.displayName = 'DeviceFilter'
export default DeviceFilter
