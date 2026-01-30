import React from 'react'
import './CTA.css'

export default function CTA() {
  return (
    <section className="cta">
      <div className="cta-inner">
        <h2 className="cta-title">Zkuste FamilyEye ve své rodině</h2>
        <p className="cta-subtitle">Možnosti nasazení a instalace</p>
        <ul className="cta-list">
          <li><strong>Server:</strong> Docker/Kubernetes – jedna příkazová řádka</li>
          <li><strong>Windows:</strong> one-click instalátor pro agenta i server</li>
          <li><strong>Android:</strong> párování přes QR kód, volitelně Device Owner na pár kliknutí</li>
        </ul>
        <div className="cta-actions">
          <a
            href="https://github.com/SkriptyRobert/Parential-Control_Enterprise/releases"
            className="cta-btn cta-btn-primary"
            target="_blank"
            rel="noopener noreferrer"
          >
            Stáhnout (Releases)
          </a>
          <a
            href="https://github.com/SkriptyRobert/Parential-Control_Enterprise"
            className="cta-btn cta-btn-secondary"
            target="_blank"
            rel="noopener noreferrer"
          >
            Repozitář na GitHubu
          </a>
        </div>
        <p className="cta-note">
          Dokumentace včetně prvního nastavení, instalace serveru a agentů je v sekci Dokumentace (MkDocs).
        </p>
      </div>
    </section>
  )
}
