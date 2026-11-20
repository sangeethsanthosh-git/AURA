import { useState, useEffect, useRef, useCallback } from 'react';

export type AssistantState = 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING' | 'ERROR';

export interface WikiArticle {
  title: string;
  url: string;
  extract: string;
}

export interface WikiImage {
  url: string;
  original_url: string;
  title: string;
  caption: string;
}

export interface WikiResult {
  query: string;
  articles: WikiArticle[];
  images: WikiImage[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  wiki?: WikiResult;
}

export interface VoiceProfile {
  id: string;
  name: string;
  gender: string;
  engine: string;
  speaker: string;
  badge: string;
  description: string;
}

export interface AuraSocketState {
  state: AssistantState;
  transcription: string;
  response: string;
  messages: ChatMessage[];
  activeModel: string;
  activeVoice: string;
  availableVoices: VoiceProfile[];
  ttsEngine: string;
  isConnected: boolean;
  wakeWordActive: boolean;
  deepSearchActive: boolean;
  activePersona?: string;
  companionMood?: string;
  personalitySettings?: any;
  startListening: () => void;
  stopAudio: () => void;
  sendText: (text: string) => void;
  setModel: (model: string) => void;
  setVoice: (voice: string) => void;
  toggleWakeWord: (enabled: boolean) => void;
  toggleDeepSearch: (enabled: boolean) => void;
  clearTranscript: () => void;
}

const DEFAULT_VOICES: VoiceProfile[] = [
  { id: 'aria', name: 'Aria', gender: 'Female', engine: 'edge', speaker: 'en-US-AriaNeural', badge: 'Neural (Default)', description: 'Warm, expressive, natural conversational female voice' },
  { id: 'guy', name: 'Guy', gender: 'Male', engine: 'edge', speaker: 'en-US-GuyNeural', badge: 'Neural', description: 'Natural, relaxed American male voice' },
  { id: 'jenny', name: 'Jenny', gender: 'Female', engine: 'edge', speaker: 'en-US-JennyNeural', badge: 'Neural', description: 'Friendly, bright modern female voice' },
  { id: 'christopher', name: 'Christopher', gender: 'Male', engine: 'edge', speaker: 'en-US-ChristopherNeural', badge: 'Neural', description: 'Confident, authoritative male voice' },
  { id: 'eric', name: 'Eric', gender: 'Male', engine: 'edge', speaker: 'en-US-EricNeural', badge: 'Neural', description: 'Youthful, energetic male voice' },
  { id: 'ana', name: 'Ana', gender: 'Female', engine: 'edge', speaker: 'en-US-AnaNeural', badge: 'Neural', description: 'Gentle, soft female voice' },
  { id: 'sonia', name: 'Sonia', gender: 'Female', engine: 'edge', speaker: 'en-GB-SoniaNeural', badge: 'British', description: 'Refined British English female voice' },
  { id: 'ryan', name: 'Ryan', gender: 'Male', engine: 'edge', speaker: 'en-GB-RyanNeural', badge: 'British', description: 'Conversational British English male voice' },
  { id: 'piper', name: 'Piper (Lessac)', gender: 'Female', engine: 'piper', speaker: 'lessac-medium', badge: 'Offline <20ms', description: 'Ultra-fast offline local ONNX voice with zero latency' },
];

const getDefaultWsUrl = () => {
  if (typeof window !== 'undefined' && window.location.port === '8000') {
    return `ws://${window.location.host}/ws`;
  }
  return 'ws://127.0.0.1:8000/ws';
};

export function useAuraSocket(wsUrl: string = getDefaultWsUrl()): AuraSocketState {
  const [state, setState] = useState<AssistantState>('IDLE');
  const [transcription, setTranscription] = useState<string>('');
  const [response, setResponse] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeModel, setActiveModel] = useState<string>('llama3.2:3b');
  const [activeVoice, setActiveVoice] = useState<string>('Aria');
  const [availableVoices, setAvailableVoices] = useState<VoiceProfile[]>(DEFAULT_VOICES);
  const [ttsEngine, setTtsEngine] = useState<string>('edge');
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [wakeWordActive, setWakeWordActive] = useState<boolean>(true);
  const [deepSearchActive, setDeepSearchActive] = useState<boolean>(true);
  const [activePersona, setActivePersona] = useState<string>('normal');
  const [companionMood, setCompanionMood] = useState<string>('neutral');
  const [personalitySettings, setPersonalitySettings] = useState<any>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isClosingRef = useRef<boolean>(false);

