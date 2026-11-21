import React, { useState, useEffect, useRef, useCallback } from 'react';
import { WikiKnowledgeCard } from './components/WikiKnowledgeCard';
import { ActionCard } from './components/ActionCard';
import { ClaraCompanion, MOOD_LABELS } from './components/ClaraCompanion';
import { SetupWizard } from './components/SetupWizard';
import { SecurityDashboard } from './components/SecurityDashboard';
import { CustomCursor, type CursorConfig } from './components/CustomCursor';
import { VirtualHandSettings } from './components/VirtualHandSettings';
import { playTapSound, playGiggleSound, getRandomGiggle, vocalizeGiggle, spawnTapSparkles } from './utils/companionAudio';
import type { SystemAction, CompanionType, ConversationMode, WikiResult, MessageItem, ModelProfile, VoiceOption, AssistantState } from './types';

const AVAILABLE_MODELS: ModelProfile[] = [
  {
    id: 'llama3.2:3b',
    name: 'Llama 3.2 (3B)',
    desc: 'Balanced conversational reasoning · 2.0 GB',
    badge: 'Recommended',
    tag: 'balanced',
  },
  {
    id: 'qwen3:1.7b',
    name: 'Qwen 3 (1.7B)',
    desc: 'Ultra-fast sub-second token latency · 1.4 GB',
    badge: 'Fastest',
    tag: 'fast',
  },
  {
    id: 'qwen2.5-coder:3b',
    name: 'Qwen 2.5 Coder (3B)',
    desc: 'Optimized for scripts, debugging & code · 1.9 GB',
    badge: 'Coding',
    tag: 'coder',
  },
  {
    id: 'dolphin3:8b',
    name: 'Dolphin 3 (8B)',
    desc: 'High-capability general knowledge · 4.9 GB',
    badge: 'Large',
    tag: 'large',
  },
  {
    id: 'gemma3:1b',
    name: 'Gemma 3 (1B)',
    desc: 'Minimal RAM footprint · 815 MB',
    badge: 'Lightweight',
    tag: 'lite',
  },
  {
    id: 'gemma3:4b',
    name: 'Gemma 3 (4B)',
    desc: 'Google multilingual multimodal model · 3.3 GB',
    badge: 'Multimodal',
    tag: 'multimodal',
  },
];

const AVAILABLE_VOICES: VoiceOption[] = [
  { id: 'aria', name: 'Aria', label: 'Serena (Aria)', sub: 'Warm · female', gender: 'Female', engine: 'Neural' },
  { id: 'guy', name: 'Guy', label: 'Guy', sub: 'Natural · American male', gender: 'Male', engine: 'Neural' },
  { id: 'jenny', name: 'Jenny', label: 'Vivian (Jenny)', sub: 'Bright · engaging female', gender: 'Female', engine: 'Neural' },
  { id: 'ryan', name: 'Ryan', label: 'Ryan', sub: 'Natural · British male', gender: 'Male', engine: 'Neural' },
  { id: 'eric', name: 'Eric', label: 'Aiden (Eric)', sub: 'Casual · male', gender: 'Male', engine: 'Neural' },
  { id: 'christopher', name: 'Christopher', label: 'Christopher', sub: 'Authoritative · male', gender: 'Male', engine: 'Neural' },
  { id: 'sonia', name: 'Sonia', label: 'Sonia', sub: 'Refined · British female', gender: 'Female', engine: 'Neural' },
  { id: 'piper', name: 'Piper', label: 'Piper (Lessac)', sub: 'Offline local ONNX · 0 latency', gender: 'Female', engine: 'Local ONNX' },
];

