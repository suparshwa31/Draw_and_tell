import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/global.css';
import '../styles/PromptScreen.css';

function PromptScreen() {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPrompt();
  }, []);

  const fetchPrompt = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await fetch('http://localhost:8000/prompt');
      if (!response.ok) {
        throw new Error('Failed to fetch prompt');
      }
      const data = await response.json();
      setPrompt(data.prompt);
    } catch (err) {
      setError('Oops! Could not get your drawing idea. Try again?');
      console.error('Error fetching prompt:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = () => {
    fetchPrompt();
  };

  const handleStart = () => {
    if (prompt) {
      navigate('/draw', { state: { prompt } });
    }
  };

  return (
    <div className="screen-container prompt-screen">
      {isLoading ? (
        <div className="loading">
          <h2>Getting a fun drawing idea... 🎨</h2>
          <div className="loading-spinner"></div>
        </div>
      ) : error ? (
        <div className="error">
          <h2>{error}</h2>
          <button onClick={handleRetry}>Try Again</button>
        </div>
      ) : (
        <>
          <h1>{prompt}</h1>
          <div className="button-container">
            <button onClick={handleRetry} className="new-prompt-button">
              Get Another Idea ✨
            </button>
            <button onClick={handleStart} className="start-button">
              Start Drawing! 🎨
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default PromptScreen;
