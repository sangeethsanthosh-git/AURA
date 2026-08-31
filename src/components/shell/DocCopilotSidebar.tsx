import { useState } from "react";
import { PageId } from "./AppShell";

interface DocCopilotSidebarProps {
  activePage: PageId;
  onPageChange: (page: PageId) => void;
  activeDocId?: string;
  onSelectDoc?: (docId: string) => void;
  onNewDoc?: () => void;
}

export function DocCopilotSidebar({
  activeDocId = "bizplan",
  onSelectDoc,
  onNewDoc,
}: DocCopilotSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <aside className="doc-copilot-sidebar" aria-label="Project Notes and Files">
      {/* Top Project Header */}
      <div className="doc-sidebar-header">
        <div className="project-title-box">
          <span className="project-book-icon">📖</span>
          <h2 className="project-title">Business planing project</h2>
        </div>
        <button type="button" className="sidebar-header-icon-btn" title="Toggle Sidebar">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M9 3v18" />
          </svg>
        </button>
      </div>

      {/* Search Input */}
      <div className="doc-sidebar-search">
        <span className="search-icon">🔍</span>
        <input
          type="text"
          placeholder="Search"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="doc-search-input"
        />
      </div>

      {/* Instructions Link */}
      <button type="button" className="doc-sidebar-link-row">
        <span className="link-icon">⚐</span>
        <span className="link-text">Instructions</span>
        <span className="link-chevron">›</span>
      </button>

      {/* Note Section Header */}
      <div className="doc-tree-section">
        <div className="doc-section-title-row">
          <div className="section-title-left">
            <span className="section-icon">🗎</span>
            <span className="section-name">Note</span>
          </div>
          <div className="section-actions">
            <button type="button" className="section-btn" onClick={onNewDoc} title="Add Note">
              ＋
            </button>
            <button type="button" className="section-btn" title="Organize">
              ◫
            </button>
          </div>
        </div>

        {/* Tree Items */}
        <div className="doc-tree-items">
          <button type="button" className="tree-folder-btn">
            <span className="folder-icon">📁</span>
            <span>Business Planing</span>
          </button>
          <button type="button" className="tree-folder-btn">
            <span className="folder-icon">📁</span>
            <span>Marketing</span>
          </button>

          {/* Active Note (Matching Reference Image) */}
          <button
            type="button"
            className={`tree-file-btn ${activeDocId === "bizplan" ? "active" : ""}`}
            onClick={() => onSelectDoc?.("bizplan")}
          >
            <span className="file-icon">📄</span>
            <span className="file-label">Business Plan: AI-Powered Customer F...</span>
          </button>

          <button
            type="button"
            className={`tree-file-btn ${activeDocId === "financial" ? "active" : ""}`}
            onClick={() => onSelectDoc?.("financial")}
          >
            <span className="file-icon">📄</span>
            <span className="file-label">Financial Plan</span>
          </button>

          <button
            type="button"
            className={`tree-file-btn ${activeDocId === "summary" ? "active" : ""}`}
            onClick={() => onSelectDoc?.("summary")}
          >
            <span className="file-icon">📄</span>
            <span className="file-label">Summary</span>
          </button>
        </div>
      </div>

      {/* File Storage Section (Matching Reference Image) */}
      <div className="doc-tree-section">
        <div className="doc-section-title-row">
          <div className="section-title-left">
            <span className="section-icon">📁</span>
            <span className="section-name">File <span className="storage-muted">(0.8MB/5GB used)</span> ⓘ</span>
          </div>
          <button type="button" className="section-btn" title="Sync Files">
            ↻
          </button>
        </div>

        <div className="doc-tree-items">
          <div className="storage-file-item">
            <span className="file-icon">📄</span>
            <span className="storage-filename">Customer_Insight_Survey_Result.xlsx</span>
          </div>
          <div className="storage-file-item">
            <span className="file-icon">📄</span>
            <span className="storage-filename">Customer_Feedback.pdf</span>
          </div>
          <div className="storage-file-item">
            <span className="file-icon">📄</span>
            <span className="storage-filename">Market_Research.xlsx</span>
          </div>
        </div>
      </div>

      {/* Trash Link */}
      <button type="button" className="doc-sidebar-link-row doc-sidebar-link-row--trash">
        <span className="link-icon">🗑</span>
        <span className="link-text">Trash</span>
        <span className="link-chevron">›</span>
      </button>

      {/* User Footer Card (Matching Reference Image) */}
      <div className="doc-sidebar-user-footer">
        <div className="user-avatar-badge">J</div>
        <div className="user-info-text">
          <strong className="user-full-name">John Davis</strong>
          <span className="user-plan-pill">✦ 10000 Pro ›</span>
        </div>
      </div>
    </aside>
  );
}

