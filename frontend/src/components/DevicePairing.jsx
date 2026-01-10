import React, { useState, useEffect } from 'react'
import api from '../services/api'
import { Smartphone, Link as LinkIcon, Copy, CheckCircle, Monitor, Check } from 'lucide-react'
import './DevicePairing.css'

/**
 * Komponenta pro párování nového zařízení
 * Poskytuje krok-za-krokem průvodce pro rodiče
 */
const DevicePairing = () => {
    const [step, setStep] = useState(1)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [pairingData, setPairingData] = useState({
        token: null,
        qrCode: null,
        expiresAt: null
    })
    const [pairedDevice, setPairedDevice] = useState(null)
    const [timeLeft, setTimeLeft] = useState(0)

    // Odpočet platnosti tokenu
    useEffect(() => {
        if (!pairingData.expiresAt || step !== 2) return

        const updateTimer = () => {
            const now = new Date()
            const diff = Math.max(0, Math.floor((pairingData.expiresAt.getTime() - now.getTime()) / 1000))
            setTimeLeft(diff)
            return diff
        }

        const initialDiff = updateTimer()
        if (initialDiff <= 0) return

        const timer = setInterval(() => {
            const currentDiff = updateTimer()
            if (currentDiff <= 0) {
                clearInterval(timer)
            }
        }, 1000)

        return () => clearInterval(timer)
    }, [pairingData.expiresAt, step])

    const generateToken = async () => {
        setLoading(true)
        setError(null)

        try {
            const response = await api.post('/api/devices/pairing/token')
            const { token, expires_at } = response.data

            // Získat QR kód
            const qrResponse = await api.get(`/api/devices/pairing/qr/${token}`)

            setPairingData({
                token,
                qrCode: qrResponse.data.qr_code,
                expiresAt: new Date(expires_at)
            })

            // Okamžitě vypočítat a nastavit čas, aby neproblikl stav "vypršelo"
            const now = new Date()
            const expires = new Date(expires_at)
            const diff = Math.max(0, Math.floor((expires.getTime() - now.getTime()) / 1000))
            setTimeLeft(diff)

            setStep(2)
        } catch (err) {
            console.error('Pairing error:', err)
            const errorMsg = err.response?.data?.detail || err.message || 'Nepodařilo se vygenerovat párovací kód'
            setError(`Chyba: ${typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg)}`)
        } finally {
            setLoading(false)
        }
    }

    const checkPairing = async () => {
        setLoading(true)

        try {
            // Zkontrolovat, zda bylo zařízení spárováno
            const response = await api.get('/api/devices/')
            const devices = response.data

            // Najít nově spárované zařízení
            const newDevice = devices.find(d => {
                const pairedAt = new Date(d.paired_at)
                return (Date.now() - pairedAt.getTime()) < 5 * 60 * 1000 // Spárováno v posledních 5 minutách
            })

            if (newDevice) {
                setPairedDevice(newDevice)
                setStep(3)
            } else {
                setError('Zatím nebylo spárováno žádné zařízení. Dokončete instalaci na dětském počítači.')
            }
        } catch (err) {
            setError('Chyba při kontrole párování.')
        } finally {
            setLoading(false)
        }
    }

    const getServerAddress = () => {
        // Získat IP adresu serveru pro zobrazení
        const hostname = window.location.hostname
        const port = window.location.port || '8000'
        return `https://${hostname}:${port}`
    }

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text)
        // Feedback
        alert('Zkopírováno do schránky!')
    }

    const formatTimeRemaining = () => {
        if (!pairingData.expiresAt) return ''
        if (timeLeft <= 0) return 'Token vypršel'

        const minutes = Math.floor(timeLeft / 60)
        const seconds = timeLeft % 60
        return `${minutes}:${seconds.toString().padStart(2, '0')}`
    }

    return (
        <div className="device-pairing">
            {/* Progress stepper */}
            <div className="pairing-stepper">
                <div className={`step ${step >= 1 ? 'active' : ''} ${step > 1 ? 'completed' : ''}`}>
                    <div className="step-number">1</div>
                    <div className="step-label">Vygenerovat kód</div>
                </div>
                <div className="step-line"></div>
                <div className={`step ${step >= 2 ? 'active' : ''} ${step > 2 ? 'completed' : ''}`}>
                    <div className="step-number">2</div>
                    <div className="step-label">Nainstalovat agenta</div>
                </div>
                <div className="step-line"></div>
                <div className={`step ${step >= 3 ? 'active' : ''}`}>
                    <div className="step-number">3</div>
                    <div className="step-label">Hotovo</div>
                </div>
            </div>

            {/* Step 1: Generate token */}
            {step === 1 && (
                <div className="pairing-step">
                    <div className="step-icon"><Smartphone size={48} /></div>
                    <h2>Přidat nové zařízení</h2>
                    <p>
                        Chcete přidat nový počítač nebo telefon pod rodičovskou kontrolu?
                        Vygenerujte párovací kód a použijte ho při instalaci agenta na dětském zařízení.
                    </p>

                    <div className="requirements-box">
                        <h4>Co budete potřebovat:</h4>
                        <ul>
                            <li><Check size={14} style={{ marginRight: '6px', color: 'var(--success-color)' }} /> Přístup k dětskému počítači</li>
                            <li><Check size={14} style={{ marginRight: '6px', color: 'var(--success-color)' }} /> Administrátorská práva na dětském PC</li>
                            <li><Check size={14} style={{ marginRight: '6px', color: 'var(--success-color)' }} /> Připojení k síti</li>
                        </ul>
                    </div>

                    {error && <div className="error-message">{error}</div>}

                    <button
                        className="primary-button"
                        onClick={generateToken}
                        disabled={loading}
                    >
                        {loading ? 'Generuji...' : 'Vygenerovat párovací kód'}
                    </button>
                </div>
            )}

            {/* Step 2: Show pairing info */}
            {step === 2 && (
                <div className="pairing-step">
                    <div className="step-icon"><LinkIcon size={48} /></div>
                    <h2>Nainstalujte agenta na dětský počítač</h2>

                    <div className="pairing-info-cards">
                        {/* Server adresa */}
                        <div className="info-card">
                            <div className="info-label">Adresa serveru</div>
                            <div className="info-value copyable" onClick={() => copyToClipboard(getServerAddress())}>
                                {getServerAddress()}
                                <span className="copy-icon"><Copy size={16} /></span>
                            </div>
                        </div>

                        {/* Párovací token */}
                        <div className="info-card">
                            <div className="info-label">Párovací token</div>
                            <div className="info-value copyable token" onClick={() => copyToClipboard(pairingData.token)}>
                                {pairingData.token}
                                <span className="copy-icon"><Copy size={16} /></span>
                            </div>
                            <div className={`info-expires ${timeLeft < 60 ? 'critical' : timeLeft < 180 ? 'warning' : ''}`}>
                                {timeLeft <= 0 ? 'Token vypršel' : `Platnost: ${formatTimeRemaining()}`}
                            </div>
                        </div>
                    </div>

                    {/* QR kód */}
                    {pairingData.qrCode && (
                        <div className="qr-section">
                            <p>Nebo naskenujte QR kód z dětského zařízení:</p>
                            <img
                                src={pairingData.qrCode}
                                alt="QR kód pro párování"
                                className="qr-code"
                            />
                        </div>
                    )}

                    {/* Instrukce */}
                    <div className="instructions-box">
                        <h4>Na dětském počítači:</h4>
                        <ol>
                            <li>Stáhněte instalátor agenta z <strong>parentalcontrol.cz/agent</strong></li>
                            <li>Spusťte instalátor jako <strong>správce</strong></li>
                            <li>Během instalace zadejte <strong>adresu serveru</strong> a <strong>párovací token</strong></li>
                            <li>Dokončete instalaci</li>
                        </ol>
                    </div>

                    {error && <div className="error-message">{error}</div>}

                    <div className="button-group">
                        <button
                            className="secondary-button"
                            onClick={generateToken}
                            disabled={loading}
                        >
                            Nový kód
                        </button>
                        <button
                            className="primary-button"
                            onClick={checkPairing}
                            disabled={loading}
                        >
                            {loading ? 'Kontroluji...' : 'Zkontrolovat párování'}
                        </button>
                    </div>
                </div>
            )}

            {/* Step 3: Success */}
            {step === 3 && pairedDevice && (
                <div className="pairing-step success">
                    <div className="step-icon success-icon"><CheckCircle size={48} /></div>
                    <h2>Zařízení úspěšně připojeno!</h2>

                    <div className="device-card-new">
                        <div className="device-icon"><Monitor size={24} /></div>
                        <div className="device-info">
                            <div className="device-name">{pairedDevice.name}</div>
                            <div className="device-type">{pairedDevice.device_type}</div>
                            <div className="device-status online">● Online</div>
                        </div>
                    </div>

                    <p>
                        Nové zařízení je nyní pod vaší kontrolou.
                        Můžete nastavit pravidla a časové limity.
                    </p>

                    <button
                        className="primary-button"
                        onClick={() => window.location.href = '/'}
                    >
                        Přejít na přehled
                    </button>
                </div>
            )}
        </div>
    )
}

export default DevicePairing
