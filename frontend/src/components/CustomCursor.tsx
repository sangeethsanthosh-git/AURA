import React, { useEffect } from 'react';
import {
  CURSOR_32_PNG,
  POINTER_32_PNG,
  CURSOR_48_PNG,
  POINTER_48_PNG,
} from '../assets/cursorBase64';

export interface CursorConfig {
  theme: 'default' | 'kawaii_cat_paw';
  animated: boolean;
  size: 32 | 48 | 64;
}

interface CustomCursorProps {
  config: CursorConfig;
}

export const CustomCursor: React.FC<CustomCursorProps> = ({ config }) => {
  const { theme, size } = config;
  const isEnabled = theme === 'kawaii_cat_paw';

  useEffect(() => {
    if (!isEnabled) {
      document.body.classList.remove('aura-custom-cursor-active');
      return;
    }

    document.body.classList.add('aura-custom-cursor-active');
    return () => {
      document.body.classList.remove('aura-custom-cursor-active');
    };
  }, [isEnabled]);

  // Hotspots for CSS native cursor
  const cursorPng = size >= 48 ? CURSOR_48_PNG : CURSOR_32_PNG;
  const pointerPng = size >= 48 ? POINTER_48_PNG : POINTER_32_PNG;
  const arrowHotspot = size >= 48 ? '3 3' : '2 2';
  const pointerHotspot = size >= 48 ? '18 6' : '12 4';

  if (!isEnabled) return null;

  return (
    <>
      {/* 
        Native Hardware Cursor Injection:
        Uses embedded base64 data URIs so it works with 0 latency, 0 flickering, 
        and works flawlessly across file://, http://, and Electron protocols.
      */}
      <style>{`
        body.aura-custom-cursor-active {
          cursor: url("${cursorPng}") ${arrowHotspot}, auto !important;
        }
        body.aura-custom-cursor-active button,
        body.aura-custom-cursor-active a,
        body.aura-custom-cursor-active [role="button"],
        body.aura-custom-cursor-active .pill,
        body.aura-custom-cursor-active select,
        body.aura-custom-cursor-active .cursor-pointer {
          cursor: url("${pointerPng}") ${pointerHotspot}, pointer !important;
        }
        body.aura-custom-cursor-active input[type="text"],
        body.aura-custom-cursor-active input[type="search"],
        body.aura-custom-cursor-active input[type="email"],
        body.aura-custom-cursor-active input[type="number"],
        body.aura-custom-cursor-active input[type="password"],
        body.aura-custom-cursor-active textarea,
        body.aura-custom-cursor-active [contenteditable] {
          cursor: text !important;
        }
        body.aura-custom-cursor-active [style*="resize"],
        body.aura-custom-cursor-active [class*="resize"] {
          cursor: auto !important;
        }
      `}</style>

      {/* Native Hardware Cursor: 0 flickering, instant 0ms hardware response */}
    </>
  );
};

export default CustomCursor;
