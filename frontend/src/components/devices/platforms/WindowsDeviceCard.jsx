import React from 'react'
import {
    Unlock,
    Globe,
    Calendar,
    Settings,
    Clock,
    Smartphone,
    RefreshCw,
    XCircle,
    EyeOff,
    Check
} from 'lucide-react'
import DynamicIcon from '../../DynamicIcon'
import { LimitChip } from '../../limits'
import QuickActionsBar from '../QuickActionsBar'
import {
    formatDuration,
    formatRelativeTime,
    formatTimestamp,
    getDeviceState,
    getLimitStatus,
    filterSystemApps,
    formatLimitText
} from '../../../utils/formatting'

const WindowsDeviceCard = ({
    device,
    summary,
    rules = [],
    expanded,
    onToggle,
    actionPending,
    actionFeedback,
    onDeviceAction,
    onAppAction,
    onAdjustLimit,
    onShowAllApps,
    onShowScreenshot,
    onHideApp,
    typeInfo,
    todayUsage,
    topApps,
    appsWithLimits,
    state
}) => {
    return (
        <div
            className={`device-card ${state.status} ${expanded ? 'expanded' : ''}`}
            onClick={onToggle}
        >
            {/* Device header */}
            <div className="device-header">
                <div className="device-identity">
                    <span className="device-type-icon" title={typeInfo.label}>
                        <DynamicIcon name={typeInfo.iconName} size={24} />
                    </span>
                    <div className="device-name-group">
                        <h3 className="device-name">{device.name}</h3>
                        <span className={`device-status ${state.color}`}>
                            <span className="status-icon">
                                <DynamicIcon name={state.iconName} size={14} />
                            </span>
                            <span className="status-label">{state.label}</span>
                        </span>
                    </div>
                </div>
                <div className="device-meta">
                    <span className="last-seen">
                        {device.last_seen
                            ? formatRelativeTime(device.last_seen)
                            : 'nikdy nepřipojeno'
                        }
                    </span>
                </div>
            </div>

            {/* Today's usage */}
            <div className="usage-today">
                <div className="usage-primary">
                    <span className="usage-value">{formatDuration(todayUsage, true)}</span>
                    <span className="usage-label">dnes aktivní</span>
                </div>
            </div>

            {/* Compact limit chips */}
            {appsWithLimits.length > 0 && (
                <div className="limit-chips" onClick={e => e.stopPropagation()}>
                    {appsWithLimits.slice(0, 3).map((app, idx) => (
                        <LimitChip
                            key={idx}
                            appName={app.appName}
                            usedSeconds={app.usedSeconds}
                            limitMinutes={app.limitMinutes}
                            status={app.status}
                            color={app.color}
                        />
                    ))}
                    {appsWithLimits.length > 3 && (
                        <span className="limit-chips-more">
                            +{appsWithLimits.length - 3}
                        </span>
                    )}
                </div>
            )}

            <div onClick={e => e.stopPropagation()}>
                <QuickActionsBar
                    device={device}
                    actionPending={actionPending}
                    actionFeedback={actionFeedback}
                    onDeviceAction={onDeviceAction}
                    onShowScreenshot={onShowScreenshot}
                />
            </div>

            {/* Expanded content */}
            {expanded && (
                <div className="device-details" onClick={e => e.stopPropagation()}>
                    {/* Monitoring info */}
                    <div className="detail-section monitoring-info">
                        <div className="detail-item">
                            <span className="detail-icon"><Calendar size={18} /></span>
                            <div className="detail-content">
                                <span className="detail-label">Monitorování od</span>
                                <span className="detail-value">
                                    {summary?.paired_at
                                        ? formatTimestamp(summary.paired_at, 'full')
                                        : 'neznámý datum'
                                    }
                                </span>
                            </div>
                        </div>
                        <div className="detail-item">
                            <span className="detail-icon"><RefreshCw size={18} /></span>
                            <div className="detail-content">
                                <span className="detail-label">Poslední kontrola</span>
                                <span className="detail-value">
                                    {device.last_seen
                                        ? formatTimestamp(device.last_seen, 'full')
                                        : 'nikdy'
                                    }
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* App limits expanded */}
                    {appsWithLimits.length > 0 && (
                        <div className="detail-section limits-section-expanded">
                            <h4 className="section-title"><Clock size={16} /> Limity aplikací</h4>
                            {appsWithLimits.map((app, idx) => {
                                const adjustKey = `${device.id}-adjust-${app.appName}`
                                const isPending = actionPending[adjustKey]
                                const feedback = actionFeedback[adjustKey]

                                return (
                                    <div key={idx} className={`limit-item-expanded ${app.color}`}>
                                        <div className="limit-header">
                                            <span className="limit-app-name">{app.appName}</span>
                                            <span className={`limit-text ${app.color}`}>
                                                {formatLimitText(app.usedSeconds, app.limitMinutes)}
                                            </span>
                                        </div>
                                        <div className="limit-bar-container">
                                            <div
                                                className={`limit-bar ${app.color}`}
                                                style={{ width: `${Math.min(100, app.actualPercentage)}%` }}
                                            />
                                        </div>
                                        <div className="limit-quick-actions">
                                            <button
                                                className={`limit-action-btn subtract ${isPending ? 'pending' : ''}`}
                                                onClick={() => onAdjustLimit(device.id, app.appName, -15)}
                                                disabled={isPending}
                                            >
                                                -15m
                                            </button>
                                            <button
                                                className={`limit-action-btn add ${isPending ? 'pending' : ''}`}
                                                onClick={() => onAdjustLimit(device.id, app.appName, 15)}
                                                disabled={isPending}
                                            >
                                                +15m
                                            </button>
                                            <button
                                                className={`limit-action-btn add-more ${isPending ? 'pending' : ''}`}
                                                onClick={() => onAdjustLimit(device.id, app.appName, 30)}
                                                disabled={isPending}
                                            >
                                                +30m
                                            </button>
                                        </div>
                                        {feedback && (
                                            <div className={`limit-action-feedback ${feedback.status}`}>
                                                {feedback.message}
                                            </div>
                                        )}
                                    </div>
                                )
                            })}
                        </div>
                    )}

                    {/* Daily device limit */}
                    {summary?.daily_limit && (
                        <div className="detail-section limits-section-expanded">
                            <h4 className="section-title"><Calendar size={16} /> Denní limit zařízení</h4>
                            <div className={`limit-item-expanded ${summary.daily_limit.percentage_used >= 100 ? 'red' :
                                summary.daily_limit.percentage_used >= 65 ? 'orange' : 'green'
                                }`}>
                                <div className="limit-header">
                                    <span className="limit-app-name">Celkový čas dnes</span>
                                    <span className="limit-text">
                                        {formatDuration(summary.daily_limit.usage_seconds, true)} / {summary.daily_limit.limit_minutes} min
                                    </span>
                                </div>
                                <div className="limit-bar-container">
                                    <div
                                        className={`limit-bar ${summary.daily_limit.percentage_used >= 100 ? 'red' :
                                            summary.daily_limit.percentage_used >= 65 ? 'orange' : 'green'
                                            }`}
                                        style={{ width: `${Math.min(100, summary.daily_limit.percentage_used)}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Top apps */}
                    {topApps.length > 0 && (
                        <div className="detail-section apps-section">
                            <div className="section-header-row">
                                <h4 className="section-title">
                                    <Smartphone size={16} /> Top 5 používaných aplikací dnes
                                </h4>
                                <button className="show-all-apps-btn" onClick={() => onShowAllApps(device.id)}>
                                    <DynamicIcon name="clipboardList" size={14} /> Všechny ({topApps.length})
                                </button>
                            </div>
                            <div className="apps-list">
                                {topApps.slice(0, 5).map((app, index) => {
                                    const appName = app.app_name || app.display_name
                                    const hasRule = rules.some(r =>
                                        r.app_name?.toLowerCase() === appName?.toLowerCase()
                                    )
                                    const blockKey = `${device.id}-app-${appName}-block`
                                    const limit60Key = `${device.id}-app-${appName}-limit-60`
                                    const isPending = actionPending[blockKey] || actionPending[limit60Key]
                                    const feedback = actionFeedback[blockKey] || actionFeedback[limit60Key]

                                    return (
                                        <div key={index} className="app-item-with-actions">
                                            <div className="app-item-main">
                                                <div className="top-app-icon-group">
                                                    <div className="top-app-icon">
                                                        <DynamicIcon name={app.icon || app.icon_type} size={20} />
                                                    </div>
                                                    <div className="top-app-name-details">
                                                        <span className="top-app-name-internal">{app.display_name}</span>
                                                        {app.window_title && (
                                                            <span className="top-app-window-title" title={app.window_title}>
                                                                {app.window_title.length > 40 ? app.window_title.substring(0, 37) + '...' : app.window_title}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                                <span className="app-duration">
                                                    {formatDuration(app.duration_seconds, true)}
                                                </span>
                                            </div>

                                            {!hasRule && (
                                                <div className="app-quick-actions">
                                                    <button
                                                        className={`app-action-btn block ${isPending ? 'pending' : ''}`}
                                                        onClick={() => onAppAction(device.id, appName, 'block')}
                                                        disabled={isPending}
                                                        title="Zablokovat aplikaci"
                                                    >
                                                        <XCircle size={14} />
                                                    </button>
                                                    <button
                                                        className={`app-action-btn limit ${isPending ? 'pending' : ''}`}
                                                        onClick={() => onAppAction(device.id, appName, 'limit-30')}
                                                        disabled={isPending}
                                                        title="Limit 30 min"
                                                    >
                                                        30m
                                                    </button>
                                                    <button
                                                        className={`app-action-btn limit ${isPending ? 'pending' : ''}`}
                                                        onClick={() => onAppAction(device.id, appName, 'limit-60')}
                                                        disabled={isPending}
                                                        title="Limit 60 min"
                                                    >
                                                        1h
                                                    </button>
                                                    <button
                                                        className="app-action-btn hide"
                                                        onClick={() => onHideApp(appName)}
                                                        title="Skrýt z přehledu"
                                                    >
                                                        <EyeOff size={14} />
                                                    </button>
                                                </div>
                                            )}

                                            {hasRule && (
                                                <span className="app-has-rule-badge">
                                                    <Check size={10} /> Pravidlo
                                                </span>
                                            )}

                                            {feedback && (
                                                <div className={`app-action-feedback ${feedback.status}`}>
                                                    {feedback.message}
                                                </div>
                                            )}
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    )}

                    {/* Extended actions */}
                    <div className="detail-section actions-section">
                        <button
                            className={`action-btn-full unlock ${actionPending[`${device.id}-unlock`] ? 'pending' : ''}`}
                            onClick={() => onDeviceAction(device.id, 'unlock')}
                            disabled={actionPending[`${device.id}-unlock`] || !device.is_online}
                        >
                            <Unlock size={14} style={{ marginRight: '6px' }} /> Odemknout zařízení
                        </button>
                        <button
                            className={`action-btn-full resume ${actionPending[`${device.id}-resume-internet`] ? 'pending' : ''}`}
                            onClick={() => onDeviceAction(device.id, 'resume-internet')}
                            disabled={actionPending[`${device.id}-resume-internet`] || !device.is_online}
                        >
                            <Globe size={14} style={{ marginRight: '6px' }} /> Obnovit internet
                        </button>
                    </div>
                </div>
            )}

            {/* Expand indicator */}
            <div className="expand-indicator">
                <span className={`expand-arrow ${expanded ? 'up' : 'down'}`}>
                    {expanded ? '▲' : '▼'}
                </span>
            </div>
        </div>
    )
}

export default WindowsDeviceCard
