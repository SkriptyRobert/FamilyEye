import React, { useState, useEffect } from 'react'
import { removeToken, getBackendUrl } from '../utils/auth'
import api from '../services/api'
import DeviceList from './DeviceList'
import DevicePairing from './DevicePairing'
import RuleEditor from './RuleEditor'
import Reports from './Reports'
import StatusOverview from './StatusOverview'
import SmartShieldView from './SmartShieldView' // Import
import NotificationDropdown from './NotificationDropdown'
import './Dashboard.css'
import logo from '../assets/logo.png'
import {
  LayoutDashboard,
  Smartphone,
  Shield,
  BarChart3,
  PlusCircle,
  LogOut,
  Menu,
  Moon,
  Sun,
  Eye,
  ScrollText // For Rules
} from 'lucide-react'

const Dashboard = ({ onLogout, darkMode, setDarkMode }) => {
  const [activeTab, setActiveTab] = useState('overview')
  const [selectedDevice, setSelectedDevice] = useState(null)
  const [serverInfo, setServerInfo] = useState(null)
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false)

  useEffect(() => {
    // Fetch server info on mount
    const fetchServerInfo = async () => {
      try {
        const response = await api.get('/api/info')
        setServerInfo(response.data)
      } catch (error) {
        console.error('Failed to fetch server info:', error)
      }
    }
    fetchServerInfo()
  }, [])

  const handleLogout = () => {
    removeToken()
    onLogout()
  }

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    setIsMobileNavOpen(false)
  }

  const navItems = [
    { id: 'overview', label: 'Přehled', icon: <LayoutDashboard size={20} /> },
    { id: 'devices', label: 'Zařízení', icon: <Smartphone size={20} /> },
    { id: 'smart-shield', label: 'Smart Shield', icon: <Shield size={20} /> }, // New
    { id: 'rules', label: 'Pravidla', icon: <ScrollText size={20} /> }, // Changed icon
    { id: 'reports', label: 'Statistiky', icon: <BarChart3 size={20} /> },
    { id: 'pairing', label: 'Přidat', icon: <PlusCircle size={20} /> },
  ]

  return (
    <div className="dashboard-container">
      {/* Mobile header */}
      <header className="dashboard-header">
        <div className="header-left">
          <button
            className="mobile-menu-btn"
            onClick={() => setIsMobileNavOpen(!isMobileNavOpen)}
            aria-label="Menu"
          >
            <Menu size={24} color="var(--text-primary)" />
          </button>
          <h1 className="header-title">
            <img src={logo} alt="FamilyEye" className="title-logo" />
            <span className="title-text">FamilyEye</span>
            <span className="title-subtitle">Rodičovská kontrola</span>
          </h1>
        </div>
        <div className="header-right">
          <button
            type="button"
            onClick={() => setDarkMode(!darkMode)}
            className="theme-toggle"
            title={darkMode ? 'Světlý režim' : 'Tmavý režim'}
          >
            {darkMode ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          <NotificationDropdown />
          <button onClick={handleLogout} className="logout-button">
            <LogOut size={16} />
            <span className="logout-text">Odhlásit</span>
          </button>
        </div>
      </header>


      <div className="dashboard-layout">
        {/* Navigation */}
        <nav className={`dashboard-nav ${isMobileNavOpen ? 'open' : ''}`}>
          <div className="nav-backdrop" onClick={() => setIsMobileNavOpen(false)}></div>
          <div className="nav-content">
            {navItems.map(item => (
              <button
                key={item.id}
                onClick={() => handleTabChange(item.id)}
                className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
              </button>
            ))}
          </div>
        </nav>

        {/* Main content */}
        <main className="dashboard-content">
          {activeTab === 'overview' && <StatusOverview />}
          {activeTab === 'devices' && (
            <DeviceList onSelectDevice={setSelectedDevice} />
          )}
          {activeTab === 'smart-shield' && <SmartShieldView />}
          {activeTab === 'pairing' && <DevicePairing />}
          {activeTab === 'rules' && (
            <RuleEditor deviceId={selectedDevice?.id} />
          )}
          {activeTab === 'reports' && (
            <Reports deviceId={selectedDevice?.id} />
          )}
        </main>
      </div>


      {/* Status Footer (Desktop) */}
      <footer className="status-footer">
        <div className="status-footer-left">
          {serverInfo && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span className="server-info-dot"></span>
                <span>Server: {serverInfo.local_ip || 'localhost'}</span>
              </div>
            </>
          )}
        </div>
        <div className="status-footer-right">
          <span><Eye size={12} style={{ marginRight: '4px' }} /> FamilyEye · v1.0 | Developed by BertSoftware</span>
        </div>
      </footer>

      {/* Mobile bottom navigation */}
      <nav className="mobile-bottom-nav">
        {navItems.slice(0, 4).map(item => (
          <button
            key={item.id}
            onClick={() => handleTabChange(item.id)}
            className={`bottom-nav-item ${activeTab === item.id ? 'active' : ''}`}
          >
            <span className="bottom-nav-icon">{item.icon}</span>
            <span className="bottom-nav-label">{item.label}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}

export default Dashboard
