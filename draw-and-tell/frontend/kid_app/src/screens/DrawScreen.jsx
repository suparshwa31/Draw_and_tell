import React, { useState, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Webcam from 'react-webcam';
import '../styles/global.css';
import '../styles/DrawScreen.css';

const API_BASE_URL = 'http://localhost:8000';

function DrawScreen() {
  const navigate = useNavigate();
  const location = useLocation();
  const webcamRef = useRef(null);
  const [capturedImage, setCapturedImage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showCamera, setShowCamera] = useState(false);

  const capture = useCallback(() => {
    if (!webcamRef.current) return;
    
    try {
      // Capture image from webcam
      const imageSrc = webcamRef.current.getScreenshot();
      setCapturedImage(imageSrc);
      setShowCamera(false); // Hide camera after capture
      setError(null);
    } catch (err) {
      setError('Could not capture image. Please try again.');
      console.error('Error capturing image:', err);
    }
  }, [webcamRef]);

  const handleNext = async () => {
    if (!capturedImage) return;
    
    try {
      setIsLoading(true);
      setError(null);

      // Convert base64 to blob
      const base64Data = capturedImage.split(',')[1];
      const blob = await fetch(`data:image/jpeg;base64,${base64Data}`).then(res => res.blob());
      
      // Create form data
      const formData = new FormData();
      formData.append('image', blob, 'drawing.jpg');
      formData.append('prompt', location.state?.prompt || '');  // Add the drawing prompt

      // Send to backend for analysis
      const response = await fetch(`${API_BASE_URL}/analyze-drawing`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to analyze image');
      }

      // Get the analysis result with the question
      const analysisResult = await response.json();
      
      // Navigate to talk screen with the generated question
      navigate('/talk', { 
        state: { 
          ...location.state,
          capturedImage,
          question: analysisResult.question,
          drawingId: analysisResult.drawingId,  // Store drawing ID for answer submission
          questionId: analysisResult.questionId,  // Store question ID for answer submission
          questionAudio: analysisResult.questionAudio  // Store TTS audio for question
        } 
      });
    } catch (err) {
      setError('Could not analyze your drawing. Please try again.');
      console.error('Error analyzing image:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const retake = () => {
    setCapturedImage(null);
    setError(null);
    setShowCamera(true);
  };

  const startCamera = () => {
    setShowCamera(true);
    setError(null);
  };

  return (
    <div className="screen-container draw-screen">
      <h1>Time to Draw!</h1>
      <p className="instruction">When you're done drawing, take a picture of it!</p>
      
      <div className="camera-container">
        {capturedImage ? (
          <div className="captured-image-container">
            <img src={capturedImage} alt="Your drawing" />
            <div className="button-group">
              <button onClick={retake} className="retake-button">
                Take Another Picture
              </button>
            </div>
          </div>
        ) : showCamera ? (
          <div className="webcam-container">
            <Webcam
              ref={webcamRef}
              screenshotFormat="image/jpeg"
              mirrored={true}
              className="webcam"
            />
            <button
              onClick={capture}
              className="capture-button"
            >
              📸 Take Picture
            </button>
          </div>
        ) : (
          <button
            onClick={startCamera}
            className="start-camera-button"
          >
            📷 Start Camera
          </button>
        )}
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <button
        className="next-button"
        onClick={handleNext}
        disabled={!capturedImage || isLoading}
      >
        {isLoading ? 'Uploading...' : 'My Drawing is Ready!'}
      </button>
    </div>
  );
}

export default DrawScreen;
