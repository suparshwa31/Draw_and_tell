import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import '../styles/global.css';
import '../styles/TalkScreen.css';

const API_BASE_URL = 'http://localhost:8000';

function TalkScreen() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isRecording, setIsRecording] = useState(false);
  const [recordedChunks, setRecordedChunks] = useState([]);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [question, setQuestion] = useState(null);
  const [questionAudio, setQuestionAudio] = useState(null);
  const [hasRecording, setHasRecording] = useState(false);
  const [response, setResponse] = useState(null);
  const [responseAudio, setResponseAudio] = useState(null);
  const [showResponse, setShowResponse] = useState(false);
  const [questionAudioPlayed, setQuestionAudioPlayed] = useState(false);
  const audioRef = React.useRef(null);
  const responseAudioRef = React.useRef(null);

  useEffect(() => {
    getQuestion();
    
    return () => {
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
      }
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
    };
  }, [mediaRecorder]);

  // Play the question audio when it's available (only once)
  useEffect(() => {
    if (questionAudio && audioRef.current && !questionAudioPlayed) {
      console.log('Setting up audio playback...'); // Debug log
      
      const playAudio = async () => {
        try {
          // Reset audio element
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
          
          // Set up event listeners for debugging
          const audio = audioRef.current;
          
          // Remove any existing listeners
          audio.onloadeddata = null;
          audio.onerror = null;
          audio.onplay = null;
          audio.onended = null;
          
          // Add new listeners
          audio.onloadeddata = () => console.log('Audio loaded successfully');
          audio.onerror = (e) => {
            console.error('Audio loading error:', e);
            console.error('Audio error code:', audio.error?.code);
            console.error('Audio error message:', audio.error?.message);
          };
          audio.onplay = () => {
            console.log('Audio started playing');
            setQuestionAudioPlayed(true); // Mark as played when it starts
          };
          audio.onended = () => console.log('Audio finished playing');
          
          // Set MIME type and source
          audio.type = 'audio/wav';
          audio.src = questionAudio;
          
          // Wait for audio to be loaded
          await new Promise((resolve, reject) => {
            audio.oncanplaythrough = resolve;
            audio.onerror = reject;
          });
          
          // Play the audio
          await audio.play();
          console.log('Audio playback started successfully');
          
        } catch (error) {
          console.error('Error in audio playback:', error);
          setError('Unable to play the question audio. Please try again.');
        }
      };
      
      playAudio();
    }
  }, [questionAudio, questionAudioPlayed]);

  // Play the response audio when it's available
  useEffect(() => {
    if (responseAudio && responseAudioRef.current) {
      const playResponseAudio = async () => {
        try {
          const audio = responseAudioRef.current;
          audio.src = responseAudio;
          await audio.play();
        } catch (error) {
          console.error('Error playing response audio:', error);
        }
      };
      
      playResponseAudio();
    }
  }, [responseAudio]);

  const getQuestion = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Get question and audio from location state (passed from DrawScreen)
      const { question: generatedQuestion, questionAudio: audioData } = location.state || {};
      if (!generatedQuestion) {
        throw new Error('No question found. Please try again.');
      }

      setQuestion(generatedQuestion);
      console.log('Question received in TalkScreen:', generatedQuestion);
      
      // Convert base64 audio data to blob URL if available
      if (audioData) {
        try {
          // Convert base64 to binary
          const binaryString = atob(audioData);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          const audioBlob = new Blob([bytes], { type: 'audio/wav' });
          const audioUrl = URL.createObjectURL(audioBlob);
          setQuestionAudio(audioUrl);
        } catch (error) {
          console.error('Error converting audio data:', error);
        }
      }
      
      setIsLoading(false);
    } catch (err) {
      setError('Oops! Something went wrong. Please try again.');
      console.error('Error getting question:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          setRecordedChunks((chunks) => [...chunks, e.data]);
        }
      };

      recorder.onstop = () => {
        // Stop all audio tracks
        stream.getTracks().forEach(track => track.stop());
        setHasRecording(true);
      };

      setMediaRecorder(recorder);
      recorder.start();
      setIsRecording(true);
      setHasRecording(false);
    } catch (err) {
      setError('Could not access microphone. Please check permissions.');
      console.error('Error accessing microphone:', err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const handleTalkClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const handleFinish = async () => {
    try {
      setIsLoading(true);
      setError(null);

      if (!hasRecording) {
        navigate('/end');
        return;
      }

      const audioBlob = new Blob(recordedChunks, { type: 'audio/webm' });
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      // Get drawing_id and question_id from location.state or wherever they are stored
      const { drawingId, questionId } = location.state || {};
      if (!drawingId || !questionId || drawingId === 0 || questionId === 0) {
        setError('Missing drawing or question ID.');
        console.error('Missing IDs:', { drawingId, questionId, locationState: location.state });
        return;
      }

      // Convert string IDs to integers as expected by backend
      formData.append('drawing_id', parseInt(drawingId));
      formData.append('question_id', parseInt(questionId));

      const response = await fetch(`${API_BASE_URL}/transcribe-answer`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Failed to process recording');
      }

      const result = await response.json();
      console.log('Transcription result:', result);
      
      // Handle response and response audio
      if (result.response) {
        setResponse(result.response);
        setShowResponse(true);
        
        // Convert base64 response audio to blob URL if available
        if (result.responseAudio) {
          try {
            // Convert base64 to binary
            const binaryString = atob(result.responseAudio);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i);
            }
            const audioBlob = new Blob([bytes], { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(audioBlob);
            setResponseAudio(audioUrl);
          } catch (error) {
            console.error('Error converting response audio data:', error);
          }
        }
      } else {
        // No response generated, navigate to end screen
        navigate('/end');
      }
    } catch (err) {
      setError('Could not save your recording. Try again!');
      console.error('Error saving recording:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleContinue = () => {
    navigate('/end');
  };

  return (
    <div className="screen-container talk-screen">
      <h1>Great job! You did it!</h1>
      
      {isLoading ? (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Way to go, champ!</p>
        </div>
      ) : error ? (
        <div className="error-message">
          {error}
          <button onClick={getQuestion} className="retry-button">
            Try Again
          </button>
        </div>
      ) : (
        <>
          <div className="content-container">
            <audio ref={audioRef} style={{ display: 'none' }} />
            <audio ref={responseAudioRef} style={{ display: 'none' }} />
            <div className="drawing-container">
              {location.state?.capturedImage && (
                <img 
                  src={location.state.capturedImage} 
                  alt="Your drawing" 
                  className="drawing-preview"
                />
              )}
            </div>

            <div className="interaction-container">
              {!showResponse ? (
                <>
                  <div className={`question-bubble ${isRecording ? 'emphasis' : ''}`}>
                    {question || "Tell me about what you drew!"}
                  </div>

                  <div className="controls-container">
                    <button 
                      className={`talk-button ${isRecording ? 'recording' : ''} ${hasRecording ? 'recorded' : ''}`}
                      onClick={handleTalkClick}
                      disabled={isLoading}
                    >
                      {isLoading ? 'Processing...' :
                       isRecording ? '⏹️ Stop Recording' : 
                       hasRecording ? '🔄 Record Again' : '🎤 Answer'}
                    </button>

                    <button 
                      className={`finish-button ${hasRecording ? 'ready' : ''}`}
                      onClick={handleFinish}
                      disabled={isLoading}
                    >
                      {isLoading ? 'Saving...' : 'All Done! 🌟'}
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="response-bubble">
                    {response}
                  </div>

                  <div className="controls-container">
                    <button 
                      className="finish-button ready"
                      onClick={handleContinue}
                    >
                      Continue! 🌟
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default TalkScreen;