export function App() {
  const [state, setState] = useState<AssistantState>('idle');
  const [wakeOn, setWakeOn] = useState<boolean>(false);
  const [deepSearchOn, setDeepSearchOn] = useState<boolean>(true);
  const [isLive, setIsLive] = useState<boolean>(false);
  const [companion, setCompanion] = useState<CompanionType>(() => {
    try {
      return (localStorage.getItem('auraChar') as CompanionType) || 'ember';
    } catch {
      return 'ember';
    }
  });

  const [conversationMode, setConversationMode] = useState<ConversationMode>(() => {
    try {
      return (localStorage.getItem('auraConversationMode') as ConversationMode) || 'companion';
    } catch {
      return 'companion';
    }
  });

  const [activeModel, setActiveModel] = useState<string>('llama3.2:3b');
  const [activeVoice, setActiveVoice] = useState<string>('Aria');
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [isSetupOpen, setIsSetupOpen] = useState<boolean>(() => !localStorage.getItem('aura_setup_completed'));
  const [isSecurityOpen, setIsSecurityOpen] = useState<boolean>(false);
  const [cursorConfig] = useState<CursorConfig>(() => {
    // User pointer inside AURA is the clean default system cursor; Kawaii Cat Paw is AURA's desktop claw
    localStorage.removeItem('aura_cursor_theme');
    const savedAnim = localStorage.getItem('aura_cursor_animated');
    const savedSize = localStorage.getItem('aura_cursor_size');
    return {
      theme: 'default',
      animated: savedAnim !== 'false',
      size: (savedSize === '48' ? 48 : savedSize === '64' ? 64 : 32) as 32 | 48 | 64,
    };
  });

  useEffect(() => {
    localStorage.setItem('aura_cursor_theme', cursorConfig.theme);
    localStorage.setItem('aura_cursor_animated', cursorConfig.animated ? 'true' : 'false');
    localStorage.setItem('aura_cursor_size', String(cursorConfig.size));
  }, [cursorConfig]);

  const [vramText, setVramText] = useState<string>('2.5 / 4.0 GB');
  const [vramPercent, setVramPercent] = useState<number>(62);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [bubbleText, setBubbleText] = useState<string>('…');
  const [inputText, setInputText] = useState<string>('');

  const [claraMood, setClaraMood] = useState<string>('neutral');
  const [claraDisplayMode, setClaraDisplayMode] = useState<'cutout' | 'portrait'>('cutout');
  const [liveAmp, setLiveAmp] = useState<number>(0);
  const isDesktopApp = typeof window !== 'undefined' && Boolean((window as any).electronAPI);

  useEffect(() => {
    document.body.dataset.display = claraDisplayMode;
  }, [claraDisplayMode]);

  const socketRef = useRef<WebSocket | null>(null);
  const chatStreamRef = useRef<HTMLDivElement | null>(null);
  const dialogueStreamRef = useRef<HTMLDivElement | null>(null);
  const txtRef = useRef<HTMLInputElement | null>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const companionRef = useRef<HTMLDivElement | null>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Drag physics refs
  const dragRef = useRef<{
    startX: number;
    startY: number;
    originX: number;
    originY: number;
    moved: boolean;
  } | null>(null);
  const posRef = useRef<{ dx: number; dy: number }>({ dx: 0, dy: 0 });
  const velocityRef = useRef<number>(0);

  // Mouse & Eye tracking refs
  const mouseRef = useRef<{ mx: number; my: number; ex: number; ey: number }>({
    mx: 0,
    my: 0,
    ex: 0,
    ey: 0,
  });
  const ampRef = useRef<{ amp: number; target: number }>({ amp: 0, target: 0.05 });
  const stateRef = useRef<AssistantState>(state);
  stateRef.current = state;
  const isLiveRef = useRef<boolean>(isLive);
  isLiveRef.current = isLive;

  // Human-like typewriter cadence refs
  const typewriterTargetRef = useRef<string>('');
  const typewriterDisplayedRef = useRef<string>('');
  const typewriterTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const currentStreamIdRef = useRef<string | null>(null);
  const pendingTextRef = useRef<string | null>(null);

  // Whether user has sent messages in this session
  const hasMessages = messages.some((m) => m.role === 'user');

  // Initialize saved companion position
  useEffect(() => {
    try {
      const saved = localStorage.getItem('auraPos');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
          posRef.current = { dx: parsed.x, dy: parsed.y };
          if (companionRef.current) {
            companionRef.current.style.setProperty('--dx', `${parsed.x}px`);
            companionRef.current.style.setProperty('--dy', `${parsed.y}px`);
          }
        }
      }
    } catch {}
  }, []);

  // Update companion in DOM body
  useEffect(() => {
    document.body.dataset.char = companion;
    try {
      localStorage.setItem('auraChar', companion);
    } catch {}
  }, [companion]);

  // Initial welcome message
  useEffect(() => {
    const welcome =
      companion === 'clara'
        ? "Good evening! I'm Clara. What are we exploring today?"
        : `Hi, I'm ${companion === 'ember' ? 'Ember' : 'Frost'}, AURA's companion. Press Space or say “Hey AURA” to start.`;
    setBubbleText(welcome);
  }, [companion]);

  // Smooth scroll chat streams when messages or state change
  useEffect(() => {
    if (chatStreamRef.current) {
      chatStreamRef.current.scrollTo({
        top: chatStreamRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
    if (dialogueStreamRef.current) {
      dialogueStreamRef.current.scrollTo({
        top: dialogueStreamRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages.length, messages, state]);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (typewriterTimeoutRef.current) {
      clearTimeout(typewriterTimeoutRef.current);
      typewriterTimeoutRef.current = null;
    }
    typewriterTargetRef.current = '';
    typewriterDisplayedRef.current = '';
    currentStreamIdRef.current = null;
  }, []);

  // Organic human-like typewriter animation with natural cadence pauses at punctuation
  const advanceTypewriter = useCallback((streamId: string) => {
    if (typewriterTimeoutRef.current) {
      clearTimeout(typewriterTimeoutRef.current);
      typewriterTimeoutRef.current = null;
    }

    const target = typewriterTargetRef.current;
    const current = typewriterDisplayedRef.current;

    if (current.length < target.length) {
      const remaining = target.length - current.length;
      const step = remaining > 50 ? 3 : remaining > 20 ? 2 : 1;
      const nextSlice = target.slice(0, current.length + step);
      typewriterDisplayedRef.current = nextSlice;

      setBubbleText(nextSlice);
      setMessages((prev) => {
        const idx = prev.findIndex((m) => m.id === streamId);
        if (idx !== -1) {
          const next = [...prev];
          next[idx] = { ...next[idx], text: nextSlice };
          return next;
        }
        return prev;
      });

      const lastChar = nextSlice.slice(-1);
      let delay = Math.floor(Math.random() * 14) + 16; // Base 16-30ms

      if (['.', '!', '?'].includes(lastChar)) {
        delay = remaining > 20 ? 70 : 160; // Sentence pause
      } else if ([',', ';', ':'].includes(lastChar)) {
        delay = remaining > 20 ? 40 : 90; // Clause pause
      } else if (lastChar === ' ') {
        delay = Math.floor(Math.random() * 10) + 18; // Word cadence
      }

      if (remaining > 50) {
        delay = 10; // Catch-up acceleration to keep sync with audio
      }

      typewriterTimeoutRef.current = setTimeout(() => advanceTypewriter(streamId), delay);
    }
  }, []);

  // Safe message adding with deduplication for consecutive or closely interleaved user, assistant, wiki, or action messages
  const addMsg = useCallback(
    (role: 'user' | 'aura', text: string, wiki?: WikiResult, action?: SystemAction) => {
      if (!text && !wiki && !action) return;
      if (role === 'aura' && text) {
        setBubbleText(text);
      }
      setMessages((prev) => {
        if (prev.length > 0) {
          const recent = prev.slice(-4);
          // Deduplicate Action Cards (prevents stacked duplicate system cards)
          if (action) {
            const isDupAction = recent.some(
              (m) =>
                m.action &&
                (m.action.title === action.title ||
                  (m.action.action === action.action && m.action.message === action.message))
            );
            if (isDupAction) {
              return prev;
            }
          }
          // Deduplicate Wiki Result Cards
          if (wiki) {
            const isDupWiki = recent.some(
              (m) => m.wiki && m.wiki.query.toLowerCase() === wiki.query.toLowerCase()
            );
            if (isDupWiki) {
              return prev;
            }
          }
          // Deduplicate Plain Text Messages
          if (!action && !wiki && text) {
            const isDupText = recent.some(
              (m) => m.role === role && !m.action && !m.wiki && m.text.trim().toLowerCase() === text.trim().toLowerCase()
            );
            if (isDupText) {
              return prev;
            }
          }
        }
        const id = `msg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
        return [...prev, { id, role, text, wiki, action }];
      });
    },
    []
  );

  // Reset back to Fresh Conversation
  const handleNewChat = useCallback(() => {
    clearTimers();
    setMessages([]);
    setState('idle');
    const greet =
      companion === 'clara'
        ? "Good evening! I'm Clara. What are we exploring today?"
        : `Hi, I'm ${companion === 'ember' ? 'Ember' : 'Frost'}, AURA's companion. Press Space or say “Hey AURA” to start.`;
    setBubbleText(greet);
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'new_conversation' }));
    }
  }, [clearTimers, companion]);

  const startListening = useCallback(() => {
    if (stateRef.current === 'speaking') return;
    clearTimers();
    setState('listening');
    setBubbleText("I'm listening…");
    if (isLiveRef.current && socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'start_listening' }));
    }
  }, [clearTimers]);

  const stopListening = useCallback(() => {
    if (stateRef.current !== 'listening') return;
    if (isLiveRef.current && socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'stop_listening' }));
      setState('thinking');
      setBubbleText('Hmm, let me think…');
    } else {
      setState('idle');
      setBubbleText("Connecting to AURA core…");
    }
  }, []);

  const togglePTT = useCallback(() => {
    if (stateRef.current === 'listening') {
      stopListening();
    } else {
      startListening();
    }
  }, [startListening, stopListening]);

  const sendText = useCallback(
    (customText?: string) => {
      const v = (customText !== undefined ? customText : inputText).trim();
      if (!v || stateRef.current === 'speaking' || stateRef.current === 'thinking') return;
      setInputText('');

      if (isLiveRef.current && socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        addMsg('user', v);
        socketRef.current.send(JSON.stringify({ type: 'send_text', text: v }));
        setState('thinking');
        setBubbleText('Hmm, let me think…');
      } else {
        // Queue pending text and show connecting state rather than static mock replies
        addMsg('user', v);
        setState('thinking');
        setBubbleText('Connecting to AURA background core…');
        pendingTextRef.current = v;
      }
    },
    [inputText, addMsg]
  );

  // WebSocket connection management
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    let isDisposed = false;

    const connect = () => {
      if (isDisposed) return;
      try {
        const host = typeof window !== 'undefined' && window.location.port === '8000'
          ? window.location.host
          : '127.0.0.1:8000';
        ws = new WebSocket(`ws://${host}/ws`);
        socketRef.current = ws;

        ws.onopen = () => {
          if (isDisposed) return;
          setIsLive(true);
          // If the user entered a command while connecting, dispatch it now!
          if (pendingTextRef.current) {
            const queued = pendingTextRef.current;
            pendingTextRef.current = null;
            ws?.send(JSON.stringify({ type: 'send_text', text: queued }));
            setState('thinking');
            setBubbleText('Hmm, let me think…');
          }
        };

        ws.onclose = ws.onerror = () => {
          if (isDisposed) return;
          setIsLive(false);
          reconnectTimeout = setTimeout(connect, 1000);
        };

        ws.onmessage = (event) => {
          if (isDisposed) return;
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'state' || data.type === 'state_change') {
              const s = String(data.state || '').toLowerCase();
              if (['idle', 'listening', 'thinking', 'speaking'].includes(s)) {
                setState(s as AssistantState);
              }
            } else if (data.type === 'status') {
              if (data.model) setActiveModel(data.model);
              if (data.voice) setActiveVoice(data.voice);
              if (data.wake_word !== undefined) setWakeOn(data.wake_word);
              if (data.deep_search !== undefined) setDeepSearchOn(data.deep_search);
              if (typeof data.vram_used === 'number' && typeof data.vram_total === 'number') {
                setVramText(`${data.vram_used.toFixed(1)} / ${data.vram_total.toFixed(1)} GB`);
                setVramPercent(Math.round((data.vram_used / data.vram_total) * 100));
              }
              if (data.companion_mood) {
                setClaraMood(data.companion_mood);
              }
            } else if (data.type === 'personality_update') {
              if (data.mood) setClaraMood(data.mood);
            } else if (data.type === 'companion_mood') {
              if (data.mood) setClaraMood(data.mood);
            } else if (data.type === 'model_updated') {
              if (data.model) setActiveModel(data.model);
            } else if (data.type === 'voice_updated') {
              if (data.voice) setActiveVoice(data.voice);
            } else if (data.type === 'deep_search_status') {
              if (data.active !== undefined) setDeepSearchOn(data.active);
            } else if (data.type === 'wake_word_status') {
              if (data.active !== undefined) setWakeOn(data.active);
            } else if (data.type === 'wiki_results') {
              const wikiPayload: WikiResult = {
                query: data.query || '',
                articles: Array.isArray(data.articles) ? data.articles : [],
                images: Array.isArray(data.images) ? data.images : [],
              };
              addMsg('aura', '', wikiPayload);
            } else if (data.type === 'system_action') {
              const actionPayload: SystemAction = {
                action: data.action,
                tool_type: data.tool_type,
                title: data.title,
                message: data.message,
                spoken_response: data.spoken_response,
                data: data.data || {},
              };
              addMsg('aura', '', undefined, actionPayload);
            } else if (data.type === 'transcription' || (data.type === 'transcript' && data.role === 'user')) {
              const userTxt = (data.text || '').trim();
              if (userTxt) {
                addMsg('user', userTxt);
              }
            } else if (data.type === 'response_chunk') {
              const chunkTxt = data.text || '';
              if (chunkTxt) {
                typewriterTargetRef.current = chunkTxt;
                let sId = currentStreamIdRef.current;
                if (!sId) {
                  sId = `stream-${Date.now()}`;
                  currentStreamIdRef.current = sId;
                  typewriterDisplayedRef.current = '';
                  setMessages((prev) => [...prev, { id: sId!, role: 'aura', text: '', isStreaming: true }]);
                }
                advanceTypewriter(sId);
              }
            } else if (data.type === 'response' || (data.type === 'transcript' && data.role === 'assistant')) {
              const respTxt = (data.text || '').trim();
              if (respTxt) {
                typewriterTargetRef.current = respTxt;
                const sId = currentStreamIdRef.current;
                if (sId) {
                  advanceTypewriter(sId);
                  setTimeout(() => {
                    setBubbleText(respTxt);
                    setMessages((prev) =>
                      prev.map((m) => (m.id === sId ? { ...m, text: respTxt, isStreaming: false } : m))
                    );
                    currentStreamIdRef.current = null;
                  }, 180);
                } else {
                  setBubbleText(respTxt);
                  addMsg('aura', respTxt);
                }
              }
            } else if (data.type === 'level') {
              if (typeof data.value === 'number') {
                ampRef.current.target = data.value;
                setLiveAmp(data.value);
              }
            } else if (data.type === 'vram') {
              if (typeof data.used === 'number' && typeof data.total === 'number') {
                setVramText(`${data.used.toFixed(1)} / ${data.total.toFixed(1)} GB`);
                setVramPercent(Math.round((data.used / data.total) * 100));
              }
            } else if (data.type === 'timer_expired') {
              const actionPayload: SystemAction = {
                action: 'timer',
                tool_type: 'expired',
                title: `Timer Finished: ${data.title || 'Timer'}`,
                message: `Your timer for ${data.title || 'Timer'} is complete!`,
                spoken_response: `Your timer for ${data.title || 'Timer'} is complete.`,
                data: { action: 'expired', title: data.title, duration_seconds: data.duration_seconds },
              };
              addMsg('aura', '', undefined, actionPayload);
            }
          } catch {}
        };
      } catch {
        reconnectTimeout = setTimeout(connect, 4000);
      }
    };

    connect();

    return () => {
      isDisposed = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) {
        ws.close();
      }
    };
  }, [addMsg]);

  // Spacebar hotkey listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && document.activeElement !== txtRef.current && !e.repeat && !isSettingsOpen) {
        e.preventDefault();
        togglePTT();
      }
      if (e.code === 'Escape' && isSettingsOpen) {
        setIsSettingsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [togglePTT, isSettingsOpen]);

  // Phase 11: Electron Global Hotkey listener (Ctrl+Shift+Space, Alt+A)
  useEffect(() => {
    const electronAPI = (window as any).electronAPI;
    if (electronAPI?.onGlobalHotkey) {
      electronAPI.onGlobalHotkey((payload: { action: string; source?: string }) => {
        if (payload.action === 'toggle-listen') {
          if (stateRef.current === 'idle') {
            startListening();
          } else if (stateRef.current === 'listening') {
            stopListening();
          } else if (stateRef.current === 'speaking' || stateRef.current === 'thinking') {
            stopListening();
          }
        } else if (payload.action === 'toggle-wake-word') {
          setWakeOn((prev) => {
            const next = !prev;
            if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
              socketRef.current.send(JSON.stringify({ type: 'toggle_wake_word', enabled: next }));
            }
            return next;
          });
        }
      });
    }
  }, [startListening, stopListening]);

  // Mouse move eye-tracking listener
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const mx = Math.max(-4, Math.min(4, (e.clientX / window.innerWidth - 0.5) * 10));
      const my = Math.max(-3, Math.min(3, (e.clientY / window.innerHeight - 0.5) * 8));
      mouseRef.current.mx = mx;
      mouseRef.current.my = my;
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // RequestAnimationFrame physics loop (optimized with delta-checks and visibility throttling)
  useEffect(() => {
    let animId: number;
    let lastAmpStr = '';
    let lastMouthStr = '';
    let lastExStr = '';
    let lastEyStr = '';
    let lastSwayStr = '';

    const loop = (t: number) => {
      // Pause computation and DOM style mutations when window is minimized or hidden
      if (document.hidden) {
        animId = requestAnimationFrame(loop);
        return;
      }

      const currentState = stateRef.current;

      let target = 0.05 + (Math.sin(t / 900) + 1) * 0.04;
      if (currentState === 'listening') {
        target = 0.35 + Math.abs(Math.sin(t / 160) * Math.sin(t / 410)) * 0.65;
      } else if (currentState === 'speaking') {
        target = 0.25 + Math.abs(Math.sin(t / 120) * Math.cos(t / 330)) * 0.75;
      } else if (currentState === 'thinking') {
        target = 0.15;
      }

      ampRef.current.amp += (target - ampRef.current.amp) * 0.18;
      const currentAmp = ampRef.current.amp;

      const root = document.documentElement.style;
      const ampStr = currentAmp.toFixed(2);
      if (ampStr !== lastAmpStr) {
        root.setProperty('--amp', ampStr);
        lastAmpStr = ampStr;
      }

      const mouthStr = (0.25 + currentAmp * 0.9).toFixed(2);
      if (mouthStr !== lastMouthStr) {
        root.setProperty('--mouth', mouthStr);
        lastMouthStr = mouthStr;
      }

      const tx = currentState === 'thinking' ? -4 + Math.sin(t / 500) * 2 : mouseRef.current.mx;
      const ty = currentState === 'thinking' ? -4 : mouseRef.current.my;

      mouseRef.current.ex += (tx - mouseRef.current.ex) * 0.12;
      mouseRef.current.ey += (ty - mouseRef.current.ey) * 0.12;

      const exStr = mouseRef.current.ex.toFixed(1);
      if (exStr !== lastExStr) {
        root.setProperty('--ex', exStr);
        lastExStr = exStr;
      }

      const eyStr = mouseRef.current.ey.toFixed(1);
      if (eyStr !== lastEyStr) {
        root.setProperty('--ey', eyStr);
        lastEyStr = eyStr;
      }

      velocityRef.current *= 0.88;
      const swayStr = velocityRef.current.toFixed(1);
      if (swayStr !== lastSwayStr) {
        root.setProperty('--sway', swayStr);
        lastSwayStr = swayStr;
      }

      animId = requestAnimationFrame(loop);
    };

    animId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animId);
  }, []);

  // Drag and drop physics for companion
  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      originX: posRef.current.dx,
      originY: posRef.current.dy,
      moved: false,
    };
    wrap.setPointerCapture(e.pointerId);
    wrap.classList.add('dragging');
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragRef.current || !companionRef.current) return;
    const drag = dragRef.current;
    const deltaX = e.clientX - drag.startX;
    const deltaY = e.clientY - drag.startY;

    if (Math.abs(deltaX) + Math.abs(deltaY) > 4) {
      drag.moved = true;
    }

    const maxLimitX = Math.max(0, window.innerWidth / 2 - 120);
    const maxLimitY = Math.max(0, window.innerHeight * 0.38);

    const nextX = Math.max(-maxLimitX, Math.min(maxLimitX, drag.originX + deltaX));
    const nextY = Math.max(-maxLimitY, Math.min(maxLimitY, drag.originY + deltaY));

    velocityRef.current = Math.max(-14, Math.min(14, velocityRef.current + (nextX - posRef.current.dx) * 0.6));
    posRef.current = { dx: nextX, dy: nextY };

    companionRef.current.style.setProperty('--dx', `${nextX}px`);
    companionRef.current.style.setProperty('--dy', `${nextY}px`);
  };

  const handlePointerUp = () => {
    const wrap = wrapRef.current;
    if (!wrap || !dragRef.current) return;
    wrap.classList.remove('dragging');

    if (!dragRef.current.moved) {
      const tapX = dragRef.current.startX;
      const tapY = dragRef.current.startY;

      // 1. Play tactile tap/poke sound
      playTapSound(companion);

      // 2. Spawn cheerful floating hearts & sparkles from tap point
      spawnTapSparkles(tapX, tapY);

      wrap.classList.remove('poke');
      void wrap.offsetWidth;
      wrap.classList.add('poke');

      // 3. Play musical giggle chime audio after slight pause
      setTimeout(() => {
        playGiggleSound(companion);
      }, 100);

      const giggleText = getRandomGiggle(companion);

      if (companion === 'clara') {
        // Clara: Surprise gasp -> joyful giggling laugh with blushing cheeks!
        setClaraMood('surprised');
        setBubbleText("Oh! Hehe!");
        setTimeout(() => {
          wrap.classList.remove('poke');
          setClaraMood('laugh');
          setBubbleText(giggleText);
          vocalizeGiggle(giggleText, 'clara');
          setTimeout(() => setClaraMood('happy'), 2200);
          setTimeout(() => setClaraMood('neutral'), 4200);
        }, 500);
      } else if (companion === 'ember') {
        setBubbleText(giggleText);
        vocalizeGiggle(giggleText, 'ember');
        setTimeout(() => wrap.classList.remove('poke'), 600);
      } else {
        setBubbleText(giggleText);
        vocalizeGiggle(giggleText, 'frost');
        setTimeout(() => wrap.classList.remove('poke'), 600);
      }
    } else {
      try {
        localStorage.setItem('auraPos', JSON.stringify({ x: posRef.current.dx, y: posRef.current.dy }));
      } catch {}
    }
    dragRef.current = null;
  };

  const handleDoubleClick = () => {
    posRef.current = { dx: 0, dy: 0 };
    if (companionRef.current) {
      companionRef.current.style.setProperty('--dx', '0px');
      companionRef.current.style.setProperty('--dy', '0px');
    }
    try {
      localStorage.setItem('auraPos', JSON.stringify({ x: 0, y: 0 }));
    } catch {}
  };

  const handleSwitchCompanion = (chosen?: CompanionType) => {
    const nextChar: CompanionType = chosen
      ? chosen
      : companion === 'ember'
      ? 'frost'
      : companion === 'frost'
      ? 'clara'
      : 'ember';
    setCompanion(nextChar);
    try {
      localStorage.setItem('auraChar', nextChar);
    } catch {}

    const charName = nextChar === 'ember' ? 'Ember' : nextChar === 'frost' ? 'Frost' : 'Clara';
    const greet =
      nextChar === 'clara'
        ? "Good evening! I'm Clara. What are we exploring today?"
        : `Hi, I'm ${charName}!`;
    setBubbleText(greet);

    const wrap = wrapRef.current;
    if (wrap) {
      wrap.classList.remove('poke');
      void wrap.offsetWidth;
      wrap.classList.add('poke');
      setTimeout(() => wrap.classList.remove('poke'), 600);
    }
  };

  const handleToggleMode = (mode?: ConversationMode) => {
    const nextMode: ConversationMode = mode
      ? mode
      : conversationMode === 'companion'
      ? 'stream'
      : 'companion';
    setConversationMode(nextMode);
    try {
      localStorage.setItem('auraConversationMode', nextMode);
    } catch {}
  };

  const handleToggleWake = () => {
    const next = !wakeOn;
    setWakeOn(next);
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'toggle_wake_word', enabled: next }));
    }
  };

  const handleToggleDeepSearch = () => {
    const next = !deepSearchOn;
    setDeepSearchOn(next);
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'toggle_deep_search', enabled: next }));
    }
  };

  const handleSelectModel = (modelId: string) => {
    setActiveModel(modelId);
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'set_model', model: modelId }));
    }
  };

  const handleSelectVoice = (name: string) => {
    setActiveVoice(name);
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'set_voice', voice: name }));
    }
  };

  // Greeting by hour
  const getGreetingHtml = () => {
    const h = new Date().getHours();
    const g = h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
    switch (state) {
      case 'listening':
        return "<span>Go ahead,</span> I'm all ears.";
      case 'thinking':
        return 'Let me <span>think</span>…';
      case 'speaking':
        return "<span>Here's</span> what I found.";
      case 'idle':
      default:
        return `${g}. <span>I'm listening.</span>`;
    }
  };

  const getStatusText = () => {
    switch (state) {
      case 'listening':
        return 'Listening…';
      case 'thinking':
        return 'Thinking…';
      case 'speaking':
        return 'Speaking…';
      case 'idle':
      default:
        return wakeOn ? 'Say “Hey AURA” or press Space' : 'Press Space to talk';
    }
  };

  // Dedicated Render function for the animated companion stage
  const renderCompanionStage = () => (
    <div className="companion" id="companion" ref={companionRef}>
      <div className="bubble">
        <span id="bubbleTxt">
          {bubbleText}
          {(state === 'thinking' || messages.some((m) => m.role === 'aura' && m.isStreaming)) && (
            <span className="typing-cursor">▊</span>
          )}
        </span>
      </div>

      <div
        className={`orb-wrap ${companion === 'clara' ? 'is-clara' : ''}`}
        id="orbWrap"
        ref={wrapRef}
        title="Drag me around · double-click to reset"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onDoubleClick={handleDoubleClick}
      >
        <div className="halo"></div>

        {/* Clara Companion (Master 2.5D Rigged Companion) */}
        {companion === 'clara' && (
          <ClaraCompanion
            state={state}
            speechText={bubbleText}
            amp={liveAmp}
            activeMood={claraMood}
            className="char clara"
          />
        )}

        {/* Ember Companion SVG (Animated Flame) */}
        {companion === 'ember' && (
          <svg
            className="char ember"
            viewBox="0 0 200 260"
            xmlns="http://www.w3.org/2000/svg"
            aria-label="Ember, AURA's companion"
          >
            <defs>
              <radialGradient id="gb" cx="50%" cy="30%" r="75%">
                <stop offset="0" stopColor="#ffc25a" />
                <stop offset=".5" stopColor="#f46a2a" />
                <stop offset="1" stopColor="#a9231d" />
              </radialGradient>
              <linearGradient id="ga" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#f4622a" />
                <stop offset="1" stopColor="#b8261f" />
              </linearGradient>
              <linearGradient id="gf" x1="0" y1="1" x2="0" y2="0">
                <stop offset="0" stopColor="#f0452a" />
                <stop offset=".6" stopColor="#ff8a2e" />
                <stop offset="1" stopColor="#ffc24a" />
              </linearGradient>
              <linearGradient id="gi" x1="0" y1="1" x2="0" y2="0">
                <stop offset="0" stopColor="#ffb23a" />
                <stop offset="1" stopColor="#fff0a0" />
              </linearGradient>
            </defs>
            <ellipse cx="100" cy="247" rx="52" ry="7" fill="rgba(120,50,20,.18)" />
            <g className="flamewrap">
              <g className="flame">
                <path
                  fill="url(#gf)"
                  d="M72 118 C58 95 78 80 84 60 C88 45 98 35 102 14 C112 38 118 48 122 62 C128 78 148 92 130 118 C115 128 87 128 72 118Z"
                >
                  <animate
                    attributeName="d"
                    dur="2.6s"
                    repeatCount="indefinite"
                    values="M72 118 C58 95 78 80 84 60 C88 45 98 35 102 14 C112 38 118 48 122 62 C128 78 148 92 130 118 C115 128 87 128 72 118Z;
                            M72 118 C54 98 82 82 80 62 C80 44 90 34 98 10 C110 34 124 50 126 64 C130 80 146 96 130 118 C115 128 87 128 72 118Z;
                            M72 118 C60 92 74 78 88 58 C94 44 104 32 108 16 C114 38 112 50 118 62 C132 76 150 94 130 118 C115 128 87 128 72 118Z;
                            M72 118 C58 95 78 80 84 60 C88 45 98 35 102 14 C112 38 118 48 122 62 C128 78 148 92 130 118 C115 128 87 128 72 118Z"
                  />
                </path>
                <path
                  className="inner"
                  fill="url(#gi)"
                  d="M88 116 C80 100 92 92 96 78 C98 68 102 62 104 50 C110 66 114 74 116 84 C120 96 124 106 114 116 C106 122 94 122 88 116Z"
                />
              </g>
            </g>
            <path d="M60 150 C42 158 40 188 52 202 C60 206 66 196 66 186Z" fill="url(#ga)" />
            <path d="M140 150 C158 158 160 188 148 202 C140 206 134 196 134 186Z" fill="url(#ga)" />
            <path
              d="M58 160 C52 128 70 106 100 106 C130 106 148 128 142 160 C150 176 148 206 140 226 C134 244 114 244 108 228 C105 220 95 220 92 228 C86 244 66 244 60 226 C52 206 50 176 58 160Z"
              fill="url(#gb)"
            />
            <ellipse cx="100" cy="160" rx="34" ry="26" fill="#ffd27a" opacity=".22" />
            <circle cx="76" cy="205" r="2" fill="#ffc25a" opacity=".7" />
            <circle cx="126" cy="198" r="2.4" fill="#ffc25a" opacity=".6" />
            <circle cx="112" cy="214" r="1.6" fill="#ffc25a" opacity=".7" />
            <g className="eyes">
              <g className="look">
                <g className="eye e1">
                  <circle cx="82" cy="152" r="7.5" fill="#5a1420" />
                  <circle cx="84.5" cy="149.5" r="2" fill="#fff" opacity=".85" />
                </g>
                <g className="eye e2">
                  <circle cx="118" cy="152" r="7.5" fill="#5a1420" />
                  <circle cx="120.5" cy="149.5" r="2" fill="#fff" opacity=".85" />
                </g>
              </g>
            </g>
            <path
              className="smile"
              d="M92 172 Q100 179 108 172"
              fill="none"
              stroke="#7a1f1a"
              strokeWidth="2.6"
              strokeLinecap="round"
            />
            <ellipse className="mouth" cx="100" cy="174" rx="6.5" ry="6" fill="#5a1420" />
            <circle className="spark" cx="68" cy="70" r="2.6" fill="#ff8a2e" />
            <circle className="spark" cx="136" cy="62" r="2" fill="#ff6a2a" style={{ animationDelay: '1s' }} />
            <circle className="spark" cx="152" cy="98" r="2.2" fill="#ffb23a" style={{ animationDelay: '1.9s' }} />
            <circle className="spark" cx="54" cy="104" r="1.8" fill="#ffb23a" style={{ animationDelay: '2.4s' }} />
            <circle className="spark" cx="118" cy="34" r="1.8" fill="#ff8a2e" style={{ animationDelay: '.5s' }} />
          </svg>
        )}

        {/* Frost Companion SVG (Animated Robot) */}
        {companion === 'frost' && (
          <svg
            className="char frost"
            viewBox="0 0 200 260"
            xmlns="http://www.w3.org/2000/svg"
            aria-label="Frost, AURA's companion"
          >
            <defs>
              <linearGradient id="fl" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#2f66ee" />
                <stop offset=".55" stopColor="#3c8cf4" />
                <stop offset=".85" stopColor="#d9e8fb" />
                <stop offset="1" stopColor="#f1f6fe" />
              </linearGradient>
              <linearGradient id="fa" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#4f86f0" />
                <stop offset="1" stopColor="#dce9fc" />
              </linearGradient>
              <radialGradient id="fh" cx="40%" cy="55%" r="70%">
                <stop offset="0" stopColor="#2f5fe8" />
                <stop offset=".55" stopColor="#7fa6f4" />
                <stop offset="1" stopColor="#eaf1fd" />
              </radialGradient>
              <filter id="fs" x="-10%" y="-10%" width="120%" height="120%">
                <feGaussianBlur stdDeviation=".7" />
              </filter>
              <filter id="fb" x="-30%" y="-60%" width="160%" height="220%">
                <feGaussianBlur stdDeviation="3" />
              </filter>
            </defs>
            <ellipse cx="100" cy="248" rx="46" ry="6" fill="rgba(40,70,150,.16)" />
            {/* Legs */}
            <path d="M80 118 L97 118 L97 232 C97 240 90 244 78 244 C70 244 72 238 78 232 Z" fill="url(#fl)" filter="url(#fs)" />
            <path d="M120 118 L103 118 L103 232 C103 240 110 244 122 244 C130 244 128 238 122 232 Z" fill="url(#fl)" filter="url(#fs)" />
            <rect x="83" y="126" width="3" height="88" rx="1.5" fill="#fff" opacity=".3" />
            <rect x="114" y="126" width="3" height="88" rx="1.5" fill="#fff" opacity=".3" />
            {/* Resting arm */}
            <path d="M74 112 C60 132 62 160 44 184" fill="none" stroke="url(#fa)" strokeWidth="8" strokeLinecap="round" filter="url(#fs)" />
            <g fill="#dbe8fb" transform="rotate(30 40 192)">
              <ellipse cx="38" cy="192" rx="9" ry="6" />
              <ellipse cx="28" cy="196" rx="6" ry="2.6" />
              <ellipse cx="30" cy="203" rx="6" ry="2.6" />
              <ellipse cx="34" cy="209" rx="5" ry="2.4" />
            </g>
            {/* Waving arm */}
            <g className="f-wave">
              <path d="M128 114 C150 124 168 102 170 62" fill="none" stroke="url(#fa)" strokeWidth="8" strokeLinecap="round" filter="url(#fs)" />
              <g className="f-hand" fill="#e6effd">
                <ellipse cx="170" cy="50" rx="8" ry="9" />
                <ellipse cx="170" cy="33" rx="3" ry="11" />
                <ellipse cx="158" cy="48" rx="7" ry="3" transform="rotate(-20 158 48)" />
                <circle cx="178" cy="48" r="4" />
                <circle cx="177" cy="55" r="4" />
              </g>
            </g>
            {/* Head */}
            <g className="f-head">
              <g transform="rotate(-10 100 85)">
                <path
                  d="M48 62 L104 40 L142 56 L150 96 L126 124 L70 128 L46 104Z"
                  fill="url(#fh)"
                  stroke="#e3edfd"
                  strokeWidth="9"
                  strokeLinejoin="round"
                  filter="url(#fs)"
                />
                <ellipse cx="84" cy="92" rx="32" ry="18" fill="#1f4ed8" opacity=".7" filter="url(#fb)" />
                <path d="M58 70 L104 50" stroke="#fff" strokeWidth="3" strokeLinecap="round" opacity=".5" />
                <g className="f-lens">
                  <circle className="f-glow" cx="112" cy="82" r="24" fill="none" stroke="#9fd0ff" strokeWidth="3" />
                  <circle cx="112" cy="82" r="22" fill="rgba(255,255,255,.2)" stroke="#fff" strokeWidth="3" opacity=".95" />
                  <path d="M97 70 Q104 62 114 61" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" opacity=".8" />
                </g>
                <g className="f-look">
                  <g className="f-eye">
                    <circle cx="82" cy="94" r="4.8" fill="#0b1230" />
                    <circle cx="83.6" cy="92.4" r="1.2" fill="#fff" opacity=".8" />
                  </g>
                  <g className="f-eye">
                    <circle cx="110" cy="86" r="4.8" fill="#0b1230" />
                    <circle cx="111.6" cy="84.4" r="1.2" fill="#fff" opacity=".8" />
                  </g>
                </g>
                <ellipse className="f-mouth" cx="98" cy="113" rx="7" ry="5" fill="#14308f" />
              </g>
            </g>
          </svg>
        )}
      </div>

      {/* Clara 13 Authentic Expressions Grid */}
      {companion === 'clara' && (
        <div className="mood-grid" id="moodGrid" title="Clara's 13 Authentic Illustrated Expressions">
          {Object.keys(MOOD_LABELS).map((mKey) => (
            <button
              key={mKey}
              type="button"
              className={`mood-btn ${claraMood === mKey ? 'active' : ''}`}
              onClick={(e) => {
                e.stopPropagation();
                setClaraMood(mKey);
                setTimeout(() => setClaraMood('neutral'), 3200);
              }}
              title={`Trigger ${MOOD_LABELS[mKey]} expression`}
            >
              {MOOD_LABELS[mKey]}
            </button>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className="app">
      {!isDesktopApp && (
        <div className="web-desktop-banner">
          <span>
            🖥️ <strong>AURA Desktop:</strong> For the native window with system tray and global hotkey (<kbd>Ctrl+Shift+Space</kbd>), run <code>Launch_AURA_Desktop.vbs</code> or <code>npm run desktop</code>.
          </span>
        </div>
      )}

      {/* Header */}
      <header>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className="logo" onClick={handleNewChat} style={{ cursor: 'pointer' }} title="AURA Home">
            <i></i>AURA
          </div>
          {hasMessages && (
            <div
              className="pill"
              onClick={handleNewChat}
              title="Start New Chat (Return to Home)"
              style={{ fontWeight: 600, color: 'var(--accent)' }}
            >
              <span>+ New chat</span>
            </div>
          )}
        </div>

        <div className="right">
          {/* Conversation Mode Switcher Pill */}
          <div
            className="pill"
            id="modePill"
            title="Toggle between 1-on-1 Companion Mode and Chat Stream Mode"
            onClick={() => handleToggleMode()}
          >
            <span
              className="dot on"
              style={{
                background: conversationMode === 'companion' ? '#e56528' : '#3b72f0',
              }}
            ></span>
            <span>
              Mode ·{' '}
              <b style={{ fontWeight: 600 }}>
                {conversationMode === 'companion' ? 'Companion (1-on-1)' : 'Chat Stream'}
              </b>
            </span>
          </div>

          {/* Active Model Switcher Pill */}
          <div
            className="pill"
            id="modelPill"
            title="Active Ollama LLM (Click to switch)"
            onClick={() => setIsSettingsOpen(true)}
          >
            <span className="dot" style={{ background: 'var(--accent)' }}></span>
            <span>
              Model · <b style={{ fontWeight: 600 }}>{activeModel}</b>
            </span>
          </div>

          {/* Companion Switcher */}
          <div
            className="pill"
            id="swap"
            title="Switch companion (Ember ⇄ Frost ⇄ Clara)"
            onClick={() => handleSwitchCompanion()}
          >
            <span
              className="dot"
              id="swapDot"
              style={{
                background:
                  companion === 'ember'
                    ? '#f06a2b'
                    : companion === 'frost'
                    ? '#3b72f0'
                    : '#e56528',
              }}
            ></span>
            <span>
              Companion ·{' '}
              <b id="swapName" style={{ fontWeight: 600 }}>
                {companion === 'ember' ? 'Ember' : companion === 'frost' ? 'Frost' : 'Clara'}
              </b>
            </span>
          </div>

          {/* Clara Display Mode Pill */}
          {companion === 'clara' && (
            <div
              className="pill"
              id="displayToggle"
              title="Toggle companion presentation: Clean Cutout vs Atmospheric Portrait"
              onClick={() => setClaraDisplayMode((prev) => (prev === 'cutout' ? 'portrait' : 'cutout'))}
            >
              <span className="dot on"></span>
              <span>
                View · <b style={{ fontWeight: 600 }}>{claraDisplayMode === 'cutout' ? 'Cutout' : 'Portrait'}</b>
              </span>
            </div>
          )}

          {/* Wake Word Switch */}
          <div
            className="pill"
            id="wake"
            title="Toggle wake-word listener"
            onClick={handleToggleWake}
          >
            <span>Wake word · “Hey AURA”</span>
            <div className={`switch ${wakeOn ? 'on' : ''}`} id="wakeSw"></div>
          </div>

          {/* Setup Wizard Pill */}
          <div
            className="pill"
            id="setupWizardPill"
            title="Open Desktop Setup Wizard"
            onClick={() => setIsSetupOpen(true)}
            style={{ cursor: 'pointer' }}
          >
            <span>Setup</span>
            <span style={{ fontSize: '12px' }}>✨</span>
          </div>

          {/* Settings Button */}
          <div
            className="pill"
            id="settingsBtn"
            title="Open Assistant Settings"
            onClick={() => setIsSettingsOpen(true)}
          >
            <span>Settings</span>
            <span style={{ fontSize: '13px' }}>⚙️</span>
          </div>

          {/* Connection Status Indicator */}
          <div className="pill" id="conn">
            <span className={`dot ${isLive ? 'on' : 'warn'}`} id="connDot"></span>
            <span id="connTxt">{isLive ? 'Connected' : 'Demo mode'}</span>
          </div>

          {/* AURA Security Sandbox & Zero-Trust Protocol Badge */}
          <div
            className="pill"
            id="sandboxPill"
            title="Open Zero-Trust Security Dashboard & Emergency Stop (Kill Switch)"
            onClick={() => setIsSecurityOpen(true)}
            style={{
              borderColor: 'rgba(0, 184, 148, 0.4)',
              background: 'rgba(0, 184, 148, 0.08)',
              cursor: 'pointer',
            }}
          >
            <span style={{ fontSize: '11px' }}>🛡️</span>
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#008f72' }}>Zero-Trust Security</span>
          </div>
        </div>
      </header>

      {/* Main Interactive Workspace */}
      <main id="main" data-state={state}>
        {conversationMode === 'companion' ? (
          /* -------------------------------------------------------------
           * COMPANION 1-ON-1 MODE (COMPANION IS IN IT - STRICTLY USER AND COMPANION ONLY)
           * ------------------------------------------------------------- */
          !hasMessages ? (
            <div className="stage">
              {renderCompanionStage()}
              <h1 id="greet" dangerouslySetInnerHTML={{ __html: getGreetingHtml() }} />
              <div className="status">
                <div className="eq">
                  <b></b><b></b><b></b><b></b>
                </div>
                <span id="statusTxt">{getStatusText()}</span>
              </div>
            </div>
          ) : (
            <div className="companion-conversation-view">
              <div className="companion-stage-pane">
                {renderCompanionStage()}
                <div className="status">
                  <div className="eq">
                    <b></b><b></b><b></b><b></b>
                  </div>
                  <span id="statusTxt">{getStatusText()}</span>
                </div>
              </div>

              <div className="companion-dialogue-pane">
                <div className="dialogue-header">
                  <span>1-on-1 Conversation</span>
                  <span className="badge">
                    {companion === 'ember' ? '🔥 Ember' : companion === 'frost' ? '🤖 Frost' : '👩‍🦰 Clara'}
                  </span>
                </div>

                <div className="dialogue-stream" ref={dialogueStreamRef}>
                  {messages
                    .filter((m) => m.text || m.wiki || m.action)
                    .map((m) => (
                      <div key={m.id} className={`dialogue-row ${m.role}`}>
                        {m.role === 'aura' && (
                          <div
                            className={`chat-avatar ${companion}`}
                            title={companion === 'ember' ? 'Ember' : companion === 'frost' ? 'Frost' : 'Clara'}
                          >
                            {companion === 'ember' ? (
                              <span style={{ fontSize: '15px' }}>🔥</span>
                            ) : companion === 'frost' ? (
                              <span style={{ fontSize: '15px' }}>🤖</span>
                            ) : (
                              <span style={{ fontSize: '15px' }}>👩‍🦰</span>
                            )}
                          </div>
                        )}
                        <div className={`dialogue-bubble ${m.role} ${(m.wiki || m.action) ? 'has-card' : ''}`}>
                          <div className="dialogue-sender">
                            {m.role === 'user'
                              ? 'You'
                              : companion === 'ember'
                              ? 'Ember'
                              : companion === 'frost'
                              ? 'Frost'
                              : 'Clara'}
                          </div>
                          {m.text && (
                            <div className="dialogue-text">
                              {m.text}
                              {m.isStreaming && <span className="typing-cursor">▊</span>}
                            </div>
                          )}
                          {m.wiki && (
                            <div style={{ marginTop: m.text ? '10px' : '2px' }}>
                              <WikiKnowledgeCard wiki={m.wiki} />
                            </div>
                          )}
                          {m.action && (
                            <div style={{ marginTop: m.text ? '10px' : '2px' }}>
                              <ActionCard action={m.action} />
                            </div>
                          )}
                        </div>
                      </div>
                    ))}

                  {state === 'thinking' && !messages.some((m) => m.role === 'aura' && m.isStreaming) && (
                    <div className="dialogue-row aura">
                      <div className={`chat-avatar ${companion}`}>
                        {companion === 'ember' ? (
                          <span style={{ fontSize: '15px' }}>🔥</span>
                        ) : companion === 'frost' ? (
                          <span style={{ fontSize: '15px' }}>🤖</span>
                        ) : (
                          <span style={{ fontSize: '15px' }}>👩‍🦰</span>
                        )}
                      </div>
                      <div className="dialogue-bubble aura">
                        <div className="typing-dots">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        ) : (
          /* -------------------------------------------------------------
           * STREAM MODE (CHATGPT / GEMINI STYLE WITH WIKIPEDIA & ACTION CARDS)
           * ------------------------------------------------------------- */
          !hasMessages ? (
            <div className="stage">
              {renderCompanionStage()}
              <h1 id="greet" dangerouslySetInnerHTML={{ __html: getGreetingHtml() }} />
              <div className="status">
                <div className="eq">
                  <b></b><b></b><b></b><b></b>
                </div>
                <span id="statusTxt">{getStatusText()}</span>
              </div>
            </div>
          ) : (
            <div className="chat-stream" ref={chatStreamRef}>
              {messages.map((m) => (
                <React.Fragment key={m.id}>
                  {m.text && (
                    <div className={`chat-row ${m.role}`}>
                      {m.role === 'aura' && (
                        <div
                          className={`chat-avatar ${companion}`}
                          title={companion === 'ember' ? 'Ember' : companion === 'frost' ? 'Frost' : 'Clara'}
                        >
                          {companion === 'ember' ? (
                            <span style={{ fontSize: '15px' }}>🔥</span>
                          ) : companion === 'frost' ? (
                            <span style={{ fontSize: '15px' }}>🤖</span>
                          ) : (
                            <span style={{ fontSize: '15px' }}>👩‍🦰</span>
                          )}
                        </div>
                      )}
                      <div className={`chat-bubble ${m.role}`}>
                        {m.text}
                        {m.isStreaming && <span className="typing-cursor">▊</span>}
                      </div>
                    </div>
                  )}

                  {/* Wikipedia Editorial Knowledge Edition */}
                  {m.wiki && (
                    <div className="chat-row aura">
                      <div className={`chat-avatar ${companion}`}>
                        <span style={{ fontSize: '14px' }}>📚</span>
                      </div>
                      <WikiKnowledgeCard wiki={m.wiki} companion={companion} />
                    </div>
                  )}

                  {/* System Tool Action Card (Phase 7 Desktop Control) */}
                  {m.action && (
                    <div className="chat-row aura">
                      <div className={`chat-avatar ${companion}`}>
                        <span style={{ fontSize: '14px' }}>⚡</span>
                      </div>
                      <ActionCard action={m.action} />
                    </div>
                  )}
                </React.Fragment>
              ))}

              {/* Thinking / Processing animated dots */}
              {state === 'thinking' && !messages.some((m) => m.role === 'aura' && m.isStreaming) && (
                <div className="chat-row aura">
                  <div className={`chat-avatar ${companion}`}>
                    <span style={{ fontSize: '15px' }}>✨</span>
                  </div>
                  <div className="chat-bubble aura">
                    <div className="typing-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        )}

        {/* Dock Controls */}
        <div className="dock">
          {/* Quick Action Chips ONLY shown when no messages yet */}
          {!hasMessages && (
            <div className="chips" id="chips">
              {companion === 'clara' ? (
                <>
                  <div className="chip" onClick={() => sendText("Tell me a short joke")}>
                    😄 Tell me a short joke
                  </div>
                  <div className="chip" onClick={() => sendText("What's on my schedule today?")}>
                    📅 What's on my schedule today?
                  </div>
                  <div className="chip" onClick={() => sendText("You look fantastic today!")}>
                    ✨ You look fantastic today!
                  </div>
                  <div className="chip" onClick={() => sendText("Can you keep a secret?")}>
                    🤫 Can you keep a secret?
                  </div>
                  <div className="chip" onClick={() => sendText("Explain black holes in one sentence")}>
                    🌌 Explain black holes
                  </div>
                  <div className="chip" onClick={() => sendText("I'm feeling a bit tired today")}>
                    ☕ I'm feeling a bit tired today
                  </div>
                </>
              ) : (
                <>
                  <div className="chip" onClick={() => sendText("how is my battery?")}>
                    🔋 Battery Status
                  </div>
                  <div className="chip" onClick={() => sendText("check ram usage")}>
                    💻 RAM & CPU
                  </div>
                  <div className="chip" onClick={() => sendText("open notepad")}>
                    🚀 Open Notepad
                  </div>
                  <div className="chip" onClick={() => sendText("where is tajmahal")}>
                    🏛️ Where is Taj Mahal?
                  </div>
                  <div className="chip" onClick={() => sendText("summarize my clipboard")}>
                    📋 Summarize Clipboard
                  </div>
                  <div className="chip" onClick={() => sendText("mute audio")}>
                    🔇 Mute Audio
                  </div>
                </>
              )}
            </div>
          )}

          {/* Input Capsule Bar */}
          <div className="bar">
            <input
              id="txt"
              ref={txtRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') sendText();
              }}
              placeholder="Type a message, or hold the mic…"
              autoComplete="off"
            />
            <button
              className={`ptt ${state === 'listening' ? 'rec' : ''}`}
              id="ptt"
              title="Push to talk (Space)"
              onClick={togglePTT}
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="9" y="3" width="6" height="12" rx="3" />
                <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
              </svg>
              <span id="pttTxt">{state === 'listening' ? 'Stop' : 'Push to Talk'}</span>
              <kbd>Space</kbd>
            </button>
            <button className="ic send" id="send" title="Send" onClick={() => sendText()}>
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 19V5M5 12l7-7 7 7" />
              </svg>
            </button>
          </div>

          <div className="hint">
            {conversationMode === 'companion'
              ? '🎭 1-on-1 Companion Mode (Only You & Companion) · Space to talk · Enter to send'
              : '💬 Chat Stream Mode (Editorial & Deep Search) · Space to talk · Enter to send'}
          </div>
        </div>
      </main>

      {/* Settings Modal (LLM Model, Voice Persona, Deep Search, Wake Word, Hardware) */}
      {isSettingsOpen && (
        <div className="modal-backdrop" onClick={() => setIsSettingsOpen(false)}>
          <div className="settings-window" onClick={(e) => e.stopPropagation()}>
            <div className="settings-header">
              <div className="settings-title">
                <span>⚙️ Assistant Settings</span>
              </div>
              <button
                type="button"
                className="settings-close"
                onClick={() => setIsSettingsOpen(false)}
                title="Close (Esc)"
              >
                ✕
              </button>
            </div>

            <div className="settings-content">
              {/* Section 0: Conversation & Display Mode */}
              <div>
                <div className="settings-section-title">Conversation & Display Mode</div>
                <div className="model-grid">
                  <div
                    className={`model-option ${conversationMode === 'companion' ? 'sel' : ''}`}
                    onClick={() => handleToggleMode('companion')}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="model-option-name">🎭 Companion (1-on-1)</span>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 600,
                          color: conversationMode === 'companion' ? 'var(--accent)' : 'var(--muted)',
                          background: conversationMode === 'companion' ? 'rgba(240,106,43,0.12)' : 'rgba(0,0,0,0.05)',
                          padding: '2px 6px',
                          borderRadius: '4px',
                        }}
                      >
                        User & Companion Only
                      </span>
                    </div>
                    <div className="model-option-desc">
                      Companion stays active on stage (Clara, Ember, Frost) with live speech & 1-on-1 dialogue. Focused and personal.
                    </div>
                  </div>

                  <div
                    className={`model-option ${conversationMode === 'stream' ? 'sel' : ''}`}
                    onClick={() => handleToggleMode('stream')}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="model-option-name">💬 Chat Stream</span>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 600,
                          color: conversationMode === 'stream' ? '#3b72f0' : 'var(--muted)',
                          background: conversationMode === 'stream' ? 'rgba(59,114,240,0.12)' : 'rgba(0,0,0,0.05)',
                          padding: '2px 6px',
                          borderRadius: '4px',
                        }}
                      >
                        Research Feed
                      </span>
                    </div>
                    <div className="model-option-desc">
                      ChatGPT / Gemini stream layout with Wikipedia deep search monographs, media galleries & system action widgets.
                    </div>
                  </div>
                </div>
              </div>

              {/* Section 1: Companion Persona & Rig */}
              <div>
                <div className="settings-section-title">Companion Persona & Rig</div>
                <div className="model-grid">
                  <div
                    className={`model-option ${companion === 'ember' ? 'sel' : ''}`}
                    onClick={() => handleSwitchCompanion('ember')}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="model-option-name">🔥 Ember</span>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 600,
                          color: companion === 'ember' ? '#f06a2b' : 'var(--muted)',
                          background: companion === 'ember' ? 'rgba(240,106,43,0.12)' : 'rgba(0,0,0,0.05)',
                          padding: '2px 6px',
                          borderRadius: '4px',
                        }}
                      >
                        Flame Rig
                      </span>
                    </div>
                    <div className="model-option-desc">Warm elemental flame companion · Fluid multi-layer SVG physics</div>
                  </div>

                  <div
                    className={`model-option ${companion === 'frost' ? 'sel' : ''}`}
                    onClick={() => handleSwitchCompanion('frost')}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="model-option-name">🤖 Frost</span>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 600,
                          color: companion === 'frost' ? '#3b72f0' : 'var(--muted)',
                          background: companion === 'frost' ? 'rgba(59,114,240,0.12)' : 'rgba(0,0,0,0.05)',
                          padding: '2px 6px',
                          borderRadius: '4px',
                        }}
                      >
                        Robot Rig
                      </span>
                    </div>
                    <div className="model-option-desc">High-tech android companion · Glowing lenses, articulated wave & blue gradients</div>
                  </div>

                  <div
                    className={`model-option ${companion === 'clara' ? 'sel' : ''}`}
                    onClick={() => handleSwitchCompanion('clara')}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="model-option-name">👩‍🦰 Clara</span>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 600,
                          color: companion === 'clara' ? '#e56528' : 'var(--muted)',
                          background: companion === 'clara' ? 'rgba(229,101,40,0.12)' : 'rgba(0,0,0,0.05)',
                          padding: '2px 6px',
                          borderRadius: '4px',
                        }}
                      >
                        Master 2.5D Rig
                      </span>
                    </div>
                    <div className="model-option-desc">Disney-renaissance 2.5D rigged companion · 13 moods, visemes, lens glints & saccades</div>
                  </div>
                </div>
              </div>

              {/* Section 2: Ollama LLM Model */}
              <div>
                <div className="settings-section-title">Ollama LLM Model (Local)</div>
                <div className="model-grid">
                  {AVAILABLE_MODELS.map((m) => {
                    const isSelected = activeModel.toLowerCase() === m.id.toLowerCase();
                    return (
                      <div
                        key={m.id}
                        className={`model-option ${isSelected ? 'sel' : ''}`}
                        onClick={() => handleSelectModel(m.id)}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span className="model-option-name">{m.name}</span>
                          <span
                            style={{
                              fontSize: '10px',
                              fontWeight: 600,
                              color: isSelected ? 'var(--accent)' : 'var(--muted)',
                              background: isSelected ? 'rgba(240,106,43,0.1)' : 'rgba(0,0,0,0.05)',
                              padding: '2px 6px',
                              borderRadius: '4px',
                            }}
                          >
                            {m.badge}
                          </span>
                        </div>
                        <div className="model-option-desc">{m.desc}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Section 3: Voice Persona & TTS Engine */}
              <div>
                <div className="settings-section-title">Voice Persona & Speech Engine</div>
                <div className="model-grid">
                  {AVAILABLE_VOICES.map((v) => {
                    const isSelected =
                      activeVoice.toLowerCase() === v.name.toLowerCase() ||
                      activeVoice.toLowerCase() === v.id.toLowerCase();
                    return (
                      <div
                        key={v.id}
                        className={`model-option ${isSelected ? 'sel' : ''}`}
                        onClick={() => handleSelectVoice(v.name)}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span className="model-option-name">{v.name}</span>
                          <span
                            style={{
                              fontSize: '10px',
                              fontWeight: 600,
                              color: isSelected ? 'var(--accent)' : 'var(--muted)',
                              background: isSelected ? 'rgba(240,106,43,0.1)' : 'rgba(0,0,0,0.05)',
                              padding: '2px 6px',
                              borderRadius: '4px',
                            }}
                          >
                            {v.engine}
                          </span>
                        </div>
                        <div className="model-option-desc">{v.sub}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Section 4: Feature Toggles */}
              <div>
                <div className="settings-section-title">Search & Voice Triggers</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {/* Wikipedia Deep Search Toggle */}
                  <div className="setting-toggle-row" onClick={handleToggleDeepSearch}>
                    <div>
                      <div style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--ink)' }}>
                        Wikipedia Deep Search
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--muted)' }}>
                        Automatically discover factual encyclopedia articles and Wikimedia gallery photos
                      </div>
                    </div>
                    <div className={`switch ${deepSearchOn ? 'on' : ''}`}></div>
                  </div>

                  {/* Wake Word Toggle */}
                  <div className="setting-toggle-row" onClick={handleToggleWake}>
                    <div>
                      <div style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--ink)' }}>
                        Wake Word Listener (“Hey AURA”)
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--muted)' }}>
                        Continuous hands-free speech activation via local Faster-Whisper
                      </div>
                    </div>
                    <div className={`switch ${wakeOn ? 'on' : ''}`}></div>
                  </div>
                </div>
              </div>

              {/* Section 5: AURA Independent Virtual Assistant Hand & Skin Library */}
              <div>
                <VirtualHandSettings />
              </div>

              {/* Section 6: Hardware & Runtime Diagnostics */}
              <div>
                <div className="settings-section-title">Hardware & Runtime System</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
                  <div style={{ padding: '12px 14px', background: 'rgba(0,0,0,0.03)', borderRadius: '12px', border: '1px solid var(--line)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase' }}>GPU VRAM</div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink)', marginTop: '4px' }}>{vramText}</div>
                    <div className="meter" style={{ marginTop: '8px' }}>
                      <i style={{ width: `${vramPercent}%` }}></i>
                    </div>
                  </div>
                  <div style={{ padding: '12px 14px', background: 'rgba(0,0,0,0.03)', borderRadius: '12px', border: '1px solid var(--line)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase' }}>Speech & TTS</div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink)', marginTop: '4px' }}>RTX 2050 (GPU accelerated)</div>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '4px' }}>Faster-Whisper + Edge/Piper</div>
                  </div>
                  <div style={{ padding: '12px 14px', background: 'rgba(0,0,0,0.03)', borderRadius: '12px', border: '1px solid var(--line)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase' }}>FastAPI Backend</div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink)', marginTop: '4px' }}>127.0.0.1:8000</div>
                    <div style={{ fontSize: '11px', color: isLive ? 'var(--ok)' : 'var(--warn)', marginTop: '4px', fontWeight: 600 }}>
                      {isLive ? '● Live WebSocket connected' : '○ Offline demo mode'}
                    </div>
                  </div>
                  <div style={{ padding: '12px 14px', background: 'rgba(0, 184, 148, 0.05)', borderRadius: '12px', border: '1px solid rgba(0, 184, 148, 0.25)' }}>
                    <div style={{ fontSize: '11px', color: '#008f72', fontWeight: 700, textTransform: 'uppercase' }}>Security Sandbox</div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: '#008f72', marginTop: '4px' }}>🛡️ ENFORCED (v1.0)</div>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '4px' }}>URI Allowlist & Boundary Active</div>
                  </div>
                </div>

                {/* Setup Wizard Trigger in Settings */}
                <div style={{ marginTop: '18px', paddingTop: '16px', borderTop: '1px solid var(--line)' }}>
                  <button
                    type="button"
                    style={{
                      width: '100%',
                      padding: '11px 16px',
                      borderRadius: '10px',
                      border: '1px solid var(--accent)',
                      background: 'rgba(240, 106, 43, 0.08)',
                      color: 'var(--accent)',
                      fontWeight: 600,
                      fontSize: '13px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      transition: 'all 0.15s ease',
                    }}
                    onClick={() => {
                      setIsSettingsOpen(false);
                      setIsSetupOpen(true);
                    }}
                  >
                    <span>✨ Re-run Desktop Setup Wizard</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Standalone Desktop Setup Wizard */}
      <SetupWizard
        isOpen={isSetupOpen}
        onClose={() => setIsSetupOpen(false)}
        currentCompanion={companion}
        onSelectCompanion={(c) => handleSwitchCompanion(c)}
        currentVoice={activeVoice}
        onSelectVoice={(v) => handleSelectVoice(v)}
        wakeWordEnabled={wakeOn}
        onToggleWakeWord={handleToggleWake}
        isBackendLive={isLive}
      />

      {/* Zero-Trust Security Dashboard & Kill Switch */}
      <SecurityDashboard
        isOpen={isSecurityOpen}
        onClose={() => setIsSecurityOpen(false)}
      />

      {/* Custom Hardware-Accelerated Cat Paw Cursor */}
      <CustomCursor config={cursorConfig} />
    </div>
  );
}

export default App;
