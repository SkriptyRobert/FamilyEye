import React from 'react'
import { DOCS_URL, GITHUB_REPO, RELEASES_URL } from '../utils/links'
import './Footer.css'

const VERSION = '2.4.0'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <img src="/images/logo.png" alt="FamilyEye" className="footer-logo" />
          <span className="footer-name">FamilyEye</span>
          <span className="footer-version">v{VERSION}</span>
        </div>
        <p className="footer-credit">
          Developed by BertSoftware
        </p>
        <div className="footer-links">
          <a href={GITHUB_REPO} target="_blank" rel="noopener noreferrer">GitHub</a>
          <a href={RELEASES_URL} target="_blank" rel="noopener noreferrer">Releases</a>
          <a href={DOCS_URL} target="_blank" rel="noopener noreferrer">Dokumentace</a>
          <a href={`${GITHUB_REPO}/blob/main/LICENSE`} target="_blank" rel="noopener noreferrer">Licence (GPLv3)</a>
        </div>
        <p className="footer-note">
          Projekt je ve fázi MVP a vyvíjí ho jeden vývojář. Funkce a dokumentace se průběžně rozšiřují a mohou se měnit. Mohou se objevit chyby a bugy, které můžete nahlásit na{' '}
          <a href="mailto:robert.pesout@gmail.com" className="footer-note-link">robert.pesout@gmail.com</a>.
        </p>
      </div>
    </footer>
  )
}
