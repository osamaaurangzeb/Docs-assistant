import { useState } from "react";
import { askQuestion, deleteSession, submitDocument } from "./api.js";
import AnswerList from "./components/AnswerList.jsx";
import DocumentForm from "./components/DocumentForm.jsx";
import QuestionForm from "./components/QuestionForm.jsx";

export default function App() {
  const [session, setSession] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [pendingQuestion, setPendingQuestion] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  async function handleDocument(input) {
    setError(null);
    setUploading(true);
    try {
      const { sessionId, chunkCount } = await submitDocument(input);
      setSession({ id: sessionId, chunkCount });
      setAnswers([]);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleAsk(question) {
    setError(null);
    setPendingQuestion(question);
    try {
      const { answer, sources } = await askQuestion(session.id, question);
      setAnswers((current) => [...current, { question, answer, sources }]);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    } finally {
      setPendingQuestion(null);
    }
  }

  function handleReset() {
    const sessionId = session.id;
    setSession(null);
    setAnswers([]);
    setError(null);
    deleteSession(sessionId).catch(() => {});
  }

  return (
    <main className="page-shell">
      <header className="site-header">
        <a className="brand" href="/" aria-label="Docwise home">
          <span className="brand-mark" aria-hidden="true">D</span>
          <span>docwise</span>
        </a>
        <span className="header-note">Your documents, easier to explore</span>
      </header>

      <section className="hero">
        <span className="eyebrow">DOCUMENT Q&A</span>
        <h1>Get to know your documents.</h1>
        <p>Bring a document. Ask a question. Get a clear answer grounded in what you shared.</p>
      </section>

      {error && <div className="error" role="alert"><span aria-hidden="true">!</span>{error}</div>}

      {!session ? (
        <DocumentForm onSubmit={handleDocument} loading={uploading} />
      ) : (
        <>
          <section className="card status-card" aria-live="polite">
            <div className="status-copy">
              <span className="status-indicator" aria-hidden="true" />
              <div>
                <strong>Your document is ready</strong>
                <p>{session.chunkCount} passages indexed and ready to search</p>
              </div>
            </div>
            <button type="button" className="button button-quiet" onClick={handleReset}>Change document</button>
          </section>
          <QuestionForm onAsk={handleAsk} loading={pendingQuestion !== null} />
          <AnswerList items={answers} pendingQuestion={pendingQuestion} />
        </>
      )}

      <footer className="site-footer">
        <span>Answers are based on the document you provide.</span>
        <span>Session-scoped · No account required</span>
      </footer>
    </main>
  );
}
