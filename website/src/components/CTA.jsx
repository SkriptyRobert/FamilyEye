import React from 'react'
import { RELEASES_URL, GITHUB_REPO } from '../utils/links'
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
        <p className="cta-badges">
          <span>100&nbsp;% zdarma</span>
          <span className="cta-badges-sep">|</span>
          <span>Otevřený kód</span>
          <span className="cta-badges-sep">|</span>
          <span>Přispějte kódem k vylepšení FamilyEye</span>
        </p>
        <div className="cta-actions">
          <a
            href={RELEASES_URL}
            className="cta-btn cta-btn-primary"
            target="_blank"
            rel="noopener noreferrer"
          >
            Stáhnout (Releases)
          </a>
          <a
            href={GITHUB_REPO}
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
