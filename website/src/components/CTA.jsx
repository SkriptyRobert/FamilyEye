import React from 'react'
import { Server, Monitor, Smartphone } from 'lucide-react'
import { RELEASES_URL, GITHUB_REPO } from '../utils/links'
import './CTA.css'

const deploymentOptions = [
  {
    icon: Server,
    title: 'Server',
    desc: 'Docker/Kubernetes – jedna příkazová řádka',
    highlight: 'docker-compose up',
  },
  {
    icon: Monitor,
    title: 'Windows',
    desc: 'One-click instalátor pro agenta i server',
    highlight: 'Bez příkazů',
  },
  {
    icon: Smartphone,
    title: 'Android',
    desc: 'Párování přes QR kód, volitelně Device Owner',
    highlight: 'Pár kliknutí',
  },
]

export default function CTA() {
  return (
    <section className="cta">
      <div className="cta-inner">
        <h2 className="cta-title">Zkuste FamilyEye ve své rodině</h2>
        <p className="cta-subtitle">Možnosti nasazení a instalace</p>

        <div className="cta-cards">
          {deploymentOptions.map((opt) => (
            <div key={opt.title} className="cta-card">
              <div className="cta-card-icon">
                <opt.icon size={28} />
              </div>
              <h3 className="cta-card-title">{opt.title}</h3>
              <p className="cta-card-desc">{opt.desc}</p>
              <span className="cta-card-highlight">{opt.highlight}</span>
            </div>
          ))}
        </div>

        <p className="cta-badges">
          <span>100&nbsp;% zdarma</span>
          <span className="cta-badges-sep">•</span>
          <span>Otevřený kód</span>
          <span className="cta-badges-sep">•</span>
          <span>Přispějte k vylepšení</span>
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
          Dokumentace včetně prvního nastavení je v sekci Dokumentace (MkDocs).
        </p>
      </div>
    </section>
  )
}