  const connect = useCallback(() => {
    if (
      socketRef.current &&
      (socketRef.current.readyState === WebSocket.OPEN ||
        socketRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    // Clean up any pending reconnect timer
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    isClosingRef.current = false;

    try {
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        if (socketRef.current !== ws) return;
        setIsConnected(true);
        ws.send(JSON.stringify({ type: 'get_state' }));
      };

      ws.onmessage = (event) => {
        // Discard any events from superseded or closed sockets
        if (socketRef.current !== ws) return;

        try {
          const data = JSON.parse(event.data);
          if (data.type === 'state_change') {
            setState(data.state);
            if (data.model) setActiveModel(data.model);
            if (data.voice) setActiveVoice(data.voice);
            if (Array.isArray(data.available_voices) && data.available_voices.length > 0) {
              setAvailableVoices(data.available_voices);
            }
            if (data.tts_engine) setTtsEngine(data.tts_engine);
            if (data.wake_word_active !== undefined) setWakeWordActive(data.wake_word_active);
            if (data.deep_search_active !== undefined) setDeepSearchActive(data.deep_search_active);
            if (data.personality) {
              setPersonalitySettings(data.personality);
              if (data.personality.current_profile) setActivePersona(data.personality.current_profile);
            }
            if (data.companion_mood) setCompanionMood(data.companion_mood);
            if (Array.isArray(data.history)) {
              setMessages(
                data.history.map((m: { role: string; content: string }) => ({
                  role: m.role === 'user' ? 'user' : 'assistant',
                  content: m.content,
                }))
              );
            }
          } else if (data.type === 'transcription') {
            const userText = (data.text || '').trim();
            if (!userText) return;
            setTranscription(userText);
            setMessages((prev) => {
              // Deduplicate: avoid appending duplicate user prompt if already present as latest message
              if (
                prev.length > 0 &&
                prev[prev.length - 1].role === 'user' &&
                prev[prev.length - 1].content.trim() === userText
              ) {
                return prev;
              }
              return [...prev, { role: 'user', content: userText }];
            });
          } else if (data.type === 'wiki_results') {
            const wikiPayload: WikiResult = {
              query: data.query || '',
              articles: Array.isArray(data.articles) ? data.articles : [],
              images: Array.isArray(data.images) ? data.images : [],
            };
            setMessages((prev) => [
              ...prev,
              { role: 'assistant', content: '', wiki: wikiPayload },
            ]);
          } else if (data.type === 'response_chunk') {
            const chunkText = data.text || '';
            setResponse(chunkText);
            setMessages((prev) => {
              // Always update the current assistant message in-place if the last bubble is assistant
              if (prev.length > 0 && prev[prev.length - 1].role === 'assistant') {
                const last = prev[prev.length - 1];
                if (last.content === chunkText) return prev;
                return [...prev.slice(0, -1), { ...last, content: chunkText }];
              }
              // First token chunk received: create single assistant bubble
              return [...prev, { role: 'assistant', content: chunkText }];
            });
          } else if (data.type === 'response') {
            const finalText = data.text || '';
            setResponse(finalText);
            setMessages((prev) => {
              // Finalize the current assistant message in-place without duplicating bubbles
              if (prev.length > 0 && prev[prev.length - 1].role === 'assistant') {
                const last = prev[prev.length - 1];
                if (last.content === finalText) return prev;
                return [...prev.slice(0, -1), { ...last, content: finalText }];
              }
              return [...prev, { role: 'assistant', content: finalText }];
            });
          } else if (data.type === 'conversation_cleared') {
            setMessages([]);
            setTranscription('');
            setResponse('');
          } else if (data.type === 'model_updated') {
            setActiveModel(data.model);
          } else if (data.type === 'voice_updated') {
            if (data.voice) setActiveVoice(data.voice);
            if (data.tts_engine) setTtsEngine(data.tts_engine);
          } else if (data.type === 'personality_update') {
            if (data.settings) {
              setPersonalitySettings(data.settings);
              if (data.settings.current_profile) setActivePersona(data.settings.current_profile);
            }
            if (data.profile) setActivePersona(data.profile);
            if (data.mood) setCompanionMood(data.mood);
          } else if (data.type === 'companion_mood') {
            if (data.mood) setCompanionMood(data.mood);
          } else if (data.type === 'wake_word_status') {
            setWakeWordActive(data.active);
          } else if (data.type === 'deep_search_status') {
            setDeepSearchActive(data.active);
          } else if (data.type === 'wake_word_triggered') {
            setTranscription('[Wake-Word "AURA" Detected]');
          } else if (data.type === 'error') {
            setState('ERROR');
            setResponse(`Error: ${data.message}`);
            setMessages((prev) => [
              ...prev,
              { role: 'assistant', content: `Error: ${data.message}` },
            ]);
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onclose = () => {
        if (isClosingRef.current) return;
        if (socketRef.current === ws) {
          setIsConnected(false);
          socketRef.current = null;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 2000);
        }
      };

      ws.onerror = (err) => {
        if (isClosingRef.current) return;
        console.warn('WebSocket connection error:', err);
        ws.close();
      };
    } catch (err) {
      if (isClosingRef.current) return;
      console.error('WebSocket connection initialization error:', err);
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 2000);
    }
  }, [wsUrl]);

  useEffect(() => {
    connect();
    return () => {
      isClosingRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (socketRef.current) {
        const s = socketRef.current;
        socketRef.current = null;
        s.onclose = null;
        s.onerror = null;
        s.onmessage = null;
        s.close();
      }
    };
  }, [connect]);

  const startListening = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      setTranscription('');
      setResponse('');
      socketRef.current.send(JSON.stringify({ type: 'start_listening' }));
    }
  }, []);

  const stopAudio = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'cancel' }));
    }
  }, []);

  const sendText = useCallback((text: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      setResponse('');
      socketRef.current.send(JSON.stringify({ type: 'send_text', text }));
    }
  }, []);

  const setModel = useCallback((model: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'set_model', model }));
    }
  }, []);

  const setVoice = useCallback((voice: string) => {
    setActiveVoice(voice);
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'set_voice', voice }));
    }
  }, []);

  const toggleWakeWord = useCallback((enabled: boolean) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'toggle_wake_word', enabled }));
    }
  }, []);

  const toggleDeepSearch = useCallback((enabled: boolean) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'toggle_deep_search', enabled }));
    }
  }, []);

  const clearTranscript = useCallback(() => {
    setMessages([]);
    setTranscription('');
    setResponse('');
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'new_conversation' }));
    }
  }, []);

  return {
    state,
    transcription,
    response,
    messages,
    activeModel,
    activeVoice,
    availableVoices,
    ttsEngine,
    isConnected,
    wakeWordActive,
    deepSearchActive,
    activePersona,
    companionMood,
    personalitySettings,
    startListening,
    stopAudio,
    sendText,
    setModel,
    setVoice,
    toggleWakeWord,
    toggleDeepSearch,
    clearTranscript,
  };
}
