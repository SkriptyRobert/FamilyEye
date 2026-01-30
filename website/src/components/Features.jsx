import React from 'react'
import { Shield, Globe, Lock, Clock, Zap, BarChart3 } from 'lucide-react'
import './Features.css'

const features = [
  {
    icon: Shield,
    title: 'Smart Shield detekce slov',
    paragraphs: [
      'Nečekejte na problém, předcházejte mu. Elimujte pedofily, drogy, násilí a další nebezpečné aktivity!',
      'Smart Shield – analyzuje obsah obrazovky v reálném čase. Detekce nebezpečných slov včetně vložení vlastních klíčových slov do kategorií, při zachycení se okamžitě pořídí důkazní snímek.',
      'Funguje v jakékoliv aplikaci, nejen v prohlížeči.',
    ],
  },
  {
    icon: BarChart3,
    title: 'Reporty a ochrana před obcházením',
    paragraphs: [
      'Grafy o používání aplikací. Agenti nahrávají aktivitu i offline a po připojení vše synchronizují.',
      'Anti-tamper: dítě nemůže agenta jen tak odinstalovat nebo vypnout (Device Admin / Device Owner mód).',
    ],
  },
  {
    icon: Globe,
    title: 'Žádné zbytečné aplikace pro rodiče',
    paragraphs: [
      'Váš telefon zůstane čistý. Pro správu rodiny nepotřebujete instalovat žádnou další aplikaci.',
      'Plně responzivní webový dashboard funguje na mobilu, tabletu i počítači. Stačí otevřít prohlížeč – žádné otravné aktualizace „rodičovské aplikace“.',
    ],
  },
  {
    icon: Lock,
    title: 'Vaše data zůstávají u vás',
    paragraphs: [
      'Self-hosted řešení: celý systém běží na vašem vlastním hardware. Vaše data neputují na cizí servery. Žádné sledování – vše zůstává doma.',
      'Šifrovaný provoz jako standard.',
    ],
  },
  {
    icon: Zap,
    title: 'Vzdálená správa v reálném čase',
    paragraphs: [
      'Potřebujete okamžitou pozornost? Uzamkněte zařízení dítěte Windows/Android na jedno kliknutí z mobilu.',
      'Webový filtr a vynucení bezpečného vyhledávání pro Windows.',
    ],
  },
  {
    icon: Clock,
    title: 'Limity času a rozvrhy',
    paragraphs: [
      'Flexibilní rozvrhy – nastavte přesně, kdy se smí hrát a kdy je „večerka“.',
      'Dávkování zábavy: denní limity pro konkrétní aplikace nebo celé kategorie.',
    ],
  },
]

export default function Features() {
  return (
    <section id="features" className="features">
      <div className="features-inner">
        <h2 className="features-title">Co FamilyEye nabízí</h2>
        <p className="features-intro">
          Technický nástroj pro rodiče, kteří chtějí self-hosted kontrolu a přehled nad zařízeními. Níže přehled hlavních funkcí.
        </p>
        <div className="features-grid">
          {features.map((f) => (
            <article key={f.title} className="feature-card">
              <div className="feature-icon">
                <f.icon size={28} strokeWidth={1.8} />
              </div>
              <h3 className="feature-title">{f.title}</h3>
              <div className="feature-desc">
                {f.paragraphs.map((para, i) => (
                  <p key={i}>{para}</p>
                ))}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
