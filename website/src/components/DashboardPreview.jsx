import React from 'react'
import {
  LayoutDashboard,
  Smartphone,
  Shield,
  ScrollText,
  BarChart3,
  PlusCircle,
  Monitor,
  Grid,
  Lock,
  Camera,
} from 'lucide-react'
import './DashboardPreview.css'

const navItems = [
  { id: 'overview', label: 'Přehled', icon: LayoutDashboard },
  { id: 'devices', label: 'Zařízení', icon: Smartphone },
  { id: 'smart-shield', label: 'Smart Shield', icon: Shield },
  { id: 'rules', label: 'Pravidla', icon: ScrollText },
  { id: 'reports', label: 'Statistiky', icon: BarChart3 },
  { id: 'pairing', label: 'Přidat', icon: PlusCircle },
]

export default function DashboardPreview() {
  return (
    <section id="dashboard" className="dashboard-preview">
      <div className="dashboard-preview-inner">
        <h2 className="dashboard-preview-title">Responzivní dashboard</h2>
        <p className="dashboard-preview-intro">
          Přehled v prohlížeči i v mobilní aplikaci – stejná data na počítači, tabletu i Androidu.
        </p>
        <div className="dashboard-block">
        <div className="dashboard-mock">
          <header className="dashboard-mock-header-bar">
            <img src="/images/logo.png" alt="" className="dashboard-mock-logo" />
            <span className="dashboard-mock-brand">FamilyEye</span>
            <span className="dashboard-mock-pipe">|</span>
            <span className="dashboard-mock-subtitle">Rodičovská kontrola</span>
          </header>
          <div className="dashboard-mock-body">
            <aside className="dashboard-mock-nav">
              {navItems.map((item) => (
                <div key={item.id} className="dashboard-mock-nav-item">
                  <item.icon size={18} />
                  <span>{item.label}</span>
                </div>
              ))}
            </aside>
            <main className="dashboard-mock-main">
            <div className="dashboard-mock-content-header">
              <h3>Přehled</h3>
              <button type="button" className="dashboard-mock-btn">Obnovit</button>
            </div>
            <div className="dashboard-mock-stats">
              <div className="dashboard-mock-stat">
                <span className="dashboard-mock-stat-value">2</span>
                <span className="dashboard-mock-stat-label">Celkové zařízení</span>
              </div>
              <div className="dashboard-mock-stat">
                <span className="dashboard-mock-stat-value">1</span>
                <span className="dashboard-mock-stat-label">Aktivní zařízení</span>
              </div>
              <div className="dashboard-mock-stat">
                <span className="dashboard-mock-stat-value">3,5 hodin</span>
                <span className="dashboard-mock-stat-label">Celkový čas dnes</span>
              </div>
            </div>
            <div className="dashboard-mock-filter">
              <button type="button" className="dashboard-mock-filter-btn active">
                <Grid size={12} /> Všechna (2)
              </button>
              <button type="button" className="dashboard-mock-filter-btn">
                <Monitor size={12} /> Počítače (1)
              </button>
              <button type="button" className="dashboard-mock-filter-btn">
                <Smartphone size={12} /> Mobily (1)
              </button>
            </div>
            <div className="dashboard-mock-device">
              <div className="dashboard-mock-device-head">
                <span className="dashboard-mock-device-name">Dětský notebook</span>
                <span className="dashboard-mock-device-online">ONLINE</span>
              </div>
              <div className="dashboard-mock-device-meta">
                <span>Dnes: 2h 15m</span>
                <span>Aplikací: 5</span>
                <span>Pravidel: 3</span>
              </div>
              <div className="dashboard-mock-device-actions">
                <span className="dashboard-mock-action"><Lock size={12} /> Zamknout</span>
                <span className="dashboard-mock-action"><Camera size={12} /> Snímek obrazovky</span>
              </div>
            </div>
            </main>
          </div>
        </div>

        <div className="responsive-showcase">
          <div className="responsive-phone-wrap">
            <div className="device-frame device-phone">
              <img src="/images/mobile-dashboard.png" alt="Přehled v mobilní aplikaci" />
            </div>
            <span className="device-label">Přehled</span>
          </div>
          <div className="responsive-phone-wrap">
            <div className="device-frame device-phone">
              <img src="/images/mobile-stats.png" alt="Statistiky v mobilu" />
            </div>
            <span className="device-label">Statistiky</span>
          </div>
          <div className="responsive-phone-wrap">
            <div className="device-frame device-phone">
              <img src="/images/mobile-smart-shield.png" alt="Smart Shield v mobilu" />
            </div>
            <span className="device-label">Smart Shield</span>
          </div>
        </div>
        </div>
      </div>
    </section>
  )
}
