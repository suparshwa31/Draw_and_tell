import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import PromptScreen from './screens/PromptScreen.jsx';
import DrawScreen from './screens/DrawScreen.jsx';
import ScanScreen from './screens/ScanScreen.jsx';
import TalkScreen from './screens/TalkScreen.jsx';
import EndScreen from './screens/EndScreen.jsx';
import ParentalConsent from './components/ParentalConsent.jsx';

function App() {
  const [hasConsent, setHasConsent] = useState(false);
  const [consentData, setConsentData] = useState(null);
  const [showConsent, setShowConsent] = useState(false);

  useEffect(() => {
    // Check if parental consent has been given
    const storedConsent = localStorage.getItem('parentalConsent');
    if (storedConsent) {
      try {
        const consent = JSON.parse(storedConsent);
        // Check if consent is still valid (within 30 days)
        const consentDate = new Date(consent.consentDate);
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        
        if (consentDate > thirtyDaysAgo) {
          setHasConsent(true);
          setConsentData(consent);
        } else {
          // Consent expired, remove it
          localStorage.removeItem('parentalConsent');
          setShowConsent(true);
        }
      } catch (error) {
        console.error('Error parsing consent data:', error);
        setShowConsent(true);
      }
    } else {
      setShowConsent(true);
    }
  }, []);

  const handleConsentGiven = (consent) => {
    setHasConsent(true);
    setConsentData(consent);
    setShowConsent(false);
  };

  const handleConsentDenied = () => {
    setHasConsent(false);
    setConsentData(null);
    setShowConsent(false);
    // Redirect to a "consent required" page or show a message
    alert('Parental consent is required to use this app. Please contact the administrator.');
  };

  // Show parental consent screen if needed
  if (showConsent) {
    return <ParentalConsent onConsentGiven={handleConsentGiven} onConsentDenied={handleConsentDenied} />;
  }

  // Show main app if consent is given
  if (hasConsent) {
    return (
      <Router>
        <Routes>
          <Route path="/" element={<PromptScreen />} />
          <Route path="/draw" element={<DrawScreen />} />
          <Route path="/scan" element={<ScanScreen />} />
          <Route path="/talk" element={<TalkScreen />} />
          <Route path="/end" element={<EndScreen />} />
        </Routes>
      </Router>
    );
  }

  // Show loading or consent required message
  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      height: '100vh',
      fontFamily: 'Arial, sans-serif',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    }}>
      <div style={{ 
        background: 'white', 
        padding: '40px', 
        borderRadius: '20px',
        textAlign: 'center',
        boxShadow: '0 20px 40px rgba(0,0,0,0.1)'
      }}>
        <h1>🛡️ Parental Consent Required</h1>
        <p>This app requires parental consent to continue.</p>
        <button 
          onClick={() => setShowConsent(true)}
          style={{
            background: '#667eea',
            color: 'white',
            border: 'none',
            padding: '12px 24px',
            borderRadius: '10px',
            fontSize: '16px',
            cursor: 'pointer',
            marginTop: '20px'
          }}
        >
          Continue to Consent Form
        </button>
      </div>
    </div>
  );
}

export default App;
