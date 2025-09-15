import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/global.css';
import '../styles/EndScreen.css';

function EndScreen() {
  const navigate = useNavigate();
  return (
    <div className="screen-container end-screen">
      <h1>Great Job! 🎨</h1>
      <button className="restart-button" onClick={() => navigate('/')}>
        Draw Another Picture
      </button>
    </div>
  );
}
export default EndScreen;
