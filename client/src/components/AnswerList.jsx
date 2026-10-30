export default function AnswerList({ items, pendingQuestion }) {
  if (items.length === 0 && !pendingQuestion) return null;

  return (
    <section className="card answers-card" aria-live="polite">
      <div className="answers-heading">
        <div>
          <span className="eyebrow">YOUR RESULTS</span>
          <h2>Answers</h2>
        </div>
        <span className="answer-count">{items.length} {items.length === 1 ? "answer" : "answers"}</span>
      </div>
      {pendingQuestion && (
        <article className="qa pending-answer">
          <p className="question">{pendingQuestion}</p>
          <p className="hint"><span className="spinner" aria-hidden="true" /> Looking through your document…</p>
        </article>
      )}
      {[...items].reverse().map((item, index) => (
        <article className="qa" key={`${items.length - index}-${item.question}`}>
          <p className="question"><span className="question-mark">Q</span>{item.question}</p>
          <div className="answer-wrap">
            <span className="answer-mark" aria-hidden="true">A</span>
            <p className="answer">{item.answer}</p>
          </div>
          {item.sources.length > 0 && (
            <details className="sources">
              <summary>{item.sources.length} source {item.sources.length === 1 ? "passage" : "passages"}</summary>
              <ul>
                {item.sources.map((source) => (
                  <li key={source.chunkIndex}>
                    <strong>Passage {source.chunkIndex}</strong>
                    <span className="source-score">Match {Math.round(source.score * 100)}%</span>
                    <p>{source.preview}{source.preview.length >= 200 ? "…" : ""}</p>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </article>
      ))}
    </section>
  );
}
