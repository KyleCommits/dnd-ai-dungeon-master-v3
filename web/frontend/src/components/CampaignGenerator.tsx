// web/frontend/src/components/CampaignGenerator.tsx
import React, { useState, useEffect } from 'react';
import './CampaignGenerator.css';

interface GenerationStatus {
  session_id: string;
  status: string;
  current_stage: string;
  progress_percent: number;
  message: string;
  result?: {
    title: string;
    description: string;
    file_path: string;
    metadata: {
      line_count: number;
      word_count: number;
      generation_time: number;
    };
    content_preview: string;
  };
  error?: string;
}

interface CampaignGeneratorProps {
  onGenerationComplete: () => void;
}

const CampaignGenerator: React.FC<CampaignGeneratorProps> = ({ onGenerationComplete }) => {
  const [prompt, setPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<GenerationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Effect to call the completion callback
  useEffect(() => {
    if (status?.status === 'completed') {
      onGenerationComplete();
    }
  }, [status, onGenerationComplete]);

  const handleStartGeneration = async () => {
    if (!prompt.trim() || prompt.length < 10) {
      setError('Please provide a campaign prompt of at least 10 characters');
      return;
    }
    if (prompt.length > 1000) {
      setError('Campaign prompt must be less than 1000 characters');
      return;
    }
    setError(null);
    setIsGenerating(true);
    try {
      const response = await fetch('/api/campaigns/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt, user_preferences: {} }),
      });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const result = await response.json();
      setSessionId(result.session_id);
      startStatusPolling(result.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start generation');
      setIsGenerating(false);
    }
  };

  const startStatusPolling = (sessionId: string) => {
    const pollStatus = async () => {
      try {
        const response = await fetch(`/api/campaigns/status/${sessionId}`);
        if (!response.ok) throw new Error('Failed to get status');
        const statusData: GenerationStatus = await response.json();
        setStatus(statusData);
        if (statusData.status === 'in_progress' || statusData.status === 'starting') {
          setTimeout(pollStatus, 2000);
        } else {
          setIsGenerating(false);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to get status');
        setIsGenerating(false);
      }
    };
    pollStatus();
  };

  const handleReset = () => {
    setPrompt('');
    setIsGenerating(false);
    setSessionId(null);
    setStatus(null);
    setError(null);
  };

  return (
    <div className="campaign-generator">
      <div className="generator-header">
        <h2>Professional Campaign Generator</h2>
        <p className="generator-subtitle">
          Generate high-quality campaigns using a hybrid AI approach
        </p>
      </div>

      {!isGenerating && !status?.result ? (
        <div className="prompt-input-section">
          <div className="input-group">
            <label htmlFor="campaign-prompt">Campaign Concept</label>
            <textarea
              id="campaign-prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Describe your campaign idea..."
              rows={4}
              maxLength={1000}
            />
            <div className="character-count">{prompt.length}/1000 characters</div>
          </div>

          <div className="generation-info">
            <h3>How It Works:</h3>
            <div className="stage-info">
              <div className="stage">
                <span className="stage-number">1-2</span>
                <div className="stage-details">
                  <strong>AI Models (Outline)</strong>
                  <p>Campaign outline & plot structure</p>
                </div>
              </div>
              <div className="stage">
                <span className="stage-number">3-4</span>
                <div className="stage-details">
                  <strong>AI Models (Content)</strong>
                  <p>Detailed content generation</p>
                </div>
              </div>
              <div className="stage">
                <span className="stage-number">5</span>
                <div className="stage-details">
                  <strong>Local LLM (Polish)</strong>
                  <p>Final polishing and formatting</p>
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={handleStartGeneration}
            disabled={prompt.length < 10 || prompt.length > 1000}
            className="generate-button"
          >
            Generate Professional Campaign
          </button>
        </div>
      ) : null}

      {isGenerating || status ? (
        <div className="generation-status">
          {status ? (
            <>
              <div className="progress-header">
                <h3>{status.status === 'completed' ? 'Generation Complete!' : 'Generating Campaign...'}</h3>
                <div className="progress-bar-container">
                  <div
                    className="progress-bar"
                    style={{ width: `${status.progress_percent}%` }}
                  />
                  <span className="progress-text">{status.progress_percent}%</span>
                </div>
              </div>
              <div className="stage-info-current">
                <strong>Current Stage:</strong> {status.current_stage}
                <div className="status-message">{status.message}</div>
              </div>
              {status.status === 'completed' && status.result && (
                <div className="generation-result">
                  <h3>{status.result.title}</h3>
                  <p>{status.result.description}</p>
                  <strong>Saved to:</strong> {status.result.file_path}
                </div>
              )}
              {status.status === 'failed' && status.error && (
                <div className="generation-error">
                  <h3>Generation Failed</h3>
                  <p>{status.error}</p>
                </div>
              )}
            </>
          ) : (
            <div className="loading-state">
              <div className="loading-spinner" />
              <p>Starting campaign generation...</p>
            </div>
          )}
        </div>
      ) : null}

      {error && <div className="error-message"><strong>Error:</strong> {error}</div>}

      {(status?.status === 'completed' || status?.status === 'failed') && (
        <button onClick={handleReset} className="reset-button">
          Generate Another Campaign
        </button>
      )}
    </div>
  );
};

export default CampaignGenerator;
