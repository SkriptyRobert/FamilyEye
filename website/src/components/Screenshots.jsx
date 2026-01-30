import React, { useState, useRef, useEffect } from 'react'
import LoginPreview from './LoginPreview'
import './Screenshots.css'

/**
 * Flow: instalace -> dashboard -> pravidla -> statistiky -> Smart Shield -> parovani -> prihlaseni -> stazeni.
 * Pro video: mediaType: 'video', videoSrc: '/images/demo.mp4'. GIF pouzijte jako obycejny obrazek (src: '.gif').
 */
const screenshots = [
  {
    id: 'instalace',
    src: '/images/installation_page.png',
    alt: 'Instalace serveru a agentů',
    title: 'Instalace (Win / Android)',
    desc: 'Jednoduchá instalace serveru a agentů na Windows a Android. One-click nebo Docker.',
    useLoginFallback: false,
    mediaType: 'image',
  },
  {
    id: 'dashboard',
    src: '/images/dashboard.png',
    alt: 'FamilyEye dashboard',
    title: 'Dashboard',
    desc: 'Přehled zařízení, stav rodiny, čas u obrazovky a rychlé akce.',
    useLoginFallback: false,
    mediaType: 'image',
  },
  {
    id: 'pravidla',
    src: '/images/rules.png',
    alt: 'Pravidla a limity',
    fallbackSrc: '/images/dashboard.png',
    title: 'Pravidla',
    desc: 'Časové limity, rozvrhy a pravidla pro aplikace a zařízení.',
    useLoginFallback: false,
    mediaType: 'image',
  },
  {
    id: 'statistiky',
    src: '/images/statistics.png',
    alt: 'Statistiky používání',
    fallbackSrc: '/images/dashboard.png',
    title: 'Statistiky',
    desc: 'Grafy a reporty o používání aplikací a času u obrazovky.',
    useLoginFallback: false,
    mediaType: 'image',
  },
  {
    id: 'smart-shield',
    src: '/images/smart_shield.png',
    alt: 'Smart Shield – detekce obsahu',
    fallbackSrc: '/images/dashboard.png',
    title: 'Smart Shield',
    desc: 'Detekce rizikového obsahu v reálném čase a důkazní snímky.',
    useLoginFallback: false,
    mediaType: 'image',
  },
  {
    id: 'parovani',
    src: '/images/pairing_screen.png',
    alt: 'Párování zařízení',
    title: 'Párování',
    desc: 'Připojení nového zařízení přes QR kód nebo manuální vstup.',
    useLoginFallback: false,
    mediaType: 'image',
  },
  {
    id: 'prihlaseni',
    src: '/images/login.png',
    alt: 'Přihlášení do FamilyEye',
    title: 'Přihlášení',
    desc: 'E-mail a heslo; dashboard v prohlížeči odkudkoliv.',
    useLoginFallback: true,
    mediaType: 'image',
  },
  {
    id: 'stazeni',
    src: '/images/downloads_section.png',
    alt: 'Stažení',
    title: 'Stažení',
    desc: 'Agent pro Windows a APK pro Android z releases.',
    useLoginFallback: false,
    mediaType: 'image',
  },
]

const CLOSE_DELAY_MS = 80

