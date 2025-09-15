import React from 'react';
import { useNavigate } from 'react-router-dom';

function ScanScreen() {
  const navigate = useNavigate();
  return (
    <div>
      <h1>Scan</h1>
      <button onClick={() => navigate('/talk')}>Talk</button>
    </div>
  );
}
export default ScanScreen;
