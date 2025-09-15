import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import PromptScreen from './screens/PromptScreen.jsx';
import DrawScreen from './screens/DrawScreen.jsx';
import ScanScreen from './screens/ScanScreen.jsx';
import TalkScreen from './screens/TalkScreen.jsx';
import EndScreen from './screens/EndScreen.jsx';

function App() {
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

export default App;
