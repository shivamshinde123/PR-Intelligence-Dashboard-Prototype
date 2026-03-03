import React, { useState } from 'react';
import Dashboard from './components/Dashboard.jsx';
import { analyzePR } from './api.js';

export default function App() {
    const [prUrl, setPrUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!prUrl.trim()) return;
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const data = await analyzePR(prUrl.trim());
            setResult(data);
        } catch (err) {
            console.error(err);
            setError(err.message || 'Failed to analyze PR');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="app-container">
            {/* Header */}
            <header className="app-header animate-fadeInUp">
                <h1>PR Intelligence Dashboard</h1>
                <p>Paste a public GitHub PR URL to get an AI-powered intelligence report.</p>
            </header>

            {/* Input */}
            <div className="input-card animate-fadeInUp" style={{ animationDelay: '0.1s' }}>
                <form onSubmit={handleSubmit}>
                    <div className="input-row">
                        <input
                            id="pr-url-input"
                            type="url"
                            placeholder="https://github.com/owner/repo/pull/123"
                            value={prUrl}
                            onChange={(e) => setPrUrl(e.target.value)}
                            required
                        />
                        <button
                            id="analyze-btn"
                            type="submit"
                            className="btn-primary"
                            disabled={loading}
                        >
                            {loading ? 'Analyzing…' : '✨ Analyze PR'}
                        </button>
                    </div>
                </form>
            </div>

            {/* Error */}
            {error && (
                <div className="error-banner animate-fadeInUp" role="alert">
                    <strong>Error:</strong> {error}
                </div>
            )}

            {/* Loading */}
            {loading && (
                <div className="loading-container animate-fadeInUp">
                    <div className="spinner" />
                    <p>Fetching PR data and running AI analysis…</p>
                    <p style={{ fontSize: '0.82rem', opacity: 0.6 }}>
                        This may take 15–30 seconds depending on PR size.
                    </p>
                </div>
            )}

            {/* Dashboard */}
            {result && <Dashboard data={result} prUrl={prUrl} />}
        </div>
    );
}
