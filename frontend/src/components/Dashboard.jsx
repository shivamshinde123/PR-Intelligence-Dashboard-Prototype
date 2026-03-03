import React from 'react';

/* ─── helpers ─── */
function clamp(v, min, max) { return Math.min(max, Math.max(min, v)); }

function colorForScore(score, max = 10) {
    const pct = score / max;
    if (pct >= 0.7) return 'red';
    if (pct >= 0.4) return 'amber';
    return 'green';
}

/* ─── Bar ─── */
function Bar({ label, value, displayValue, max = 100, color = 'blue' }) {
    const pct = clamp((value / max) * 100, 0, 100);
    return (
        <div className="bar-container animate-fadeInUp">
            <div className="bar-header">
                <span className="bar-label">{label}</span>
                <span className="bar-value">{displayValue ?? value.toFixed(1)}</span>
            </div>
            <div className="bar-track">
                <div className={`bar-fill ${color} animate-barGrow`} style={{ width: `${pct}%` }} />
            </div>
        </div>
    );
}

/* ─── Score Tile ─── */
function ScoreTile({ label, value, color }) {
    return (
        <div className="score-tile animate-fadeInUp">
            <div className="score-tile-label">{label}</div>
            <div className="score-tile-value" style={{ color }}>{value}</div>
        </div>
    );
}

/* ─── Badge ─── */
function WorkBadge({ type }) {
    const icon = { feature: '🚀', bug: '🐛', tech_debt: '🔧', maintenance: '🛠️' }[type] || '📦';
    return <span className={`badge ${type}`}>{icon} {type.replace('_', ' ')}</span>;
}

/* ─── Export ─── */
function exportSummary(data, prUrl) {
    const lines = [
        `PR Intelligence Report`,
        `======================`,
        `PR: ${prUrl || 'N/A'}`,
        `Date: ${new Date().toISOString()}`,
        ``,
        `Complexity Score: ${data.complexity_score}/10`,
        `Expert Hours: ${data.expert_hours}`,
        `Work Type: ${data.work_type}`,
        `AI Attribution Confidence: ${(data.ai_attribution_confidence * 100).toFixed(0)}%`,
        `Review Quality Score: ${data.review_quality_score}/10`,
        ``,
        `Linter Issues: ${data.linter_issues?.length ? data.linter_issues.join('; ') : 'None'}`,
        ``,
        `Reasoning:`,
        data.reasoning || 'N/A',
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'pr-intelligence-report.txt';
    a.click();
    URL.revokeObjectURL(url);
}

/* ═══════════════════════════════════════════
   Dashboard Component
   ═══════════════════════════════════════════ */
export default function Dashboard({ data, prUrl }) {
    const {
        complexity_score = 0,
        expert_hours = 0,
        work_type = 'feature',
        ai_attribution_confidence = 0,
        review_quality_score = 0,
        linter_issues = [],
        reasoning = '',
    } = data;

    const aiPct = (ai_attribution_confidence * 100).toFixed(0);
    const humanPct = (100 - ai_attribution_confidence * 100).toFixed(0);

    return (
        <div className="dashboard-card animate-fadeInUp" style={{ animationDelay: '0.15s' }}>
            {/* Card Header */}
            <div className="dashboard-card-header">
                <h2>📊 Analysis Report</h2>
                <button
                    id="export-btn"
                    className="btn-export"
                    onClick={() => exportSummary(data, prUrl)}
                >
                    ↓ Export
                </button>
            </div>

            <div className="dashboard-card-body stagger">
                {/* Score tiles (2×2) */}
                <div className="score-grid">
                    <ScoreTile
                        label="Complexity"
                        value={`${complexity_score.toFixed(1)}`}
                        color={
                            complexity_score >= 7 ? 'var(--color-red)'
                                : complexity_score >= 4 ? 'var(--color-amber)'
                                    : 'var(--color-green)'
                        }
                    />
                    <ScoreTile
                        label="Expert Hours"
                        value={`${expert_hours.toFixed(1)}h`}
                        color="var(--color-cyan)"
                    />
                    <ScoreTile
                        label="Review Quality"
                        value={`${review_quality_score.toFixed(1)}`}
                        color={
                            review_quality_score >= 7 ? 'var(--color-green)'
                                : review_quality_score >= 4 ? 'var(--color-amber)'
                                    : 'var(--color-red)'
                        }
                    />
                    <div className="score-tile animate-fadeInUp" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                        <div className="score-tile-label">Work Type</div>
                        <div style={{ marginTop: '0.35rem' }}>
                            <WorkBadge type={work_type} />
                        </div>
                    </div>
                </div>

                {/* Bars */}
                <Bar
                    label="Complexity Score"
                    value={complexity_score}
                    displayValue={`${complexity_score.toFixed(1)} / 10`}
                    max={10}
                    color={colorForScore(complexity_score)}
                />
                <Bar
                    label="AI Attribution Confidence"
                    value={ai_attribution_confidence * 100}
                    displayValue={`${aiPct}% AI · ${humanPct}% Human`}
                    max={100}
                    color="purple"
                />
                <Bar
                    label="Review Quality"
                    value={review_quality_score}
                    displayValue={`${review_quality_score.toFixed(1)} / 10`}
                    max={10}
                    color={colorForScore(10 - review_quality_score)}
                />

                {/* Divider */}
                <hr className="divider" />

                {/* Linter Issues */}
                <div className="animate-fadeInUp">
                    <h3 className="section-title">🔍 AI Rules Linter</h3>
                    {linter_issues && linter_issues.length > 0 ? (
                        <ul className="linter-list">
                            {linter_issues.map((issue, i) => (
                                <li key={i}>{issue}</li>
                            ))}
                        </ul>
                    ) : (
                        <p className="empty-state">No AI rules files detected in this PR.</p>
                    )}
                </div>

                {/* Reasoning */}
                {reasoning && (
                    <>
                        <hr className="divider" />
                        <div className="animate-fadeInUp">
                            <h3 className="section-title">💡 Reasoning</h3>
                            <div className="reasoning-box">{reasoning}</div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
