import React, { useState, useRef, useEffect } from 'react'
import LoginPreview from './LoginPreview'
import './Screenshots.css'

/**
 * Pole karet karuselu. Pro dual-detail (dva obrazky vedle sebe v zoomu) pridat sources: [url1, url2].
 * Pro video: mediaType: 'video', videoSrc: '/images/demo.mp4'.
 */
const screenshots = [
  {
    id: 'smart-shield',
    src: '/images/smart_shield_proof_1.png',
    sources: ['/images/smart_shield_proof_1.png', '/images/smart_shield_proof_2.png'],
    alt: 'Smart Shield – důkaz funkce',
    title: 'Smart Shield',
    desc: 'Detekce rizikového obsahu v reálném čase a důkazní snímky. Dva pohledy vedle sebe.',
    useLoginFallback: false,
    mediaType: 'image',
  },
  {
    id: 'instalace-android',
    src: '/images/installation_android.png',
    alt: 'Instalace Android – uvítací obrazovka',
    title: 'Instalace Android',
    desc: 'Průvodce nastavením: rodičovský PIN, oprávnění a aktivace monitoringu. Začít nastavení.',
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
    id: 'mobile-prehled',
    src: '/images/mobile-dashboard.png',
    alt: 'Přehled v mobilní aplikaci',
    title: 'Přehled (mobil)',
    desc: 'Tento týden, graf používání a aplikace – stejné údaje jako na webu.',
    useLoginFallback: false,
    mediaType: 'image',
  },
  {
    id: 'mobile-statistiky',
    src: '/images/mobile-stats.png',
    alt: 'Statistiky v mobilu',
    title: 'Statistiky (mobil)',
    desc: 'Celkový čas dnes, nejvíce používané aplikace a chytrý přehled anomálií.',
    useLoginFallback: false,
    mediaType: 'image',
  },
  {
    id: 'mobile-smart-shield',
    src: '/images/mobile-smart-shield.png',
    alt: 'Smart Shield v mobilní aplikaci',
    title: 'Smart Shield (mobil)',
    desc: 'Detekce rizikového obsahu a důkazy v reálném čase na telefonu.',
    useLoginFallback: false,
    mediaType: 'image',
  },
  {
    id: 'mobile-menu',
    src: '/images/mobile-menu.png',
    alt: 'Boční menu (hamburger) v mobilní aplikaci',
    fallbackSrc: '/images/mobile-smart-shield.png',
    title: 'Menu (mobil)',
    desc: 'Boční navigace – Přehled, Zařízení, Smart Shield, Pravidla, Statistiky, Přidat. Stejné sekce jako v aplikaci.',
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
    id: 'statistiky-prehled',
    src: '/images/statistics_overview.png',
    alt: 'Statistiky – přehled',
    title: 'Statistiky (přehled)',
    desc: 'Přehled času u obrazovky a aplikací podle zařízení. Celkový čas dnes a trendy.',
    useLoginFallback: false,
    mediaType: 'image',
  },
  {
    id: 'statistiky-detail',
    src: '/images/statistics_detail.png',
    alt: 'Statistiky – detail',
    title: 'Statistiky (detail)',
    desc: 'Detailní pohled na používání aplikací, časové úseky a reporty pro rodiče.',
    useLoginFallback: false,
    mediaType: 'image',
  },
  {
    id: 'parovani',
    src: '/images/pairing_1.png',
    sources: ['/images/pairing_1.png', '/images/pairing_2.png'],
    alt: 'Párování zařízení',
    title: 'Párování',
    desc: 'Připojení nového zařízení přes QR kód nebo manuální vstup. Dva pohledy vedle sebe.',
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
]

/** Rychlost plynulého posuvu v pixelech za sekundu (jako titulkový pás). */
const SCROLL_PX_PER_SEC = 55
const AUTO_SCROLL_TICK_MS = 50

export default function Screenshots() {
  const [loginImageFailed, setLoginImageFailed] = useState(false)
  const [failedIds, setFailedIds] = useState(() => new Set())
  const [hovered, setHovered] = useState(null)
  const [activeIndex, setActiveIndex] = useState(0)
  const [isPaused, setIsPaused] = useState(false)
  const scrollRef = useRef(null)
  const isPausedRef = useRef(false)
  isPausedRef.current = isPaused

  const getSrc = (s) => (s.fallbackSrc && failedIds.has(s.id) ? s.fallbackSrc : s.src)
  const onImageError = (s) => {
    if (s.useLoginFallback) setLoginImageFailed(true)
    if (s.fallbackSrc) setFailedIds((prev) => new Set(prev).add(s.id))
  }

  const showZoom = (s) => !(s.useLoginFallback && loginImageFailed)

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
      const maxScroll = el.scrollWidth - el.clientWidth
      if (maxScroll <= 0) {
        setActiveIndex(0)
        return
      }
      if (scrollLeft >= maxScroll - 2) {
        setActiveIndex(screenshots.length - 1)
        return
      }
      const firstCard = el.querySelector('[data-index="0"]')
      const gap = 24
      const cardWidth = firstCard?.offsetWidth ?? 0
      const index = Math.round(scrollLeft / (cardWidth + gap))
      setActiveIndex(Math.min(Math.max(0, index), screenshots.length - 1))
    }
    el.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => el.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const step = (SCROLL_PX_PER_SEC * AUTO_SCROLL_TICK_MS) / 1000
    const id = setInterval(() => {
      if (isPausedRef.current) return
      const maxScroll = el.scrollWidth - el.clientWidth
      if (maxScroll <= 0) return
      el.scrollLeft += step
      if (el.scrollLeft >= maxScroll - 1) el.scrollLeft = 0
    }, AUTO_SCROLL_TICK_MS)
    return () => clearInterval(id)
  }, [])

  return (
    <section
      id="screenshots"
      className="screenshots"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => { setHovered(null); setIsPaused(false) }}
      onClick={() => setIsPaused(true)}
    >
      <div className="screenshots-inner">
        <h2 className="screenshots-title">FamilyEye v praxi</h2>

        <div
          ref={scrollRef}
          className={`screenshots-carousel${!isPaused ? ' screenshots-carousel--auto-scroll' : ''}`}
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
          className={`screenshot-zoom-panel${hovered.sources?.length >= 2 ? ' screenshot-zoom-panel--multi' : ''}`}
          role="dialog"
          aria-label={`Náhled: ${hovered.title}`}
          onMouseLeave={() => setHovered(null)}
        >
          <div className={`screenshot-zoom-frame${hovered.sources?.length >= 2 ? ' screenshot-zoom-frame--multi' : ''}`}>
            {hovered.fallback ? (
              <LoginPreview />
            ) : hovered.sources?.length >= 2 ? (
              hovered.sources.map((url, idx) => (
                <div key={idx} className={`screenshot-zoom-multi-cell${idx === 0 ? ' screenshot-zoom-multi-cell--zoomed' : ''}`}>
                  <img src={url} alt={`${hovered.alt} ${idx + 1}`} className="screenshot-zoom-img" />
                </div>
              ))
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
