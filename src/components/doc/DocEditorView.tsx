import { useState } from "react";

interface DocEditorViewProps {
  docId?: string;
}

export function DocEditorView({ docId = "bizplan" }: DocEditorViewProps) {
  const [isBold, setIsBold] = useState(false);
  const [isItalic, setIsItalic] = useState(false);

  return (
    <div className="doc-editor-container" aria-label="Document Canvas">
      {/* Top Formatting Toolbar (Matching Reference Image) */}
      <header className="doc-formatting-toolbar">
        <div className="toolbar-group">
          <button type="button" className="toolbar-btn" title="Undo">↩</button>
          <button type="button" className="toolbar-btn" title="Redo">↪</button>
        </div>

        <div className="toolbar-divider" />

        <div className="toolbar-group">
          <button type="button" className="toolbar-btn toolbar-dropdown-btn">
            <span>Text</span>
            <span className="caret-down">▾</span>
          </button>
        </div>

        <div className="toolbar-divider" />

        <div className="toolbar-group">
          <button
            type="button"
            className={`toolbar-btn ${isBold ? "active" : ""}`}
            onClick={() => setIsBold(!isBold)}
            title="Bold"
          >
            <strong>B</strong>
          </button>
          <button
            type="button"
            className={`toolbar-btn ${isItalic ? "active" : ""}`}
            onClick={() => setIsItalic(!isItalic)}
            title="Italic"
          >
            <em>I</em>
          </button>
          <button type="button" className="toolbar-btn" title="Strikethrough">
            <s>S</s>
          </button>
        </div>

        <div className="toolbar-divider" />

        <div className="toolbar-group">
          <button type="button" className="toolbar-btn" title="Bullet list">:=</button>
          <button type="button" className="toolbar-btn" title="Numbered list">1.</button>
        </div>

        <div className="toolbar-divider" />

        <div className="toolbar-group">
          <button type="button" className="toolbar-btn" title="Code block">&lt;/&gt;</button>
          <button type="button" className="toolbar-btn" title="Table">⊞</button>
        </div>

        <div className="toolbar-right-actions">
          <button type="button" className="toolbar-btn" title="Share / Export">📤</button>
          <button type="button" className="toolbar-btn" title="More options">···</button>
        </div>
      </header>

      {/* Document Sheet Body (Matching Reference Image) */}
      <main className="doc-sheet-body">
        <article className="doc-sheet-paper">
          {/* Main Title & Last Updated Meta */}
          <h1 className="doc-main-title">
            Business Plan: AI-Powered Customer Feedback Intelligence for SMBs
          </h1>
          <div className="doc-updated-meta">Last updated : 2026/5/20</div>

          {/* Section: Executive Summary */}
          <section className="doc-section">
            <h2 className="doc-section-heading">Executive Summary</h2>
            <p className="doc-body-paragraph">
              A lean, vision-driven SaaS business that delivers AI-powered customer feedback intelligence to small and mid-sized businesses — the segment most underserved by enterprise tools. By offering a focused, affordable platform that turns raw customer feedback into clear, actionable insights, this venture capitalizes on a proven market need (evidenced by existing demand data) while keeping startup costs minimal through a software-only, subscription model.
            </p>

            {/* Core Promise Callout Box (Matching Reference Image) */}
            <div className="doc-highlight-callout">
              <strong className="callout-strong">Core Promise:</strong>
              <span>
                Any business with 10–500 employees can understand their customers as deeply as a Fortune 500 company — without the enterprise price tag or complexity.
              </span>
            </div>

            {/* Structured Key-Value Table (Matching Reference Image) */}
            <div className="doc-keyvalue-table-container">
              <table className="doc-keyvalue-table">
                <tbody>
                  <tr>
                    <td className="key-cell">Business Type:</td>
                    <td className="val-cell">B2B SaaS (software-as-a-service)</td>
                  </tr>
                  <tr>
                    <td className="key-cell">Initial Investment:</td>
                    <td className="val-cell">$8,000–$15,000 (bootstrappable)</td>
                  </tr>
                  <tr>
                    <td className="key-cell">Target Breakeven:</td>
                    <td className="val-cell">Month 6–9</td>
                  </tr>
                  <tr>
                    <td className="key-cell">Revenue Model:</td>
                    <td className="val-cell">Monthly subscription (recurring)</td>
                  </tr>
                  <tr>
                    <td className="key-cell">First Revenue:</td>
                    <td className="val-cell">Month 1–2 (pilot customers)</td>
                  </tr>
                  <tr>
                    <td className="key-cell">Team Size at Launch:</td>
                    <td className="val-cell">1–2 founders</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* Section: Vision & Brand Identity */}
          <section className="doc-section">
            <h2 className="doc-section-heading">Vision & Brand Identity</h2>
            <h3 className="doc-subheading">Vision Statement</h3>
            <p className="doc-body-paragraph">
              To become the most trusted voice between businesses and their customers — making continuous customer listening as natural, instant, and frictionless as sending an email.
            </p>
          </section>
        </article>
      </main>
    </div>
  );
}

