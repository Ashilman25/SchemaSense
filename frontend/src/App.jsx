import React from 'react'
import AppLayout from './components/layout/AppLayout'
import { ThemeProvider } from './context/ThemeContext'

function App() {
  return (
    <ThemeProvider>
      <AppLayout />
    </ThemeProvider>
  )
}

export default App
