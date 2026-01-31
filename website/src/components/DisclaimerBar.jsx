import React from 'react'
import './DisclaimerBar.css'

export default function DisclaimerBar() {
  return (
    <div className="disclaimer-bar" role="doc-tip">
      <p className="disclaimer-bar-text">
        FamilyEye je nástroj pro ochranu, nikoliv pro špehování. Byl navržen tak, aby data nikdy neopustila vaši domácí síť. Rodičovská kontrola má být o dialogu, ne o skrytém sledování – proto je aplikace v zařízení viditelná a nelze ji zneužít jako spyware. Nástroj je určen výhradně pro rodiče a zákonné zástupce; monitorovaná osoba musí být o používání informována.
      </p>
    </div>
  )
}
