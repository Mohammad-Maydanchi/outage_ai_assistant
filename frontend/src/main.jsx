import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './styles.css'

// Find the empty <div id="root"> in index.html and draw our App inside it.
createRoot(document.getElementById('root')).render(<App />)