export default function Screenshots() {
  const [loginImageFailed, setLoginImageFailed] = useState(false)
  const [failedIds, setFailedIds] = useState(() => new Set())
  const [hovered, setHovered] = useState(null)
  const [activeIndex, setActiveIndex] = useState(0)
  const closeTimer = useRef(null)
  const scrollRef = useRef(null)

  const getSrc = (s) => (s.fallbackSrc && failedIds.has(s.id) ? s.fallbackSrc : s.src)
  const onImageError = (s) => {
    if (s.useLoginFallback) setLoginImageFailed(true)
    if (s.fallbackSrc) setFailedIds((prev) => new Set(prev).add(s.id))
  }

  const showZoom = (s) => !(s.useLoginFallback && loginImageFailed)

  const scheduleClose = () => {
    closeTimer.current = setTimeout(() => setHovered(null), CLOSE_DELAY_MS)
  }
  const cancelClose = () => {
    if (closeTimer.current) clearTimeout(closeTimer.current)
    closeTimer.current = null
  }

  const scrollToIndex = (i) => {
    const el = scrollRef.current
    if (!el) return
    const card = el.querySelector(`[data-index="${i}"]`)
    if (card) card.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
    setActiveIndex(i)
  }

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const onScroll = () => {
      const scrollLeft = el.scrollLeft
      const cardWidth = el.querySelector('[data-index]')?.offsetWidth ?? 0
      const gap = 24
      const index = Math.round(scrollLeft / (cardWidth + gap))
      setActiveIndex(Math.min(index, screenshots.length - 1))
    }
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <section
      id="screenshots"
      className="screenshots"
      onMouseLeave={() => { cancelClose(); setHovered(null) }}
    >
      <div className="screenshots-inner">
        <h2 className="screenshots-title">FamilyEye v praxi</h2>
        <p className="screenshots-intro">
          Kompletní flow: instalace agentů, dashboard, pravidla, statistiky a Smart Shield. Swipe nebo bubliny pro přepnutí. Najetí myší zobrazí větší detail.
        </p>

        <div
          ref={scrollRef}
          className="screenshots-carousel"
          role="region"
          aria-label="Náhledy obrazovek"
        >
          {screenshots.map((s, i) => (
            <figure
              key={s.id}
              data-index={i}
              className="screenshot-card"
              onMouseEnter={() => setHovered(
                showZoom(s) ? { ...s, src: getSrc(s), fallback: false } : { title: s.title, fallback: true }
              )}
            >
              <div className="screenshot-img-wrap">
                {s.useLoginFallback && loginImageFailed ? (
                  <LoginPreview />
                ) : s.mediaType === 'video' && s.videoSrc ? (
                  <video
                    src={s.videoSrc}
                    poster={s.src}
                    className="screenshot-img"
                    muted
                    loop
                    playsInline
                    preload="metadata"
                  />
                ) : (
                  <img
                    src={getSrc(s)}
                    alt={s.alt}
                    className="screenshot-img"
                    loading="lazy"
                    onError={() => onImageError(s)}
                  />
                )}
              </div>
              <figcaption className="screenshot-caption">
                <strong>{s.title}</strong>
                <span>{s.desc}</span>
              </figcaption>
            </figure>
          ))}
        </div>

        <div className="screenshots-dots" role="tablist" aria-label="Výběr sekce">
          {screenshots.map((s, i) => (
            <button
              key={s.id}
              type="button"
              role="tab"
              aria-selected={activeIndex === i}
              aria-label={`${s.title}, sekce ${i + 1} z ${screenshots.length}`}
              className={`screenshot-dot ${activeIndex === i ? 'active' : ''}`}
              onClick={() => scrollToIndex(i)}
            />
          ))}
        </div>
      </div>

      {hovered && (
        <div
          className="screenshot-zoom-panel"
          role="dialog"
          aria-label={`Náhled: ${hovered.title}`}
          onMouseEnter={cancelClose}
          onMouseLeave={() => setHovered(null)}
        >
          <div className="screenshot-zoom-frame">
            {hovered.fallback ? (
              <LoginPreview />
            ) : hovered.mediaType === 'video' && hovered.videoSrc ? (
              <video
                src={hovered.videoSrc}
                poster={hovered.src}
                className="screenshot-zoom-img"
                muted
                loop
                playsInline
                autoPlay
              />
            ) : (
              <img src={hovered.src} alt={hovered.alt} className="screenshot-zoom-img" />
            )}
          </div>
          <p className="screenshot-zoom-title">{hovered.title}</p>
        </div>
      )}
    </section>
  )
}
