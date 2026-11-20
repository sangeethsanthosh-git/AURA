import React, { useState, useEffect, useRef } from 'react';
import {
  Upload,
  Play,
  RotateCcw,
  Trash2,
  Check,
  Hand,
  Sliders,
  HelpCircle,
} from 'lucide-react';

interface ThemeVariant {
  file: string;
  hotspot?: [number, number];
  animated?: boolean;
  data_url?: string;
}

interface ThemeSettings {
  size: number;
  speed: number;
  hotspot: [number, number];
  animated: boolean;
}

export interface VirtualHandTheme {
  id: string;
  name: string;
  author: string;
  description?: string;
  is_builtin: boolean;
  is_active: boolean;
  settings: ThemeSettings;
  variants: Record<string, ThemeVariant>;
  preview?: string;
}

export const VirtualHandSettings: React.FC = () => {
  const [themes, setThemes] = useState<VirtualHandTheme[]>([]);
  const [activeTheme, setActiveTheme] = useState<VirtualHandTheme | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isTestingGlide, setIsTestingGlide] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Upload state
  const [customThemeName, setCustomThemeName] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Fetch installed themes from backend
  const fetchThemes = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/virtual-hand/themes');
      if (res.ok) {
        const data = await res.json();
        setThemes(data.themes || []);
        const active = (data.themes || []).find((t: VirtualHandTheme) => t.is_active);
        if (active) setActiveTheme(active);
      }
    } catch (e: any) {
      console.debug('Failed to query virtual hand themes:', e);
    }
  };

  useEffect(() => {
    fetchThemes();
  }, []);

  const handleSelectTheme = async (themeId: string) => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/virtual-hand/themes/active', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme_id: themeId }),
      });
      const data = await res.json();
      if (data.success) {
        setStatusMessage({ text: 'Active Virtual Hand theme updated!', type: 'success' });
        await fetchThemes();
      } else {
        setStatusMessage({ text: data.error || 'Failed to switch theme.', type: 'error' });
      }
    } catch (err: any) {
      setStatusMessage({ text: `Network error: ${err.message}`, type: 'error' });
    }
  };

  const handleUpdateSettings = async (partialSettings: Partial<ThemeSettings>) => {
    if (!activeTheme) return;
    const newSettings: ThemeSettings = {
      ...activeTheme.settings,
      ...partialSettings,
    };

    // Optimistic local update
    setActiveTheme({ ...activeTheme, settings: newSettings });

    try {
      await fetch('http://127.0.0.1:8000/api/virtual-hand/themes/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          theme_id: activeTheme.id,
          settings: newSettings,
        }),
      });
    } catch (e) {
      console.debug('Settings update error:', e);
    }
  };

  const handleDeleteTheme = async (themeId: string, themeName: string) => {
    if (!confirm(`Delete custom theme "${themeName}"?`)) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/virtual-hand/themes/${themeId}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      if (data.success) {
        setStatusMessage({ text: data.message || 'Theme deleted.', type: 'success' });
        await fetchThemes();
      } else {
        setStatusMessage({ text: data.error || 'Could not delete theme.', type: 'error' });
      }
    } catch (err: any) {
      setStatusMessage({ text: `Delete error: ${err.message}`, type: 'error' });
    }
  };

  const handleResetDefault = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/virtual-hand/themes/reset-default', {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        setStatusMessage({ text: 'Restored Kawaii Pixel Cat Paw as default hand!', type: 'success' });
        await fetchThemes();
      }
    } catch (err: any) {
      setStatusMessage({ text: `Reset error: ${err.message}`, type: 'error' });
    }
  };

  const handleTestGlide = async () => {
    setIsTestingGlide(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/virtual-hand/test-glide', {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        setStatusMessage({ text: '🐾 Look at your screen! AURA\'s Virtual Hand is gliding!', type: 'success' });
      }
    } catch (err: any) {
      setStatusMessage({ text: `Test glide error: ${err.message}`, type: 'error' });
    } finally {
      setTimeout(() => setIsTestingGlide(false), 1200);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const file = files[0];

    setIsUploading(true);
    setStatusMessage(null);

    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const base64Data = (reader.result as string) || '';
        const payload = {
          filename: file.name,
          custom_name: customThemeName.trim() || undefined,
          content_base64: base64Data,
        };

        const res = await fetch('http://127.0.0.1:8000/api/virtual-hand/themes/upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        const data = await res.json();
        if (data.success) {
          setStatusMessage({
            text: `✨ Successfully imported "${data.theme?.name || file.name}"!`,
            type: 'success',
          });
          setCustomThemeName('');
          if (fileInputRef.current) fileInputRef.current.value = '';
          await fetchThemes();
        } else {
          setStatusMessage({
            text: data.error || 'Failed to import cursor skin package.',
            type: 'error',
          });
        }
      } catch (err: any) {
        setStatusMessage({ text: `Upload failed: ${err.message}`, type: 'error' });
      } finally {
        setIsUploading(false);
      }
    };

    reader.onerror = () => {
      setStatusMessage({ text: 'Error reading uploaded file.', type: 'error' });
      setIsUploading(false);
    };

    reader.readAsDataURL(file);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Title & Badge */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Hand size={18} color="var(--accent, #eb5e28)" />
          <span style={{ fontWeight: 700, fontSize: '14px', color: 'var(--text, #252422)' }}>
            AURA Independent Virtual Hand & Skin Library
          </span>
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
            DESKTOP ASSISTANT HAND
          </span>
        </div>

        <button
          onClick={handleTestGlide}
          disabled={isTestingGlide}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: isTestingGlide ? 'rgba(235, 94, 40, 0.15)' : 'var(--accent, #eb5e28)',
            color: '#fff',
            border: 'none',
            borderRadius: '8px',
            padding: '6px 12px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: isTestingGlide ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s ease',
          }}
          title="Watch AURA's virtual hand glide and click on your desktop in real-time"
        >
          <Play size={13} fill="#fff" />
          <span>{isTestingGlide ? 'Gliding...' : 'Test Virtual Hand Glide'}</span>
        </button>
      </div>

      {/* Explanatory Distinction Banner */}
      <div
        style={{
          padding: '10px 14px',
          borderRadius: '10px',
          backgroundColor: 'rgba(59, 130, 246, 0.05)',
          border: '1px solid rgba(59, 130, 246, 0.18)',
          fontSize: '12px',
          color: '#1e293b',
          lineHeight: '1.5',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: '#2563eb' }}>
          <HelpCircle size={14} />
          <span>Two Distinct Cursors:</span>
        </div>
        <div style={{ paddingLeft: '20px' }}>
          • <strong>Your Mouse Cursor:</strong> Your personal Windows mouse pointer is never changed. It remains standard system arrow.<br />
          • <strong>AURA Assistant Hand:</strong> A transparent virtual overlay (Kawaii Pixel Cat Paw) that appears only when AURA performs automated desktop tasks, and hides when finished.
        </div>
      </div>

      {statusMessage && (
        <div
          style={{
            padding: '8px 12px',
            borderRadius: '8px',
            fontSize: '12px',
            backgroundColor: statusMessage.type === 'success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            color: statusMessage.type === 'success' ? '#10b981' : '#ef4444',
            border: `1px solid ${statusMessage.type === 'success' ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)'}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>{statusMessage.text}</span>
          <button
            onClick={() => setStatusMessage(null)}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '14px' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Theme Library Grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--muted, #64748b)' }}>
          Installed Virtual Hand Skins ({themes.length})
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: '10px' }}>
          {themes.map((theme) => {
            const isSelected = theme.is_active;
            return (
              <div
                key={theme.id}
                onClick={() => handleSelectTheme(theme.id)}
                style={{
                  padding: '12px',
                  borderRadius: '10px',
                  border: isSelected ? '2px solid var(--accent, #eb5e28)' : '1px solid var(--line, #e2e8f0)',
                  backgroundColor: isSelected ? 'rgba(235, 94, 40, 0.04)' : '#fff',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  position: 'relative',
                  transition: 'all 0.15s ease',
                  boxShadow: isSelected ? '0 2px 8px rgba(235, 94, 40, 0.12)' : 'none',
                }}
              >
                {/* Theme Preview Image */}
                <div
                  style={{
                    width: '44px',
                    height: '44px',
                    borderRadius: '8px',
                    backgroundColor: 'rgba(0, 0, 0, 0.03)',
                    border: '1px solid rgba(0, 0, 0, 0.06)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    overflow: 'hidden',
                    flexShrink: 0,
                  }}
                >
                  {theme.preview ? (
                    <img
                      src={theme.preview}
                      alt={theme.name}
                      style={{
                        maxWidth: '36px',
                        maxHeight: '36px',
                        imageRendering: 'pixelated',
                        display: 'block',
                      }}
                    />
                  ) : (
                    <Hand size={22} color="var(--muted, #64748b)" />
                  )}
                </div>

                {/* Theme Info */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: '13px',
                      fontWeight: 600,
                      color: 'var(--text, #252422)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {theme.name}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--muted, #64748b)' }}>
                    {theme.is_builtin ? '✨ Official Default' : theme.author || 'Custom Skin'}
                  </div>
                </div>

                {/* Status indicator / delete */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {isSelected && <Check size={16} color="var(--accent, #eb5e28)" />}
                  {!theme.is_builtin && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteTheme(theme.id, theme.name);
                      }}
                      style={{
                        background: 'none',
                        border: 'none',
                        padding: '4px',
                        color: 'var(--muted, #94a3b8)',
                        cursor: 'pointer',
                        borderRadius: '4px',
                      }}
                      title="Delete custom theme"
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Active Theme Customizer Controls */}
      {activeTheme && (
        <div
          style={{
            padding: '14px',
            borderRadius: '10px',
            backgroundColor: '#fff',
            border: '1px solid var(--line, #e2e8f0)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: 600 }}>
              <Sliders size={15} color="var(--accent, #eb5e28)" />
              <span>Customize Active Hand: {activeTheme.name}</span>
            </div>

            <button
              onClick={handleResetDefault}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                background: 'none',
                border: 'none',
                color: 'var(--muted, #64748b)',
                fontSize: '11px',
                cursor: 'pointer',
              }}
            >
              <RotateCcw size={12} />
              <span>Restore Default</span>
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            {/* Size Slider */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--muted, #64748b)' }}>
                <span>Hand Size</span>
                <span>{activeTheme.settings.size || 44}px</span>
              </div>
              <input
                type="range"
                min="24"
                max="72"
                step="2"
                value={activeTheme.settings.size || 44}
                onChange={(e) => handleUpdateSettings({ size: Number(e.target.value) })}
                style={{ width: '100%', accentColor: 'var(--accent, #eb5e28)' }}
              />
            </div>

            {/* Animation Toggle */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--muted, #64748b)' }}>
                <span>Animated Cat Paw Frames</span>
                <span>{activeTheme.settings.animated ? 'Active' : 'Static'}</span>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '12px' }}>
                <input
                  type="checkbox"
                  checked={Boolean(activeTheme.settings.animated)}
                  onChange={(e) => handleUpdateSettings({ animated: e.target.checked })}
                  style={{ accentColor: 'var(--accent, #eb5e28)', width: '16px', height: '16px' }}
                />
                <span>Preserve continuous sprite animation</span>
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Upload Custom Cursor Skin Section */}
      <div
        style={{
          padding: '14px',
          borderRadius: '10px',
          backgroundColor: '#fff',
          border: '1px dashed var(--line, #cbd5e1)',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: 600 }}>
          <Upload size={15} color="var(--accent, #eb5e28)" />
          <span>Upload Custom Virtual Hand Skin</span>
        </div>

        <div style={{ fontSize: '11px', color: 'var(--muted, #64748b)', lineHeight: '1.4' }}>
          Upload downloaded cursor skins (e.g. from Sweezy Cursors, OpenDesktop, or cursor packs). Supported formats:{' '}
          <strong>.zip, .ani, .cur, .gif, .png, .webp</strong>. Archives are pre-scanned and sanitized.
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="Custom theme name (optional)"
            value={customThemeName}
            onChange={(e) => setCustomThemeName(e.target.value)}
            style={{
              flex: 1,
              padding: '7px 10px',
              borderRadius: '6px',
              border: '1px solid var(--line, #cbd5e1)',
              fontSize: '12px',
              outline: 'none',
            }}
          />

          <input
            ref={fileInputRef}
            type="file"
            accept=".zip,.ani,.cur,.gif,.png,.webp,.apng"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: isUploading ? 'rgba(0,0,0,0.1)' : 'var(--accent, #eb5e28)',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              padding: '7px 14px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: isUploading ? 'not-allowed' : 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            <Upload size={13} />
            <span>{isUploading ? 'Importing...' : 'Select File or ZIP'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default VirtualHandSettings;
