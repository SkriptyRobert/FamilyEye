import React from 'react'
import { Shield } from 'lucide-react'
import DOCS_URL from '../utils/docsUrl'
import './Hero.css'

export default function Hero() {
  return (
    <header className="hero">
      <nav className="hero-nav">
        <a href="#" className="hero-logo">
          <img src="/images/logo.png" alt="FamilyEye" className="hero-logo-img" />
          <span className="hero-logo-text">FamilyEye</span>
        </a>
        <div className="hero-links">
          <a href="#features">Funkce</a>
          <a href="#dashboard">Dashboard</a>
          <a href="#screenshots">Screenshoty</a>
          <a href="https://github.com/SkriptyRobert/Parential-Control_Enterprise/releases" target="_blank" rel="noopener noreferrer">Stáhnout</a>
          <a href={DOCS_URL} target="_blank" rel="noopener noreferrer">Dokumentace</a>
        </div>
      </nav>
      <div className="hero-content">
        <h1 className="hero-title">Digitální bezpečnost pro moderní rodinu</h1>
        <p className="hero-subtitle">
          Self-hosted rodičovská kontrola, která pomáhá odhalit rizikové chování dříve, než se z něj stane problém.
        </p>
        <p className="hero-desc">
          FamilyEye poskytuje centrální přehled nad zařízeními dětí (Android, Windows). Detekuje rizikový obsah (šikana, drogy, násilí), umožňuje rodičům ověřit situaci pomocí snímku obrazovky a dává plnou kontrolu nad daty bez cloudu třetích stran.
        </p>
        <div className="hero-actions">
          <a href="https://github.com/SkriptyRobert/Parential-Control_Enterprise" className="hero-btn hero-btn-primary" target="_blank" rel="noopener noreferrer">
            Začít na GitHubu
          </a>
          <a href={DOCS_URL} className="hero-btn hero-btn-secondary" target="_blank" rel="noopener noreferrer">
            Dokumentace
          </a>
        </div>
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
