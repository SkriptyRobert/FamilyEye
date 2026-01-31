import React, { useState, useEffect } from 'react'
import { Shield, Menu, X, LayoutGrid, LayoutDashboard, Image, Download, BookOpen } from 'lucide-react'
import { DOCS_URL, RELEASES_URL, GITHUB_REPO } from '../utils/links'
import { img } from '../utils/assets'
import './Hero.css'

const navItems = [
  { href: '#features', label: 'Funkce', icon: LayoutGrid },
  { href: '#dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '#screenshots', label: 'Screenshoty', icon: Image },
  { href: RELEASES_URL, label: 'Stáhnout', icon: Download, external: true },
  { href: DOCS_URL, label: 'Dokumentace', icon: BookOpen, external: true },
]

export default function Hero() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  useEffect(() => {
    if (drawerOpen) document.body.style.overflow = 'hidden'
    else document.body.style.overflow = ''
    return () => { document.body.style.overflow = '' }
  }, [drawerOpen])

  const closeDrawer = () => setDrawerOpen(false)

  return (
    <header className="hero" style={{ '--hero-bg-image': `url(${img('images/hero-family.jpg')})` }}>
      <nav className="hero-nav">
        <a href="#" className="hero-logo">
          <img src={img('images/logo.png')} alt="FamilyEye" className="hero-logo-img" />
          <span className="hero-logo-text">FamilyEye</span>
        </a>
        <div className="hero-links">
          <a href="#features">Funkce</a>
          <a href="#dashboard">Dashboard</a>
          <a href="#screenshots">Screenshoty</a>
          <a href={RELEASES_URL} target="_blank" rel="noopener noreferrer">Stáhnout</a>
          <a href={DOCS_URL} target="_blank" rel="noopener noreferrer">Dokumentace</a>
        </div>
        <button
          type="button"
          className="hero-menu-btn"
          aria-label="Otevřít menu"
          aria-expanded={drawerOpen}
          onClick={() => setDrawerOpen(true)}
        >
          <Menu size={24} />
        </button>
      </nav>
      <div
        className={`hero-drawer-backdrop ${drawerOpen ? 'is-open' : ''}`}
        aria-hidden={!drawerOpen}
        onClick={closeDrawer}
      />
      <div className={`hero-drawer ${drawerOpen ? 'is-open' : ''}`} role="dialog" aria-label="Navigace">
        <div className="hero-drawer-header">
          <span className="hero-drawer-title">Menu</span>
          <button type="button" className="hero-drawer-close" aria-label="Zavřít menu" onClick={closeDrawer}>
            <X size={22} />
          </button>
        </div>
        <nav className="hero-drawer-nav">
          {navItems.map(({ href, label, icon: Icon, external }) => (
            <a
              key={label}
              href={href}
              className="hero-drawer-link"
              onClick={closeDrawer}
              {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
            >
              <Icon size={22} strokeWidth={1.8} />
              <span>{label}</span>
            </a>
          ))}
        </nav>
      </div>
      <div className="hero-content">
        <h1 className="hero-title">Digitální dohled pro bezpečí dětí</h1>
        <p className="hero-subtitle">
          Self-hosted rodičovská kontrola, která pomáhá odhalit rizikové chování dříve, než se z něj stane problém.
        </p>
        <p className="hero-desc">
          FamilyEye poskytuje centrální přehled nad zařízeními dětí (Android, Windows). Detekuje rizikový obsah (šikana, drogy, násilí), umožňuje rodičům ověřit situaci pomocí snímku obrazovky a dává plnou kontrolu nad daty bez cloudu třetích stran.
        </p>
        <div className="hero-actions">
          <a href={GITHUB_REPO} className="hero-btn hero-btn-primary" target="_blank" rel="noopener noreferrer">
            Začít na GitHubu
          </a>
          <a href={DOCS_URL} className="hero-btn hero-btn-secondary" target="_blank" rel="noopener noreferrer">
            Dokumentace
          </a>
        </div>
        <p className="hero-cta-badges">
          <span>100&nbsp;% zdarma</span>
          <span className="hero-cta-badges-sep">|</span>
          <span>Otevřený kód</span>
          <span className="hero-cta-badges-sep">|</span>
          <span>Přispějte kódem k vylepšení FamilyEye</span>
        </p>
      </div>
      <div className="hero-badge">
        <div className="hero-badge-text">
          <span className="hero-badge-line1">
            <Shield size={18} />
            Open Source · GPLv3
          </span>
          <em className="hero-badge-trust">zdrojový kód jako důkaz důvěryhodnosti</em>
        </div>
      </div>
    </header>
  )
}
