import React from 'react'
import {
    Bell,
    CheckCircle,
    AlertTriangle,
    Lock,
    Unlock,
    Monitor,
    Smartphone,
    Globe,
    BarChart3,
    Clock,
    Wifi,
    WifiOff,
    Plus,
    Minus,
    X,
    XCircle,
    Check,
    Info,
    AlertCircle,
    Activity,
    Cpu,
    HardDrive,
    Gamepad2,
    Music,
    Video,
    MessageSquare,
    Code,
    FileText,
    Folder,
    Image,
    Calendar,
    Settings,
    User,
    Users,
    Eye,
    EyeOff,
    Trash2,
    Edit,
    RefreshCw,
    Download,
    Upload,
    Link,
    ExternalLink,
    ChevronDown,
    ChevronUp,
    ChevronRight,
    ChevronLeft,
    MoreHorizontal,
    MoreVertical,
    Search,
    Filter,
    SortAsc,
    SortDesc,
    Circle,
    CircleDot,
    Shield,
    Scroll,
} from 'lucide-react'

// Map of icon names to components
const iconMap = {
    // Notifications & Status
    bell: Bell,
    'check-circle': CheckCircle,
    check: Check,
    'alert-triangle': AlertTriangle,
    'alert-circle': AlertCircle,
    'x-circle': XCircle,
    info: Info,
    x: X,

    // Security
    lock: Lock,
    unlock: Unlock,

    // Devices
    monitor: Monitor,
    smartphone: Smartphone,
    computer: Monitor,
    phone: Smartphone,

    // Network
    globe: Globe,
    wifi: Wifi,
    'wifi-off': WifiOff,
    internet: Globe,

    // Charts & Data
    'bar-chart': BarChart3,
    chart: BarChart3,
    activity: Activity,

    // Time
    clock: Clock,
    calendar: Calendar,

    // Actions
    plus: Plus,
    minus: Minus,
    edit: Edit,
    trash: Trash2,
    refresh: RefreshCw,
    download: Download,
    upload: Upload,

    // App Categories
    game: Gamepad2,
    gaming: Gamepad2,
    music: Music,
    video: Video,
    chat: MessageSquare,
    social: MessageSquare,
    code: Code,
    development: Code,
    document: FileText,
    file: FileText,
    folder: Folder,
    image: Image,
    app: Monitor, // Generic app icon

    // System
    cpu: Cpu,
    'hard-drive': HardDrive,
    settings: Settings,

    // Users
    user: User,
    users: Users,

    // Visibility
    eye: Eye,
    'eye-off': EyeOff,

    // Links
    link: Link,
    'external-link': ExternalLink,

    // Navigation
    'chevron-down': ChevronDown,
    'chevron-up': ChevronUp,
    'chevron-right': ChevronRight,
    'chevron-left': ChevronLeft,
    'more-horizontal': MoreHorizontal,
    'more-vertical': MoreVertical,

    // Search & Filter
    search: Search,
    filter: Filter,
    'sort-asc': SortAsc,
    'sort-desc': SortDesc,

    // Status indicators
    circle: Circle,
    'circle-dot': CircleDot,

    // Smart Shield
    shield: Shield,
    'shield-alert': Shield,
    'shield-check': Shield,

    // Rules
    scroll: Scroll,
}

/**
 * Dynamic Icon Component
 * Renders a Lucide icon based on a string name
 * 
 * @param {string} name - Icon name (e.g., 'bell', 'check-circle', 'smartphone')
 * @param {number} size - Icon size in pixels (default: 16)
 * @param {string} color - Icon color (default: 'currentColor')
 * @param {string} className - Additional CSS classes
 * @param {object} style - Inline styles
 */
const DynamicIcon = ({
    name,
    size = 16,
    color = 'currentColor',
    className = '',
    style = {},
    ...props
}) => {
    const IconComponent = iconMap[name?.toLowerCase()]

    if (!IconComponent) {
        // Fallback: return a generic circle if icon not found
        console.warn(`DynamicIcon: Unknown icon name "${name}"`)
        return <Circle size={size} color={color} className={className} style={style} {...props} />
    }

    return (
        <IconComponent
            size={size}
            color={color}
            className={className}
            style={style}
            {...props}
        />
    )
}

// Export individual icons for direct import where needed
export {
    Bell,
    CheckCircle,
    AlertTriangle,
    Lock,
    Unlock,
    Monitor,
    Smartphone,
    Globe,
    BarChart3,
    Clock,
    Wifi,
    WifiOff,
    Plus,
    Minus,
    X,
    Check,
    Info,
    AlertCircle,
    Activity,
    Gamepad2,
    Music,
    Video,
    MessageSquare,
    Code,
    FileText,
    RefreshCw,
    Edit,
    Trash2,
    Eye,
    EyeOff,
    ChevronDown,
    ChevronUp,
}

export default DynamicIcon
