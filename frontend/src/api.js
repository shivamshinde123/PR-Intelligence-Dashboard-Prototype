// src/api.js
export async function analyzePR(prUrl) {
    const response = await fetch('/api/analyze-pr', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ pr_url: prUrl }),
    });

    if (!response.ok) {
        // The backend might return plain text or JSON — handle both
        let message = `Server error (${response.status})`;
        try {
            const text = await response.text();
            // Try to parse as JSON for FastAPI's {"detail": "..."} format
            try {
                const json = JSON.parse(text);
                message = json.detail || json.message || text;
            } catch {
                // Not JSON — use the raw text
                message = text || message;
            }
        } catch {
            // Could not read body at all
        }
        throw new Error(message);
    }

    const data = await response.json();
    return data;
}
