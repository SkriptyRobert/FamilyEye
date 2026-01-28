import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Login from './components/auth/Login'
import Dashboard from './components/Dashboard'
import InitialSetup from './components/setup/InitialSetup'
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
    // Check if we are connected to a backend
    const checkStatus = async () => {
      // If we have a token, we are good
      if (getToken()) {
        setIsAuthenticated(true)
        return
      }

      // If no token, default to Login. 
      // The installer creates the admin, so "Initial Setup" is rarely needed 
      // unless it's a manual install.
      // We can check if any users exist, but for now, let's assume Login is the primary entry.
      setNeedsSetup(false)
    }

    checkStatus()
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

