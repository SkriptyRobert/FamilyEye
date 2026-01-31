import React from 'react'
import { img } from '../utils/assets'
import './DashboardPreview.css'

export default function DashboardPreview() {
  return (
    <section id="dashboard" className="dashboard-preview">
      <div className="dashboard-preview-inner">
        <h2 className="dashboard-preview-title">Responzivní dashboard</h2>
        <p className="dashboard-preview-intro">
          Přehled v prohlížeči i v mobilní aplikaci – stejná data na počítači, tabletu i Androidu.
        </p>

        {/* Desktop Dashboard Screenshot */}
        <div className="dashboard-block">
          <div className="dashboard-image-frame">
            <img
              src={img('images/dashboard.png')}
              alt="FamilyEye Dashboard – přehled zařízení a rodičovská kontrola"
              loading="lazy"
            />
          </div>
        </div>

        {/* Mobile Screenshots */}
        <div className="responsive-showcase">
          <div className="responsive-phone-wrap">
            <div className="device-frame device-phone">
              <img src={img('images/mobile-dashboard.png')} alt="Přehled v mobilní aplikaci" />
            </div>
            <span className="device-label">Přehled</span>
          </div>
          <div className="responsive-phone-wrap">
            <div className="device-frame device-phone">
              <img src={img('images/mobile-stats.png')} alt="Statistiky v mobilu" />
            </div>
            <span className="device-label">Statistiky</span>
          </div>
          <div className="responsive-phone-wrap">
            <div className="device-frame device-phone">
              <img src={img('images/mobile-smart-shield.png')} alt="Smart Shield v mobilu" />
            </div>
            <span className="device-label">Smart Shield</span>
          </div>
        </div>
      </div>
    </section>
  )
}
