import { useState } from "react";

export default function DocumentForm({ onSubmit, loading }) {
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const hasInput = file !== null || text.trim() !== "";

  function handleFile(event) {
    const chosen = event.target.files?.[0] ?? null;
    setFile(chosen);
    if (chosen) setText("");
  }

  function handleText(event) {
    setText(event.target.value);
    if (event.target.value) {
      setFile(null);
      const picker = document.getElementById("doc-file");
      if (picker) picker.value = "";
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    onSubmit({ text, file });
  }

  return (
    <form onSubmit={handleSubmit} className="card document-card">
      <div className="section-heading">
        <span className="step-number">01</span>
        <div>
          <h2>Add your document</h2>
          <p>Paste text or choose a plain-text or Markdown file.</p>
        </div>
      </div>

      <label htmlFor="doc-text">Paste your text</label>
      <textarea
        id="doc-text"
        rows={8}
        value={text}
        onChange={handleText}
        placeholder="Paste a report, set of notes, article, or other text…"
        disabled={loading}
      />

      <div className="or-divider"><span>OR</span></div>
      <label className="upload-area" htmlFor="doc-file">
        <span className="upload-icon" aria-hidden="true">↑</span>
        <strong>{file ? file.name : "Choose a file to upload"}</strong>
        <span>{file ? "File selected" : "TXT or MD · Up to 200 KB"}</span>
        <input id="doc-file" type="file" accept=".txt,.md,text/plain,text/markdown" onChange={handleFile} disabled={loading} />
      </label>

      <button type="submit" className="button button-primary button-wide" disabled={loading || !hasInput}>
        {loading ? <><span className="spinner" aria-hidden="true" /> Reading your document…</> : "Process document"}
        {!loading && <span aria-hidden="true">→</span>}
      </button>
      <p className="form-footnote">Your document is processed for this session and isn't saved permanently.</p>
    </form>
  );
}
