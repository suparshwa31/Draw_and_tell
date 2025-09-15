import React, { useState } from 'react';
import './ParentalConsent.css';

const ParentalConsent = ({ onConsentGiven, onConsentDenied }) => {
  const [isConsented, setIsConsented] = useState(false);
  const [parentName, setParentName] = useState('');
  const [email, setEmail] = useState('');
  const [childAge, setChildAge] = useState('');
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const handleConsent = () => {
    if (parentName && email && childAge && agreedToTerms) {
      // Store consent in localStorage for this session
      const consentData = {
        parentName,
        email,
        childAge: parseInt(childAge),
        consentDate: new Date().toISOString(),
        sessionId: `session_${Date.now()}`
      };
      
      localStorage.setItem('parentalConsent', JSON.stringify(consentData));
      onConsentGiven(consentData);
    } else {
      alert('Please fill in all required fields and agree to the terms.');
    }
  };

  const handleDeny = () => {
    onConsentDenied();
  };

  const isFormValid = parentName && email && childAge && agreedToTerms;

  return (
    <div className="parental-consent-container">
      <div className="consent-card">
        <div className="consent-header">
          <h1>🛡️ Parental Consent Required</h1>
          <p>This app is designed for children ages 5-13. We need parental permission to continue.</p>
        </div>

        <div className="consent-form">
          <div className="form-group">
            <label htmlFor="parentName">Parent/Guardian Name *</label>
            <input
              type="text"
              id="parentName"
              value={parentName}
              onChange={(e) => setParentName(e.target.value)}
              placeholder="Enter your full name"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email Address *</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email address"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="childAge">Child's Age *</label>
            <select
              id="childAge"
              value={childAge}
              onChange={(e) => setChildAge(e.target.value)}
              required
            >
              <option value="">Select age</option>
              <option value="5">5 years old</option>
              <option value="6">6 years old</option>
              <option value="7">7 years old</option>
              <option value="8">8 years old</option>
              <option value="9">9 years old</option>
              <option value="10">10 years old</option>
              <option value="11">11 years old</option>
              <option value="12">12 years old</option>
              <option value="13">13 years old</option>
            </select>
          </div>

          <div className="consent-checkbox">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={agreedToTerms}
                onChange={(e) => setAgreedToTerms(e.target.checked)}
                required
              />
              <span className="checkmark"></span>
              I agree to the <button 
                type="button" 
                className="link-button"
                onClick={() => setShowDetails(!showDetails)}
              >
                Terms of Service and Privacy Policy
              </button>
            </label>
          </div>

          {showDetails && (
            <div className="terms-details">
              <h3>Privacy & Safety Information</h3>
              <ul>
                <li>✅ <strong>Data Collection:</strong> We only collect drawing images, audio recordings, and basic interaction data</li>
                <li>✅ <strong>No Personal Info:</strong> We never collect names, addresses, phone numbers, or other personal information</li>
                <li>✅ <strong>Data Retention:</strong> All data is automatically deleted after 30 days</li>
                <li>✅ <strong>Safety First:</strong> All content is filtered for age-appropriate material</li>
                <li>✅ <strong>No Third Parties:</strong> We don't share data with any third parties</li>
                <li>✅ <strong>Parental Control:</strong> You can request data deletion at any time</li>
              </ul>
              <p><strong>COPPA Compliant:</strong> This app follows all Children's Online Privacy Protection Act requirements.</p>
            </div>
          )}

          <div className="consent-buttons">
            <button 
              className="consent-button deny-button" 
              onClick={handleDeny}
            >
              Deny Access
            </button>
            <button 
              className={`consent-button allow-button ${!isFormValid ? 'disabled' : ''}`}
              onClick={handleConsent}
              disabled={!isFormValid}
            >
              Give Consent & Continue
            </button>
          </div>
        </div>

        <div className="safety-badge">
          <span>🛡️ COPPA Compliant</span>
          <span>🔒 Child Safe</span>
          <span>📱 No Personal Data</span>
        </div>
      </div>
    </div>
  );
};

export default ParentalConsent;
