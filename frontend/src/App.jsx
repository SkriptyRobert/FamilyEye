import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Login from './components/Login'
import Dashboard from './components/Dashboard'
import InitialSetup from './components/InitialSetup'
import { getToken } from './utils/auth'
import './App.css'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!getToken())
  const [needsSetup, setNeedsSetup] = useState(false)
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode')
    return saved !== null ? saved === 'true' : true // Default to dark mode
  })

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('darkMode', darkMode.toString())
  }, [darkMode])

  useEffect(() => {
    // Check if setup is needed (no token and no backend configured)
    if (!getToken()) {
      const backendUrl = localStorage.getItem('parental_control_backend_url')
      if (!backendUrl) {
        setNeedsSetup(true)
      }
    }
  }, [])

  const handleSetupComplete = () => {
    setIsAuthenticated(true)
    setNeedsSetup(false)
  }

  return (
    <Router>
      <div className={`App ${darkMode ? 'dark' : ''}`}>
        <Routes>
          {needsSetup ? (
            <Route
              path="*"
              element={<InitialSetup onComplete={handleSetupComplete} />}
            />
          ) : (
            <>
              <Route
                path="/login"
                element={
                  isAuthenticated ? (
                    <Navigate to="/" replace />
                  ) : (
                    <Login onLogin={() => setIsAuthenticated(true)} darkMode={darkMode} setDarkMode={setDarkMode} />
                  )
                }
              />
              <Route
                path="/"
                element={
                  isAuthenticated ? (
                    <Dashboard onLogout={() => setIsAuthenticated(false)} darkMode={darkMode} setDarkMode={setDarkMode} />
                  ) : (
                    <Navigate to="/login" replace />
                  )
                }
              />
            </>
          )}
        </Routes>
      </div>
    </Router>
  )
}

export default App

