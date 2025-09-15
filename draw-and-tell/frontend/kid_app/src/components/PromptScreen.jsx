import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/PromptScreen.css';

const API_BASE_URL = 'http://localhost:8000';

const PromptScreen = () => {
  const [prompt, setPrompt] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const getPrompt = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/prompt`);
      if (!response.ok) {
        throw new Error('Failed to get prompt');
      }
      const data = await response.json();
      setPrompt(data.prompt);
    } catch (err) {
      setError('Oops! Could not get a prompt. Please try again.');
      console.error('Error fetching prompt:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStart = () => {
    if (prompt) {
      navigate('/draw', { state: { prompt } });
    }
  };

  if (isLoading) {
    return (
      <div className="prompt-screen">
        <div className="loading">
          <h2>Getting your creative prompt ready...</h2>
          <div className="loading-spinner"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="prompt-screen">
        <div className="error">
          <h2>{error}</h2>
          <button onClick={getPrompt}>Try again</button>
        </div>
      </div>
    );
  }

  return (
    <div className="prompt-screen">
      <h1>{prompt || "Click the button to get your drawing prompt!"}</h1>
      <div className="button-container">
        {prompt ? (
          <>
            <button className="start-button" onClick={handleStart}>
              Start Drawing!
            </button>
            <button className="new-prompt-button" onClick={getPrompt}>
              Get a new prompt
            </button>
          </>
        ) : (
          <button className="new-prompt-button" onClick={getPrompt}>
            Get started!
          </button>
        )}
      </div>
    </div>
  );
};

export default PromptScreen;
