import { useState } from "react";

export default function QuestionForm({ onAsk, loading }) {
  const [question, setQuestion] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    const ok = await onAsk(question.trim());
    if (ok) setQuestion("");
  }

  return (
    <form onSubmit={handleSubmit} className="card question-card">
      <div className="section-heading">
        <span className="step-number">02</span>
        <div>
          <h2>What would you like to know?</h2>
          <p>Ask in your own words. Answers use the document's content.</p>
        </div>
      </div>
      <div className="question-entry">
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="e.g. What are the main points?"
          maxLength={1000}
          disabled={loading}
          aria-label="Question"
        />
        <button type="submit" className="button button-primary" disabled={loading || question.trim() === ""}>
          {loading ? "Thinking…" : "Ask question"}
          {!loading && <span aria-hidden="true">→</span>}
        </button>
      </div>
      <p className="form-footnote">Tip: Ask about a specific detail, date, person, or key idea.</p>
    </form>
  );
}
