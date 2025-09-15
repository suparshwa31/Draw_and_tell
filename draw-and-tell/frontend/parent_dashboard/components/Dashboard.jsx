import React, { useEffect, useState } from 'react';
import { fetchSessions, fetchSession, fetchRecap, imageUrl } from '../services/api';

export default function Dashboard() {
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [session, setSession] = useState(null);
  const [recap, setRecap] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchSessions();
        setSessions(data);
        if (data.length > 0) {
          setSelectedSessionId(data[0].id);
        }
      } catch (e) {
        setError(e.message);
      }
    })();
  }, []);

  useEffect(() => {
    if (!selectedSessionId) return;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const [sessionData, recapData] = await Promise.all([
          fetchSession(selectedSessionId),
          fetchRecap(selectedSessionId)
        ]);
        setSession(sessionData);
        setRecap(recapData);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [selectedSessionId]);

  if (loading) return <div>Loading...</div>;

  return (
    <div style={{ padding: 20, fontFamily: 'Arial, sans-serif' }}>
      <h1 style={{ marginBottom: 20, color: '#1f2937' }}>Parent Dashboard</h1>
      
      {error && <div style={{ color: '#b00020', marginBottom: 12 }}>Error: {error}</div>}

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
        <label style={{ fontWeight: 600 }}>Select Session:</label>
        <select
          value={selectedSessionId || ''}
          onChange={(e) => setSelectedSessionId(parseInt(e.target.value))}
          style={{
            padding: '8px 12px',
            border: '1px solid #d1d5db',
            borderRadius: '6px',
            fontSize: '14px'
          }}
        >
          {sessions.map(session => (
            <option key={session.id} value={session.id}>
              Session {session.id} - {new Date(session.timestamp).toLocaleDateString()}
            </option>
          ))}
        </select>
      </div>

      {session && (
        <div style={{ display: 'grid', gap: 20 }}>
          {/* Session Info */}
          <div style={{ 
            background: '#f9fafb', 
            padding: 16, 
            borderRadius: '8px',
            border: '1px solid #e5e7eb'
          }}>
            <h2 style={{ margin: '0 0 12px 0', color: '#374151' }}>Session Details</h2>
            <p><strong>Prompt:</strong> {session.prompt}</p>
            <p><strong>Date:</strong> {new Date(session.timestamp).toLocaleString()}</p>
            <p><strong>Drawings:</strong> {session.drawings?.length || 0}</p>
          </div>

          {/* Drawings */}
          {session.drawings && session.drawings.length > 0 && (
            <div style={{ 
              background: '#f9fafb', 
              padding: 16, 
              borderRadius: '8px',
              border: '1px solid #e5e7eb'
            }}>
              <h2 style={{ margin: '0 0 16px 0', color: '#374151' }}>Drawings</h2>
              <div style={{ display: 'grid', gap: 16 }}>
                {session.drawings.map((drawing, index) => (
                  <div key={drawing.id} style={{ 
                    display: 'flex', 
                    gap: 16, 
                    alignItems: 'flex-start',
                    padding: 12,
                    background: 'white',
                    borderRadius: '6px',
                    border: '1px solid #e5e7eb'
                  }}>
                    <img 
                      src={imageUrl(drawing.id)} 
                      alt={`Drawing ${index + 1}`}
                      style={{ 
                        width: 120, 
                        height: 120, 
                        objectFit: 'cover',
                        borderRadius: '4px',
                        border: '1px solid #d1d5db'
                      }}
                    />
                    <div style={{ flex: 1 }}>
                      <h3 style={{ margin: '0 0 8px 0', color: '#374151' }}>
                        Drawing {index + 1}
                      </h3>
                      <p><strong>Caption:</strong> {drawing.caption}</p>
                      {drawing.tags && drawing.tags.length > 0 && (
                        <div style={{ marginTop: 8 }}>
                          <strong>Tags:</strong>
                          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                            {drawing.tags.map((tag, tagIndex) => (
                              <span 
                                key={tagIndex}
                                style={{
                                  background: '#dbeafe',
                                  color: '#1e40af',
                                  padding: '2px 8px',
                                  borderRadius: '12px',
                                  fontSize: '12px'
                                }}
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recap Report */}
          {recap && (
            <div style={{ 
              background: '#f9fafb', 
              padding: 16, 
              borderRadius: '8px',
              border: '1px solid #e5e7eb'
            }}>
              <h2 style={{ margin: '0 0 16px 0', color: '#374151' }}>Recap Report</h2>
              
              {recap.skills && recap.skills.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <h3 style={{ margin: '0 0 8px 0', color: '#4b5563' }}>Skills Practiced:</h3>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {recap.skills.map((skill, index) => (
                      <span 
                        key={index}
                        style={{
                          background: '#dcfce7',
                          color: '#166534',
                          padding: '4px 12px',
                          borderRadius: '16px',
                          fontSize: '14px',
                          fontWeight: 500
                        }}
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {recap.highlights && (
                <div>
                  <h3 style={{ margin: '0 0 8px 0', color: '#4b5563' }}>Summary:</h3>
                  <p style={{ margin: 0, lineHeight: 1.6, color: '#374151' }}>
                    {recap.highlights}
                  </p>
                </div>
              )}

              {recap.top_tags && recap.top_tags.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <h3 style={{ margin: '0 0 8px 0', color: '#4b5563' }}>Key Themes:</h3>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {recap.top_tags.map((tag, index) => (
                      <span 
                        key={index}
                        style={{
                          background: '#e0e7ff',
                          color: '#3730a3',
                          padding: '3px 10px',
                          borderRadius: '12px',
                          fontSize: '12px',
                          fontWeight: 500
                        }}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {recap.num_drawings && (
                <div style={{ marginTop: 16, padding: 12, background: '#f0f9ff', borderRadius: '6px', border: '1px solid #bae6fd' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: '24px' }}>🎨</span>
                    <div>
                      <div style={{ fontWeight: 600, color: '#0c4a6e' }}>
                        {recap.num_drawings} Drawing{recap.num_drawings > 1 ? 's' : ''} Created
                      </div>
                      <div style={{ fontSize: '14px', color: '#0369a1' }}>
                        {recap.prompt && `Prompt: "${recap.prompt}"`}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}