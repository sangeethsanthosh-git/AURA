import React, { useState, useEffect } from 'react';
import type { CursorConfig } from './CustomCursor';
import { Sparkles, MousePointer, Monitor, RefreshCw, Check, RotateCcw } from 'lucide-react';
import { CAT_PAW_ANIMATED_GIF } from '../assets/cursorBase64';

interface CursorSettingsSectionProps {
  config: CursorConfig;
  onChange: (newConfig: CursorConfig) => void;
}

interface WindowsCursorStatus {
  system_wide_active: boolean;
  current_system_arrow: string;
  current_system_hand: string;
  backup_available: boolean;
  ani_asset_exists: boolean;
  cur_asset_exists: boolean;
}

export const CursorSettingsSection: React.FC<CursorSettingsSectionProps> = ({ config, onChange }) => {
  const [winStatus, setWinStatus] = useState<WindowsCursorStatus | null>(null);
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);
  const [testClickCount, setTestClickCount] = useState<number>(0);

  const fetchWinStatus = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/cursor/status');
      if (res.ok) {
        const data = await res.json();
        setWinStatus(data);
      }
    } catch (e) {
      console.debug('Failed to query cursor status:', e);
    }
  };

  useEffect(() => {
    fetchWinStatus();
  }, []);

  const handleApplySystemWide = async () => {
    setShowConfirmModal(false);
    setLoadingAction('apply');
    try {
      const res = await fetch('http://127.0.0.1:8000/api/cursor/system/apply', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setMessage('✨ Kawaii Pixel Cat Paw cursor applied across Windows desktop!');
        await fetchWinStatus();
      } else {
        setMessage(`Error applying cursor: ${data.error || 'Unknown error'}`);
      }
    } catch (err: any) {
      setMessage(`Network error: ${err.message}`);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleRestoreSystemWide = async () => {
    setLoadingAction('restore');
    try {
      const res = await fetch('http://127.0.0.1:8000/api/cursor/system/restore', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setMessage('✓ Original Windows cursor scheme restored successfully.');
        await fetchWinStatus();
      } else {
        setMessage(`Error restoring cursor: ${data.error || 'Unknown error'}`);
      }
    } catch (err: any) {
      setMessage(`Network error: ${err.message}`);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleRestoreDefaultAura = () => {
    onChange({
      theme: 'default',
      animated: true,
      size: 32,
    });
    setMessage('AURA cursor reset to default system cursor.');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div className="settings-section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span>AURA Desktop Assistant Claw</span>
        <span
          style={{
            fontSize: '10px',
            fontWeight: 700,
            padding: '2px 8px',
            borderRadius: '20px',
            backgroundColor: 'rgba(235, 94, 40, 0.12)',
            color: 'var(--accent, #eb5e28)',
            letterSpacing: '0.04em',
          }}
        >
          AUTONOMOUS TASK POINTER
        </span>
      </div>

      <div style={{ fontSize: '12px', color: 'var(--muted, #64748b)', lineHeight: '1.5' }}>
        🐾 The <strong>Kawaii Pixel Cat Paw</strong> represents AURA's hands when performing desktop operations (clicking search bars, typing, opening media, and clicking video thumbnails). Inside this assistant chat window, your normal native cursor is preserved.
      </div>

      {message && (
        <div
          style={{
            padding: '8px 12px',
            borderRadius: '8px',
            fontSize: '12px',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            color: '#10b981',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>{message}</span>
          <button
            onClick={() => setMessage(null)}
            style={{ background: 'none', border: 'none', color: '#10b981', cursor: 'pointer', fontSize: '14px' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Theme Selection: Default vs Kawaii Cat Paw */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        {/* Card 1: Default Cursor */}
        <div
          onClick={() => {
            onChange({ ...config, theme: 'default' });
            handleRestoreSystemWide();
          }}
          style={{
            padding: '14px',
            borderRadius: '12px',
            border: config.theme === 'default' ? '2px solid var(--accent, #eb5e28)' : '1px solid var(--line, #e2e8f0)',
            backgroundColor: config.theme === 'default' ? 'rgba(235, 94, 40, 0.04)' : 'rgba(0, 0, 0, 0.01)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              backgroundColor: 'rgba(0,0,0,0.04)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <MousePointer size={22} color="var(--ink, #1f2937)" />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--ink, #1f2937)' }}>
              Default System Cursor
            </div>
            <div style={{ fontSize: '11px', color: 'var(--muted, #64748b)', marginTop: '2px' }}>
              Standard Windows pointer
            </div>
          </div>
          {config.theme === 'default' && <Check size={18} color="var(--accent, #eb5e28)" />}
        </div>

        {/* Card 2: Kawaii Pixel Cat Paw */}
        <div
          onClick={() => {
            onChange({ ...config, theme: 'kawaii_cat_paw' });
            handleApplySystemWide();
          }}
          style={{
            padding: '14px',
            borderRadius: '12px',
            border:
              config.theme === 'kawaii_cat_paw' ? '2px solid var(--accent, #eb5e28)' : '1px solid var(--line, #e2e8f0)',
            backgroundColor:
              config.theme === 'kawaii_cat_paw' ? 'rgba(235, 94, 40, 0.04)' : 'rgba(0, 0, 0, 0.01)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              backgroundColor: 'rgba(235, 94, 40, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden',
            }}
          >
            <img
              src={CAT_PAW_ANIMATED_GIF}
              alt="Cat Paw"
              style={{ width: '32px', height: '32px', imageRendering: 'pixelated' }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--ink, #1f2937)' }}>
              Kawaii Pixel Cat Paw
            </div>
            <div style={{ fontSize: '11px', color: 'var(--muted, #64748b)', marginTop: '2px' }}>
              Animated pixel paw cursor theme
            </div>
          </div>
          {config.theme === 'kawaii_cat_paw' && <Check size={18} color="var(--accent, #eb5e28)" />}
        </div>
      </div>

      {/* Controls when Kawaii Cat Paw is active */}
      {config.theme === 'kawaii_cat_paw' && (
        <div
          style={{
            padding: '16px',
            backgroundColor: 'rgba(0, 0, 0, 0.02)',
            borderRadius: '12px',
            border: '1px solid var(--line, #e2e8f0)',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
          }}
        >
          {/* Animation Toggle */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
            }}
            onClick={() => onChange({ ...config, animated: !config.animated })}
          >
            <div>
              <div style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--ink, #1f2937)' }}>
                Enable Cat Paw Animation
              </div>
              <div style={{ fontSize: '11px', color: 'var(--muted, #64748b)' }}>
                {config.animated
                  ? 'Playing 10-frame Kawaii animation at native 6 fps'
                  : 'Static cat paw (reduced motion)'}
              </div>
            </div>
            <div className={`switch ${config.animated ? 'on' : ''}`}></div>
          </div>

          {/* Size Adjustment */}
          <div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--ink, #1f2937)', marginBottom: '8px' }}>
              Cursor Size: {config.size}px
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              {([32, 48, 64] as const).map((sz) => (
                <button
                  key={sz}
                  type="button"
                  onClick={() => onChange({ ...config, size: sz })}
                  style={{
                    flex: 1,
                    padding: '8px',
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    border: config.size === sz ? '2px solid var(--accent, #eb5e28)' : '1px solid var(--line, #e2e8f0)',
                    backgroundColor: config.size === sz ? 'rgba(235, 94, 40, 0.08)' : 'var(--bg, #ffffff)',
                    color: config.size === sz ? 'var(--accent, #eb5e28)' : 'var(--ink, #1f2937)',
                  }}
                >
                  {sz === 32 ? 'Normal (32px)' : sz === 48 ? 'Large (48px)' : 'Extra Large (64px)'}
                </button>
              ))}
            </div>
          </div>

          {/* Live Interactive Cursor Sandbox */}
          <div
            style={{
              padding: '14px',
              backgroundColor: 'rgba(255, 255, 255, 0.7)',
              borderRadius: '10px',
              border: '1px dashed var(--line, #cbd5e1)',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--muted, #64748b)', textTransform: 'uppercase' }}>
              🐾 Live Cursor Test Sandbox
            </div>
            <div style={{ fontSize: '12px', color: 'var(--ink, #1f2937)' }}>
              Move your mouse over each control below to verify interactive state changes and hotspot alignment:
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', alignItems: 'center' }}>
              {/* Test Button (Triggers pointer hand) */}
              <button
                type="button"
                onClick={() => setTestClickCount((c) => c + 1)}
                style={{
                  padding: '7px 14px',
                  borderRadius: '6px',
                  backgroundColor: 'var(--accent, #eb5e28)',
                  color: '#ffffff',
                  border: 'none',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Hover for Pointer Hand {testClickCount > 0 ? `(${testClickCount} taps!)` : ''}
              </button>

              {/* Test Text Input (Triggers native I-beam) */}
              <input
                type="text"
                placeholder="Hover here for Text I-beam..."
                defaultValue="Cat paw text selection test"
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--line, #cbd5e1)',
                  fontSize: '12px',
                  width: '210px',
                  backgroundColor: '#ffffff',
                }}
              />

              {/* Test Link */}
              <a
                href="#test"
                onClick={(e) => e.preventDefault()}
                style={{ fontSize: '12px', color: 'var(--accent, #eb5e28)', textDecoration: 'underline', cursor: 'pointer' }}
              >
                Interactive Link Test
              </a>
            </div>
          </div>

          {/* Restore Default Button */}
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button
              type="button"
              onClick={handleRestoreDefaultAura}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '6px',
                border: '1px solid var(--line, #cbd5e1)',
                backgroundColor: 'transparent',
                color: 'var(--muted, #64748b)',
                fontSize: '12px',
                cursor: 'pointer',
              }}
            >
              <RotateCcw size={13} />
              <span>Restore Default AURA Cursor</span>
            </button>
          </div>
        </div>
      )}

      {/* Windows Desktop System-Wide Integration */}
      <div
        style={{
          padding: '16px',
          borderRadius: '12px',
          border: '1px solid rgba(0, 0, 0, 0.08)',
          backgroundColor: 'rgba(0, 0, 0, 0.02)',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Monitor size={17} color="var(--ink, #1f2937)" />
            <span style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--ink, #1f2937)' }}>
              Windows Desktop Cursor Scheme (System-Wide)
            </span>
          </div>
          <span
            style={{
              fontSize: '11px',
              fontWeight: 600,
              padding: '2px 8px',
              borderRadius: '12px',
              backgroundColor: winStatus?.system_wide_active ? 'rgba(16, 185, 129, 0.15)' : 'rgba(0, 0, 0, 0.06)',
              color: winStatus?.system_wide_active ? '#10b981' : 'var(--muted, #64748b)',
            }}
          >
            {winStatus?.system_wide_active ? '● Cat Paw Active on Windows' : '○ Default Windows Scheme'}
          </span>
        </div>

        <div style={{ fontSize: '12px', color: 'var(--muted, #64748b)', lineHeight: 1.5 }}>
          Optionally apply the Kawaii Pixel Cat Paw animated cursor (.ani) and pointer (.cur) across your entire Windows OS
          (File Explorer, desktop, and other applications). Your original Windows cursor scheme is automatically backed up.
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginTop: '4px' }}>
          <button
            type="button"
            onClick={() => setShowConfirmModal(true)}
            disabled={loadingAction !== null || winStatus?.system_wide_active}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: winStatus?.system_wide_active ? '#94a3b8' : 'var(--ink, #1f2937)',
              color: '#ffffff',
              fontSize: '12.5px',
              fontWeight: 600,
              cursor: winStatus?.system_wide_active ? 'default' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Sparkles size={14} />
            <span>Apply to Windows Desktop</span>
          </button>

          {winStatus?.system_wide_active && (
            <button
              type="button"
              onClick={handleRestoreSystemWide}
              disabled={loadingAction !== null}
              style={{
                padding: '8px 16px',
                borderRadius: '8px',
                border: '1px solid var(--line, #cbd5e1)',
                backgroundColor: '#ffffff',
                color: 'var(--ink, #1f2937)',
                fontSize: '12.5px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <RotateCcw size={14} />
              <span>Restore Original Windows Scheme</span>
            </button>
          )}

          <button
            type="button"
            onClick={fetchWinStatus}
            title="Refresh Windows cursor status"
            style={{ background: 'none', border: 'none', color: 'var(--muted, #64748b)', cursor: 'pointer', padding: '6px' }}
          >
            <RefreshCw size={14} className={loadingAction ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Confirmation Modal for Windows System Changes */}
      {showConfirmModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            zIndex: 9999999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
          }}
          onClick={() => setShowConfirmModal(false)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '14px',
              padding: '24px',
              maxWidth: '440px',
              boxShadow: '0 20px 40px rgba(0, 0, 0, 0.25)',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '8px',
                  backgroundColor: 'rgba(235, 94, 40, 0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Monitor size={20} color="var(--accent, #eb5e28)" />
              </div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--ink, #1f2937)' }}>
                Apply Cursor to Windows?
              </div>
            </div>

            <div style={{ fontSize: '13px', color: 'var(--muted, #64748b)', lineHeight: 1.5 }}>
              This will configure the Kawaii Pixel Cat Paw animated cursor (<code>.ani</code>) and hand pointer (
              <code>.cur</code>) as your active Windows mouse theme via official Windows APIs.
              <br />
              <br />
              Your current Windows cursor theme will be automatically backed up so you can restore it anytime with one click.
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '6px' }}>
              <button
                type="button"
                onClick={() => setShowConfirmModal(false)}
                style={{
                  padding: '8px 16px',
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0',
                  backgroundColor: 'transparent',
                  color: 'var(--muted, #64748b)',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApplySystemWide}
                style={{
                  padding: '8px 16px',
                  borderRadius: '8px',
                  border: 'none',
                  backgroundColor: 'var(--accent, #eb5e28)',
                  color: '#ffffff',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Confirm & Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CursorSettingsSection;
