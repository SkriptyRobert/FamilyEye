import React from 'react'
import { img } from '../utils/assets'
import './LoginPreview.css'

export default function LoginPreview() {
  return (
    <div className="login-preview" aria-hidden="true">
      <img src={img('images/logo.png')} alt="" className="login-preview-logo" />
      <p className="login-preview-title">Přihlášení</p>
      <div className="login-preview-field" />
      <div className="login-preview-field" />
      <div className="login-preview-btn">Přihlásit</div>
    </div>
  )
}
