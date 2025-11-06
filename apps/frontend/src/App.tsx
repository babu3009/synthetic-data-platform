import { Routes, Route } from 'react-router-dom'

import Navbar from './components/Navbar'
import HomePage from './pages/HomePage'
import WizardPage from './pages/WizardPage'
import './App.css'

function App() {
  return (
    <div className="App">
      <Navbar />
      <main className="container-fluid px-0">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/wizard" element={<WizardPage />} />
          {/* Add more routes as needed */}
        </Routes>
      </main>
    </div>
  )
}

export default App