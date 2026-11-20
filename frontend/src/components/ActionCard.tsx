import React from 'react';
import type { SystemAction } from '../types';

interface ActionCardProps {
  action: SystemAction;
}

export const ActionCard: React.FC<ActionCardProps> = ({ action }) => {
  const { action: actionType, title, message, data } = action;

  // 1. Volume Card
  if (actionType === 'volume') {
    const isMute = action.tool_type === 'volume_mute';
    const percent = typeof data?.percent === 'number' ? data.percent : null;
    return (
      <div className="action-card volume-card">
        <div className="action-card-header">
          <div className="action-card-icon">{isMute ? '🔇' : '🔊'}</div>
          <div className="action-card-info">
            <div className="action-card-title">{title}</div>
            <div className="action-card-subtitle">{message}</div>
          </div>
          {percent !== null && (
            <div className="action-card-badge">{percent}%</div>
          )}
        </div>
        {percent !== null && (
          <div className="action-meter-wrap">
            <div className="action-meter-bar" style={{ width: `${percent}%` }}></div>
          </div>
        )}
      </div>
    );
  }

  // 2. Battery & Power Card
  if (actionType === 'battery') {
    const percent = data?.percent ?? 100;
    const plugged = Boolean(data?.plugged);
    const meterColor = percent > 40 ? 'var(--ok)' : percent > 20 ? 'var(--warn)' : '#e04838';

    return (
      <div className="action-card battery-card">
        <div className="action-card-header">
          <div className="action-card-icon">{plugged ? '⚡' : '🔋'}</div>
          <div className="action-card-info">
            <div className="action-card-title">{title}</div>
            <div className="action-card-subtitle">{message}</div>
          </div>
          <div className="action-card-badge" style={{ color: meterColor }}>
            {percent}%
          </div>
        </div>
        <div className="action-meter-wrap">
          <div
            className="action-meter-bar"
            style={{ width: `${percent}%`, background: meterColor }}
          ></div>
        </div>
      </div>
    );
  }

  // 3. Hardware Specs (RAM / CPU)
  if (actionType === 'system_specs') {
    const ramPct = data?.ram_percent ?? 50;
    const cpuPct = intVal(data?.cpu_percent);
    const freeGb = data?.ram_free_gb ?? 0;
    const totalGb = data?.ram_total_gb ?? 16;

    return (
      <div className="action-card specs-card">
        <div className="action-card-header">
          <div className="action-card-icon">💻</div>
          <div className="action-card-info">
            <div className="action-card-title">{title}</div>
            <div className="action-card-subtitle">Windows Performance Metrics</div>
          </div>
        </div>

        <div className="action-specs-grid">
          <div className="action-spec-item">
            <div className="spec-label">CPU LOAD</div>
            <div className="spec-val">{cpuPct}%</div>
            <div className="action-meter-wrap mini">
              <div className="action-meter-bar" style={{ width: `${cpuPct}%` }}></div>
            </div>
          </div>
          <div className="action-spec-item">
            <div className="spec-label">RAM USAGE</div>
            <div className="spec-val">{ramPct}%</div>
            <div className="action-meter-wrap mini">
              <div className="action-meter-bar" style={{ width: `${ramPct}%` }}></div>
            </div>
            <div className="spec-sub">{freeGb} GB free of {totalGb} GB</div>
          </div>
        </div>
      </div>
    );
  }

  // 4. App Launcher Card
  if (actionType === 'app_launch') {
    const appName = data?.app_name || 'Windows App';
    return (
      <div className="action-card app-card">
        <div className="action-card-header">
          <div className="action-card-icon">🚀</div>
          <div className="action-card-info">
            <div className="action-card-title">{title}</div>
            <div className="action-card-subtitle">{message}</div>
          </div>
          <div className="action-card-badge">{appName}</div>
        </div>
      </div>
    );
  }

  // 5. Clipboard Card
  if (actionType === 'clipboard') {
    const hasText = Boolean(data?.has_text);
    const wordCount = data?.word_count ?? 0;
    const preview = data?.preview || message;

    return (
      <div className="action-card clipboard-card">
        <div className="action-card-header">
          <div className="action-card-icon">📋</div>
          <div className="action-card-info">
            <div className="action-card-title">{title}</div>
            <div className="action-card-subtitle">
              {hasText ? `${wordCount} words on Windows clipboard` : 'Clipboard is empty'}
            </div>
          </div>
          {hasText && <div className="action-card-badge">{wordCount} words</div>}
        </div>
        {hasText && (
          <div className="action-clipboard-quote">
            <span>“{preview}”</span>
          </div>
        )}
      </div>
    );
  }

  // 6. Screen Vision Card (Phase 8)
  if (actionType === 'screen_vision') {
    const thumb = data?.thumbnail_base64;
    const activeWindow = data?.active_window || 'Primary Display';
    const resolution = data?.width && data?.height ? `${data.width}×${data.height}` : '1080p';

    return (
      <div className="action-card vision-card">
        <div className="action-card-header">
          <div className="action-card-icon">👁️</div>
          <div className="action-card-info">
            <div className="action-card-title">{title}</div>
            <div className="action-card-subtitle">{message}</div>
          </div>
          <div className="action-card-badge">{resolution}</div>
        </div>
        {thumb && (
          <div className="action-vision-preview-wrap">
            <img src={thumb} alt={activeWindow} className="action-vision-img" />
            <div className="action-vision-overlay">
              <span className="vision-overlay-tag">Active: {activeWindow}</span>
            </div>
          </div>
        )}
      </div>
    );
  }

  // 7. Local Document Knowledge Card (Phase 9 RAG)
  if (actionType === 'document_search') {
    const chunks: any[] = Array.isArray(data?.chunks) ? data.chunks : [];
    const count = data?.count ?? chunks.length;
    const docs: string[] = Array.isArray(data?.documents) ? data.documents : [];

    return (
      <div className="action-card doc-card">
        <div className="action-card-header">
          <div className="action-card-icon">📚</div>
          <div className="action-card-info">
            <div className="action-card-title">{title}</div>
            <div className="action-card-subtitle">{message}</div>
          </div>
          <div className="action-card-badge">{count} match{count === 1 ? '' : 'es'}</div>
        </div>

        {docs.length > 0 && (
          <div className="action-doc-tags">
            {docs.map((doc, idx) => (
              <span key={idx} className="doc-chip">📄 {doc}</span>
            ))}
          </div>
        )}

        {chunks.length > 0 && (
          <div className="action-doc-snippets">
            {chunks.slice(0, 2).map((chunk, idx) => (
              <div key={idx} className="doc-snippet-item">
                <span className="doc-source-label">{chunk.doc_name}</span>
                <p className="doc-snippet-text">“{chunk.snippet}”</p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // 8. Timers & Reminders Card (Phase 10)
  if (actionType === 'timer') {
    const subAction = action.tool_type || data?.action || 'timer';
    const duration = data?.duration_seconds ? `${Math.round(data.duration_seconds)}s` : '';
    const status = subAction === 'cancel' ? 'Cancelled' : subAction === 'list' ? 'Active' : 'Scheduled';

    return (
      <div className="action-card timer-card">
        <div className="action-card-header">
          <div className="action-card-icon">⏱️</div>
          <div className="action-card-info">
            <div className="action-card-title">{title}</div>
            <div className="action-card-subtitle">{message}</div>
          </div>
          <div className={`action-card-badge timer-status ${subAction}`}>
            {duration ? `${duration} · ${status}` : status}
          </div>
        </div>
      </div>
    );
  }

  // 9. Sandbox Security Protection Card
  if (actionType === 'sandbox_blocked') {
    const policy = data?.policy || 'AURA-SANDBOX-v1.0';
    const target = data?.blocked_target || '';

    return (
      <div className="action-card sandbox-card">
        <div className="action-card-header">
          <div className="action-card-icon">🛡️</div>
          <div className="action-card-info">
            <div className="action-card-title">{title || 'AURA Sandbox Alert'}</div>
            <div className="action-card-subtitle">{message}</div>
          </div>
          <div className="action-card-badge sandbox-badge">
            BLOCKED · SAFE
          </div>
        </div>
        <div className="action-sandbox-details">
          {target && <div className="sandbox-target">Target: <code>{target}</code></div>}
          <div className="sandbox-policy-tag">Enforced by {policy}</div>
        </div>
      </div>
    );
  }

  // 10. Window Management & Active Windows
  if (actionType === 'window_management' || actionType === 'app_close' || actionType === 'active_window' || actionType === 'running_apps') {
    const icon = actionType === 'app_close' ? '🛑' : actionType === 'active_window' ? '🪟' : actionType === 'running_apps' ? '📑' : '📐';
    const appsList: any[] = Array.isArray(data?.apps) ? data.apps : [];
    return (
      <div className="action-card window-card">
        <div className="action-card-header">
          <div className="action-card-icon">{icon}</div>
          <div className="action-card-info">
            <div className="action-card-title">{title}</div>
            <div className="action-card-subtitle">{message}</div>
          </div>
          {data?.action && <div className="action-card-badge">{String(data.action).toUpperCase()}</div>}
        </div>
        {appsList.length > 0 && (
          <div className="action-doc-tags" style={{ marginTop: '8px' }}>
            {appsList.slice(0, 6).map((app, idx) => (
              <span key={idx} className="doc-chip">🪟 {app.title || app.process}</span>
            ))}
          </div>
        )}
      </div>
    );
  }

  // 11. File & Storage Operations (Organize, Duplicates, Large Files, Search, Storage Drives)
  if (actionType === 'file_search' || actionType === 'file_organize' || actionType === 'large_files' || actionType === 'duplicate_files' || actionType === 'storage_analysis' || actionType === 'read_document') {
    const icon = actionType === 'file_organize' ? '📂' : actionType === 'duplicate_files' ? '👥' : actionType === 'storage_analysis' ? '💾' : '📄';
    const plan: any[] = Array.isArray(data?.plan) ? data.plan : [];
    const files: any[] = Array.isArray(data?.files) ? data.files : [];
    const drives: any[] = Array.isArray(data?.drives) ? data.drives : [];

    return (
      <div className="action-card file-card">
        <div className="action-card-header">
          <div className="action-card-icon">{icon}</div>
          <div className="action-card-info">
            <div className="action-card-title">{title}</div>
            <div className="action-card-subtitle">{message}</div>
          </div>
          {data?.preview && <div className="action-card-badge" style={{ background: 'var(--amber-surface, #feecd4)', color: '#b45309' }}>PREVIEW</div>}
        </div>

        {plan.length > 0 && (
          <div className="action-doc-snippets" style={{ marginTop: '8px' }}>
            {plan.slice(0, 4).map((p, idx) => (
              <div key={idx} className="doc-snippet-item" style={{ padding: '4px 8px' }}>
                <span className="doc-source-label">{p.category}</span>
                <span style={{ fontSize: '0.85rem' }}>{p.file}</span>
              </div>
            ))}
          </div>
        )}

        {files.length > 0 && (
          <div className="action-doc-tags" style={{ marginTop: '8px' }}>
            {files.slice(0, 5).map((f, idx) => (
              <span key={idx} className="doc-chip">📄 {f.name} ({f.size_mb || 0} MB)</span>
            ))}
          </div>
        )}

        {drives.length > 0 && (
          <div className="action-specs-grid" style={{ marginTop: '8px' }}>
            {drives.slice(0, 2).map((d, idx) => (
              <div key={idx} className="action-spec-item">
                <div className="spec-label">DRIVE {d.device}</div>
                <div className="spec-val">{d.percent_used}% Used</div>
                <div className="spec-sub">{d.free_gb} GB free of {d.total_gb} GB</div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // 12. Developer Assistant (Git, Diff, Tests)
  if (actionType === 'git_status' || actionType === 'git_diff' || actionType === 'unit_tests') {
    const isTest = actionType === 'unit_tests';
    const isPassed = data?.passed;
    const icon = isTest ? (isPassed ? '✅' : '❌') : '🐙';

    return (
      <div className="action-card dev-card">
        <div className="action-card-header">
          <div className="action-card-icon">{icon}</div>
          <div className="action-card-info">
            <div className="action-card-title">{title}</div>
            <div className="action-card-subtitle">{message}</div>
          </div>
          {isTest && (
            <div className="action-card-badge" style={{ background: isPassed ? '#dcfce7' : '#fee2e2', color: isPassed ? '#166534' : '#991b1b' }}>
              {isPassed ? 'ALL TESTS OK' : 'FAILED'}
            </div>
          )}
        </div>
      </div>
    );
  }

  // 13. Multi-Step Composite Workflow
  if (actionType === 'composite_workflow') {
    const steps: any[] = Array.isArray(data?.steps) ? data.steps : [];
    return (
      <div className="action-card workflow-card" style={{ borderLeft: '3px solid var(--accent, #6366f1)' }}>
        <div className="action-card-header">
          <div className="action-card-icon">⚡</div>
          <div className="action-card-info">
            <div className="action-card-title">{title}</div>
            <div className="action-card-subtitle">{message}</div>
          </div>
          <div className="action-card-badge">{data?.step_count || steps.length} STEPS</div>
        </div>
      </div>
    );
  }

  // 14. Zero-Trust Security Checkpoint Card
  if (actionType === 'permission_checkpoint' || action.type === 'checkpoint_required') {
    const approvalId = data?.approval_id;
    const [actionState, setActionState] = React.useState<'idle' | 'approved' | 'denied'>('idle');

    const handleConfirm = async () => {
      if (!approvalId) return;
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/security/approve/${approvalId}`, { method: 'POST' });
        if (res.ok) setActionState('approved');
      } catch (e) {
        console.error(e);
      }
    };

    const handleDeny = async () => {
      if (!approvalId) return;
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/security/reject/${approvalId}`, { method: 'POST' });
        if (res.ok) setActionState('denied');
      } catch (e) {
        console.error(e);
      }
    };

    return (
      <div className="action-card checkpoint-card" style={{ borderLeft: '4px solid #f59e0b', background: 'rgba(245, 158, 11, 0.05)' }}>
        <div className="action-card-header">
          <div className="action-card-icon">🛡️</div>
          <div className="action-card-info">
            <div className="action-card-title">{title}</div>
            <div className="action-card-subtitle">{message}</div>
          </div>
          <div className="action-card-badge" style={{ background: '#f59e0b', color: '#000' }}>CHECKPOINT</div>
        </div>
        {actionState === 'idle' ? (
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '10px' }}>
            <button
              onClick={handleDeny}
              style={{ padding: '6px 14px', borderRadius: '6px', border: '1px solid #ef4444', background: 'transparent', color: '#ef4444', fontSize: '12px', fontWeight: 600, cursor: 'pointer' }}
            >
              Deny
            </button>
            <button
              onClick={handleConfirm}
              style={{ padding: '6px 14px', borderRadius: '6px', border: 'none', background: '#10b981', color: '#fff', fontSize: '12px', fontWeight: 600, cursor: 'pointer' }}
            >
              Authorize
            </button>
          </div>
        ) : (
          <div style={{ marginTop: '8px', fontSize: '12px', fontWeight: 600, color: actionState === 'approved' ? '#10b981' : '#ef4444' }}>
            {actionState === 'approved' ? '✓ Authorized & Executed' : '✕ Denied by User'}
          </div>
        )}
      </div>
    );
  }

  // 15. Media / Web Search Card
  return (
    <div className="action-card generic-card">
      <div className="action-card-header">
        <div className="action-card-icon">
          {actionType === 'media' ? '🎵' : '🌐'}
        </div>
        <div className="action-card-info">
          <div className="action-card-title">{title}</div>
          <div className="action-card-subtitle">{message}</div>
        </div>
      </div>
    </div>
  );
};

function intVal(val: any): number {
  if (typeof val === 'number') return Math.round(val);
  return 0;
}

export default ActionCard;
