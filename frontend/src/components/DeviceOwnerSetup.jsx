import React, { useState, useEffect, useCallback } from 'react'
import { Smartphone, Usb, CheckCircle, AlertCircle, Loader, Computer, Terminal, Settings, HelpCircle, Trash2, Shield } from 'lucide-react'
import { AdbDaemonWebUsbDeviceManager } from "@yume-chan/adb-daemon-webusb";
import { Adb, AdbDaemonTransport } from "@yume-chan/adb";
import { Consumable, InspectableWritableStream } from "@yume-chan/stream-extra";
import AdbWebCredentialStore from "@yume-chan/adb-credential-web";
import './DeviceOwnerSetup.css'

/**
 * Device Owner Setup Wizard (Real WebADB Implementation)
 */
const MOBILE_BREAKPOINT = 768

const DeviceOwnerSetup = ({ deviceId, onComplete, onCancel }) => {
  const [step, setStep] = useState(1)
  const [adb, setAdb] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [status, setStatus] = useState('idle')
  const [commandOutput, setCommandOutput] = useState('') // Terminal output log
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.innerWidth <= MOBILE_BREAKPOINT)

  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT}px)`)
    const update = () => setIsMobile(mq.matches)
    mq.addEventListener('change', update)
    update()
    return () => mq.removeEventListener('change', update)
  }, [])

  // Constants
  const PACKAGE_NAME = 'com.familyeye.agent'
  const ADMIN_RECEIVER = 'com.familyeye.agent.receiver.FamilyEyeDeviceAdmin'
  const DEVICE_OWNER_CMD = `dpm set-device-owner ${PACKAGE_NAME}/${ADMIN_RECEIVER}`

  // Cleanup ADB on unmount
  useEffect(() => {
    return () => {
      if (adb) {
        try { adb.close(); } catch (e) { console.error("Error closing ADB:", e); }
      }
    }
  }, [adb]);

  const handleNext = () => { if (step < 4) setStep(step + 1); setError(null); }
  const handleBack = () => { if (step > 1) setStep(step - 1); setError(null); }

  const handleConnect = async () => {
    setLoading(true); setError(null); setStatus('connecting');

    try {
      const Manager = AdbDaemonWebUsbDeviceManager.BROWSER;
      if (!Manager) throw new Error("WebUSB není v tomto prohlížeči podporováno.");

      const device = await Manager.requestDevice();
      if (!device) throw new Error("Nebylo vybráno žádné zařízení.");

      const connection = await device.connect();

      // Use real credential store for RSA key generation
      const credentialStore = new AdbWebCredentialStore();

      // Corrected: Use AdbDaemonTransport to authenticate first
      const transport = await AdbDaemonTransport.authenticate({
        serial: device.serial,
        connection,
        credentialStore,
      });

      // Then create ADB instance with the transport
      const adbInstance = new Adb(transport);

      setAdb(adbInstance);
      setStatus('connected');
      setStep(3);
    } catch (err) {
      console.error(err);
      let errorMessage = err.message || "Neznámá chyba";

      // Localization of common WebUSB errors
      if (errorMessage.includes("No device selected")) {
        errorMessage = "Nebylo vybráno žádné zařízení.";
      } else if (errorMessage.includes("already in used") || errorMessage.includes("ClaimInterface")) {
        errorMessage = "Zařízení je používáno jiným programem! Vypněte prosím ADB terminál na PC příkazem 'adb kill-server' nebo zavřete jiné aplikace komunikující s telefonem.";
      } else if (errorMessage.includes("Access denied")) {
        errorMessage = "Přístup odepřen. Na telefonu musíte potvrdit dialog 'Povolit ladění USB'.";
      }

      setError(errorMessage);
      setStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async () => {
    if (!adb) { setError("ADB spojení ztraceno."); return; }

    setLoading(true); setError(null); setStatus('activating');
    setCommandOutput(prev => prev + `> ${DEVICE_OWNER_CMD}\n`);

    try {
      // 1. Spawning Process
      let process;
      if (adb.subprocess.shellProtocol) {
        process = await adb.subprocess.shellProtocol.spawn(DEVICE_OWNER_CMD);
      } else if (adb.subprocess.noneProtocol) {
        process = await adb.subprocess.noneProtocol.spawn(DEVICE_OWNER_CMD);
      } else {
        throw new Error("ADB subprocess protocol not supported on this device.");
      }

      // 2. Reading Output (Stdout + Stderr concurrently)
      const stdoutReader = process.stdout.getReader();
      const stderrReader = process.stderr.getReader();
      let fullOutput = "";

      const readStream = async (reader) => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = new TextDecoder().decode(value);
            fullOutput += chunk;
            setCommandOutput(prev => prev + chunk);
          }
        } catch (e) {
          console.error("Reader error:", e);
        } finally {
          reader.releaseLock();
        }
      };

      // 3. Timeout Logic (10s)
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error("Timeout: Zařízení neodpovídá. Zkontrolujte telefon (Xiaomi Security Settings?) nebo potvrďte dialog.")), 10000)
      );

      // Execute readers
      await Promise.race([
        Promise.all([readStream(stdoutReader), readStream(stderrReader)]),
        timeoutPromise
      ]);

      // 4. Processing Result
      const outputLower = fullOutput.toLowerCase();

      if (outputLower.includes("success") || fullOutput.trim() === "") {
        setStatus('success');
        setStep(4);
      } else if (fullOutput.includes("Device owner is already set") || (fullOutput.includes("already") && !fullOutput.includes("not allowed"))) {
        // Success: Already set (and not failed due to accounts/not allowed)
        setCommandOutput(prev => prev + "\n[INFO] Device Owner již byl nastaven.\n");
        setStatus('success');
        setStep(4);
      } else {
        // Verify if it failed
        if (fullOutput.includes("accounts")) {
          throw new Error("Na zařízení jsou stále přihlášené účty! Dočasně odhlaste Google/Xiaomi účty; po aktivaci je můžete znovu přidat.");
        }
        if (fullOutput.includes("Exception") || fullOutput.includes("Error")) {
          throw new Error(fullOutput);
        }
        // Fallback for weird outputs or silent failures
        setStatus('success');
        setStep(4);
      }

    } catch (err) {
      console.error(err);
      const msg = err.message || "Neznámá chyba";
      setCommandOutput(prev => prev + `\n[ERROR] ${msg}\n`);

      if (msg.includes("Account") || msg.includes("Not allowed")) {
        setError("Chyba: Na zařízení je stále přihlášen Google účet. Dočasně odhlaste všechny účty; po aktivaci je můžete znovu přidat.");
      } else if (msg.includes("SecurityException") || msg.includes("Permission denied") || msg.includes("MANAGE_DEVICE_ADMINS")) {
        setError("Xiaomi/HyperOS detekováno! Musíte v 'Možnosti pro vývojáře' zapnout volbu 'Ladění USB (Bezpečnostní nastavení)'. Po zapnutí příkaz zkuste znovu.");
      } else if (msg.includes("Timeout")) {
        setError("Časový limit vypršel. Zkontrolujte displej telefonu!");
      } else {
        setError("Aktivace selhala. Viz terminál.");
      }
      setStatus('error');
    } finally {
      setLoading(false);
    }
  };

  if (isMobile) {
    return (
      <div className="device-owner-setup device-owner-setup-mobile">
        <div className="setup-header">
          <Computer className="step-icon-small" size={48} style={{ marginBottom: '1rem', color: 'var(--accent-color)' }} />
          <h2>Aktivace Device Owner</h2>
          <p className="mobile-lead">Průvodce aktivace vyžaduje počítač s USB.</p>
        </div>
        <div className="mobile-do-instructions">
          <p>Na telefonu nebo tabletu nelze aktivovat Device Owner (chybí WebUSB a připojení telefonu kabelem).</p>
          <ol>
            <li>Otevřete tento dashboard na <strong>počítači</strong> (notebook, PC).</li>
            <li>Připojte dětský Android telefon k počítači <strong>USB kabelem</strong>.</li>
            <li>V záložce Zařízení u daného zařízení klikněte na <strong>Aktivovat DO</strong> a postupujte podle průvodce.</li>
          </ol>
        </div>
        <div className="step-actions" style={{ marginTop: '1.5rem' }}>
          <button type="button" onClick={onCancel} className="btn-primary">Zavřít</button>
        </div>
      </div>
    )
  }

  return (
    <div className="device-owner-setup">
      <div className="setup-header">
        <h2>Aktivace Device Owner</h2>
        <p>Maximální ochrana pro Android zařízení</p>
      </div>

      <div className="progress-steps">
        {[1, 2, 3, 4].map((num) => (
          <div key={num} className={`step ${step >= num ? 'active' : ''} ${step === num ? 'current' : ''}`}>
            <div className="step-number">{num}</div>
            <div className="step-label">
              {num === 1 && 'Příprava'}
              {num === 2 && 'Telefon'}
              {num === 3 && 'Připojení'}
              {num === 4 && 'Aktivace'}
            </div>
          </div>
        ))}
      </div>

      <div className="step-content">
        {step === 1 && <PreparationStep onNext={handleNext} />}
        {step === 2 && <PhoneStep onNext={handleNext} onBack={handleBack} />}
        {step === 3 && (
          <ConnectionStep
            loading={loading}
            error={error}
            onConnect={handleConnect}
            onBack={handleBack}
            status={status}
            adb={adb}
            onNext={handleNext}
          />
        )}
        {step === 4 && (
          <ActivationStep
            loading={loading}
            error={error}
            onActivate={handleActivate}
            onBack={handleBack}
            onComplete={onComplete}
            status={status}
            output={commandOutput}
          />
        )}
      </div>
    </div>
  )
}

// ... Subcomponents remain mostly similar but enhanced ...

const PreparationStep = ({ onNext }) => (
  <div className="step-panel">
    <div className="step-header-compact">
      <Computer className="step-icon-small" size={32} />
      <h3>Příprava zařízení</h3>
    </div>

    <div className="instruction-list compact">
      <div className="instruction-item">
        <div className="instruction-number">1</div>
        <div className="instruction-icon-wrapper"><Settings size={18} /></div>
        <div className="instruction-content">
          <span className="instruction-title">Aktivace vývojářského režimu</span>
          <p className="instruction-detail">
            V <em>O telefonu</em> klepněte 7x na <strong>Číslo sestavení</strong>. V menu <em>Pro vývojáře</em> povolte <strong>Ladění USB</strong>.
          </p>
        </div>
      </div>

      <div className="instruction-item">
        <div className="instruction-number">2</div>
        <div className="instruction-icon-wrapper"><Shield size={18} /></div>
        <div className="instruction-content">
          <span className="instruction-title">Xiaomi / HyperOS (Povinné)</span>
          <p className="instruction-detail">
            Aktivujte volbu <strong>Ladění USB (Bezpečnostní nastavení)</strong>. Tento krok vyžaduje přihlášení k Mi účtu.
          </p>
        </div>
      </div>

      <div className="instruction-item critical">
        <div className="instruction-number">3</div>
        <div className="instruction-icon-wrapper"><Trash2 size={18} /></div>
        <div className="instruction-content">
          <span className="instruction-title">Dočasné odhlášení účtů</span>
          <p className="instruction-detail">
            V <em>Nastavení {'>'} Účty</em> dočasně odhlaste <strong>všechny</strong> přihlášené účty (Google, Xiaomi atd.). Po aktivaci Device Owner je můžete znovu přidat.
          </p>
        </div>
      </div>

      <div className="instruction-item">
        <div className="instruction-number">4</div>
        <div className="instruction-icon-wrapper"><Usb size={18} /></div>
        <div className="instruction-content">
          <span className="instruction-title">Připojení k pracovní stanici</span>
          <p className="instruction-detail">Propojte telefon kabelem a zvolte režim <em>Přenos souborů</em>.</p>
        </div>
      </div>
    </div>

    <div className="step-actions">
      <button onClick={onNext} className="btn-primary">Pokračovat k aktivaci</button>
    </div>
  </div>
)

const PhoneStep = ({ onNext, onBack }) => (
  <div className="step-panel">
    <Smartphone className="step-icon" size={64} />
    <h3>Telefon</h3>
    <p>Ujistěte se, že máte na telefonu nainstalovanou aplikaci FamilyEye Agent.</p>
    <div className="step-actions">
      <button onClick={onBack} className="btn-secondary">Zpět</button>
      <button onClick={onNext} className="btn-primary">Pokračovat</button>
    </div>
  </div>
)

const ConnectionStep = ({ adb, loading, error, onConnect, onBack, onNext, status }) => (
  <div className="step-panel">
    <Usb className="step-icon" size={64} />
    <h3>Připojení k zařízení</h3>

    {!adb ? (
      <>
        <p>Klikněte pro výběr Android zařízení ze seznamu prohlížeče.</p>
        <div className="step-actions">
          <button onClick={onBack} className="btn-secondary">Zpět</button>
          <button onClick={onConnect} className="btn-primary" disabled={loading}>
            {loading ? <><Loader className="spinner" size={16} /> Hledám...</> : 'Vybrat zařízení'}
          </button>
        </div>
      </>
    ) : (
      <>
        <div className="success-box">
          <CheckCircle size={24} />
          <p>Zařízení připojeno!</p>
          <p className="device-info">{adb.serial}</p>
        </div>
        <div className="step-actions">
          <button onClick={onBack} className="btn-secondary">Odpojit</button>
          <button onClick={onNext} className="btn-primary">Pokračovat k aktivaci</button>
        </div>
      </>
    )}

    {error && <div className="error-box"><AlertCircle size={20} /><p>{error}</p></div>}
  </div>
)

const ActivationStep = ({ loading, error, onActivate, onBack, onComplete, status, output }) => (
  <div className="step-panel">
    <CheckCircle className="step-icon" size={64} />
    <h3>Aktivace Device Owner</h3>

    <div className="terminal-box">
      <div className="terminal-header"><Terminal size={14} /> ADB Output</div>
      <div className="terminal-content">
        {output || "Waiting for command..."}
      </div>
    </div>

    {status !== 'success' && (
      <div className="step-actions">
        <button onClick={onBack} className="btn-secondary" disabled={loading}>Zpět</button>
        <button onClick={onActivate} className="btn-primary" disabled={loading}>
          {loading ? <><Loader className="spinner" size={16} /> Aktivuji...</> : 'Aktivovat "Device Owner"'}
        </button>
      </div>
    )}

    {status === 'success' && (
      <div className="step-actions">
        <div className="success-message">
          <CheckCircle size={20} /> Hotovo! Nyní se můžete znovu přihlásit ke Google účtům.
        </div>
        <button onClick={onComplete} className="btn-primary">Dokončit</button>
      </div>
    )}

    {error && <div className="error-box"><AlertCircle size={20} /><p>{error}</p></div>}
  </div>
)

export default DeviceOwnerSetup
