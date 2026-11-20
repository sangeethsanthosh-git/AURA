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
    const styleId = 'aura-custom-cursor-style';
    let styleEl = document.getElementById(styleId) as HTMLStyleElement | null;

    if (!isEnabled) {
      document.body.classList.remove('aura-custom-cursor-active');
      if (styleEl) styleEl.remove();
      return;
    }

    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.id = styleId;
      document.head.appendChild(styleEl);
    }

    const cursorPng = size >= 48 ? CURSOR_48_PNG : CURSOR_32_PNG;
    const pointerPng = size >= 48 ? POINTER_48_PNG : POINTER_32_PNG;
    const arrowHotspot = size >= 48 ? '3 3' : '2 2';
    const pointerHotspot = size >= 48 ? '18 6' : '12 4';

    styleEl.textContent = `
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
    `;

    document.body.classList.add('aura-custom-cursor-active');

    return () => {
      document.body.classList.remove('aura-custom-cursor-active');
      const el = document.getElementById(styleId);
      if (el) el.remove();
    };
  }, [isEnabled, size]);

  return null;
};

export default CustomCursor;
