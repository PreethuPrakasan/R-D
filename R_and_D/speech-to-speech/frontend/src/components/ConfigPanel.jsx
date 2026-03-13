import React, { useState, useEffect } from 'react';
import { getConfig, updateConfig } from '../services/api';
import './ConfigPanel.css';

const ConfigPanel = ({ onConfigUpdate }) => {
  const [config, setConfig] = useState({
    agent_role: '',
    agent_description: '',
    tone: '',
    language: 'English'
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const data = await getConfig();
      setConfig(data);
    } catch (error) {
      console.error('Error loading config:', error);
      setMessage('Error loading configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setConfig(prev => ({ ...prev, [field]: value }));
    setMessage('');
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setMessage('');
      await updateConfig(config);
      setMessage('Configuration saved successfully!');
      if (onConfigUpdate) {
        onConfigUpdate(config);
      }
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Error saving config:', error);
      setMessage('Error saving configuration');
    } finally {
      setSaving(false);
    }
  };

  const loadPreset = (preset) => {
    const presets = {
      financial: {
        agent_role: 'Financial Advisor',
        agent_description: 'You are an expert financial advisor helping users plan investments, budgeting, and long-term wealth growth.',
        tone: 'Friendly, confident, and professional',
        language: 'English'
      },
      health: {
        agent_role: 'Health Assistant',
        agent_description: 'You are a knowledgeable health assistant providing general health information, wellness tips, and guidance on healthy living.',
        tone: 'Caring, empathetic, and informative',
        language: 'English'
      },
      insurance: {
        agent_role: 'Insurance Advisor',
        agent_description: 'You are an experienced insurance advisor helping users understand insurance options, coverage, and make informed decisions.',
        tone: 'Professional, clear, and helpful',
        language: 'English'
      }
    };

    if (presets[preset]) {
      setConfig(presets[preset]);
      setMessage('');
    }
  };

  if (loading) {
    return (
      <div className="config-panel">
        <div className="loading">Loading configuration...</div>
      </div>
    );
  }

  return (
    <div className="config-panel">
      <h2>Agent Configuration</h2>
      
      <div className="presets">
        <label>Quick Presets:</label>
        <div className="preset-buttons">
          <button onClick={() => loadPreset('financial')} className="preset-btn">
            💰 Financial Advisor
          </button>
          <button onClick={() => loadPreset('health')} className="preset-btn">
            🏥 Health Assistant
          </button>
          <button onClick={() => loadPreset('insurance')} className="preset-btn">
            🛡️ Insurance Advisor
          </button>
        </div>
      </div>

      <div className="config-form">
        <div className="form-group">
          <label htmlFor="agent_role">Agent Role:</label>
          <input
            id="agent_role"
            type="text"
            value={config.agent_role}
            onChange={(e) => handleChange('agent_role', e.target.value)}
            placeholder="e.g., Financial Advisor"
          />
        </div>

        <div className="form-group">
          <label htmlFor="agent_description">Description:</label>
          <textarea
            id="agent_description"
            value={config.agent_description}
            onChange={(e) => handleChange('agent_description', e.target.value)}
            placeholder="Describe the agent's expertise and purpose..."
            rows="3"
          />
        </div>

        <div className="form-group">
          <label htmlFor="tone">Tone:</label>
          <input
            id="tone"
            type="text"
            value={config.tone}
            onChange={(e) => handleChange('tone', e.target.value)}
            placeholder="e.g., Friendly, confident, and professional"
          />
        </div>

        <div className="form-group">
          <label htmlFor="language">Language:</label>
          <select
            id="language"
            value={config.language}
            onChange={(e) => handleChange('language', e.target.value)}
          >
            <option value="English">English</option>
            <option value="Spanish">Spanish</option>
            <option value="French">French</option>
            <option value="German">German</option>
            <option value="Chinese">Chinese</option>
          </select>
        </div>

        <button
          onClick={handleSave}
          className="save-btn"
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>

        {message && (
          <div className={`message ${message.includes('Error') ? 'error' : 'success'}`}>
            {message}
          </div>
        )}
      </div>
    </div>
  );
};

export default ConfigPanel;

