import React, { lazy, Suspense } from 'react'
import DisclaimerBar from './components/DisclaimerBar'
import Hero from './components/Hero'
import Footer from './components/Footer'

const Features = lazy(() => import('./components/Features'))
const DashboardPreview = lazy(() => import('./components/DashboardPreview'))
const Screenshots = lazy(() => import('./components/Screenshots'))
const CTA = lazy(() => import('./components/CTA'))
const Contributors = lazy(() => import('./components/Contributors'))

function App() {
  return (
    <>
      <DisclaimerBar />
      <Hero />
      <Suspense fallback={<div style={{ minHeight: '40vh' }} />}>
        <Features />
        <DashboardPreview />
        <Screenshots />
        <CTA />
        <Contributors />
      </Suspense>
      <Footer />
    </>
  )
}


export default App
