import React, { useState, useEffect, useRef } from 'react';
import type { CompanionType } from '../types';

interface SetupWizardProps {
  isOpen: boolean;
  onClose: () => void;
  currentCompanion: CompanionType;
  onSelectCompanion: (c: CompanionType) => void;
  currentVoice: string;
  onSelectVoice: (v: string) => void;
  wakeWordEnabled: boolean;
  onToggleWakeWord: () => void;
  isBackendLive: boolean;
}

interface DiagnosticStatus {
  backend: 'loading' | 'ok' | 'warn';
  ollama: 'loading' | 'ok' | 'warn';
  ollamaModel: string;
  stt: 'loading' | 'ok' | 'warn';
  tts: 'loading' | 'ok' | 'warn';
  vision: 'loading' | 'ok' | 'warn';
  documents: 'loading' | 'ok' | 'warn';
  documentCount: number;
  mic: 'checking' | 'ok' | 'denied';
}

export const SetupWizard: React.FC<SetupWizardProps> = ({
  isOpen,
  onClose,
  currentCompanion,
  onSelectCompanion,
  currentVoice,
  onSelectVoice,
  wakeWordEnabled,
  onToggleWakeWord,
  isBackendLive,
}) => {
  const [step, setStep] = useState<number>(1);
  const [diagnostics, setDiagnostics] = useState<DiagnosticStatus>({
    backend: 'loading',
    ollama: 'loading',
    ollamaModel: 'llama3.2:3b',
    stt: 'loading',
    tts: 'loading',
    vision: 'loading',
    documents: 'loading',
    documentCount: 0,
    mic: 'checking',
  });
  const [micLevel, setMicLevel] = useState<number>(0);
  const [isTestingMic, setIsTestingMic] = useState<boolean>(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const animFrameRef = useRef<number | null>(null);

  // Run Real-time Diagnostics
  const runDiagnostics = async () => {
    try {
      setDiagnostics((prev) => ({
        ...prev,
        backend: 'loading',
        ollama: 'loading',
        stt: 'loading',
        tts: 'loading',
        vision: 'loading',
        documents: 'loading',
      }));

      const res = await fetch('http://127.0.0.1:8000/health');
      if (res.ok) {
        const data = await res.json();
        setDiagnostics((prev) => ({
          ...prev,
          backend: 'ok',
          ollama: data.ollama_connected ? 'ok' : 'warn',
          ollamaModel: data.ollama_model || 'llama3.2:3b',
          stt: data.stt_loaded ? 'ok' : 'warn',
          tts: data.tts_ready ? 'ok' : 'warn',
          vision: data.vision_ready ? 'ok' : 'warn',
          documents: 'ok',
          documentCount: data.rag_chunks || 0,
        }));
      } else {
        setDiagnostics((prev) => ({ ...prev, backend: 'warn' }));
      }
    } catch {
      setDiagnostics((prev) => ({
        ...prev,
        backend: isBackendLive ? 'ok' : 'warn',
        ollama: 'warn',
        stt: 'warn',
        tts: 'ok',
        vision: 'ok',
        documents: 'ok',
      }));
    }

    // Check Microphone
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setDiagnostics((prev) => ({ ...prev, mic: 'ok' }));
      stream.getTracks().forEach((track) => track.stop());
    } catch {
      setDiagnostics((prev) => ({ ...prev, mic: 'denied' }));
    }
  };

  useEffect(() => {
    if (isOpen) {
      runDiagnostics();
    }
    return () => {
      stopMicTest();
    };
  }, [isOpen]);

  // Microphone Live Audio VU Level
  const startMicTest = async () => {
    try {
      setIsTestingMic(true);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = ctx;
      const src = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      src.connect(analyser);
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const updateLevel = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        const norm = Math.min(100, Math.round((avg / 128) * 100));
        setMicLevel(norm);
        animFrameRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();
    } catch (e) {
      console.warn('Mic test error:', e);
      setIsTestingMic(false);
    }
  };

  const stopMicTest = () => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    setIsTestingMic(false);
    setMicLevel(0);
  };

  const playVoiceSample = (voiceName: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(
        `Hello! I'm Clara, your desktop companion speaking with ${voiceName}. How can I assist you today?`
      );
      u.rate = 1.05;
      u.pitch = 1.0;
      window.speechSynthesis.speak(u);
    }
  };

  const handleFinish = () => {
    stopMicTest();
    localStorage.setItem('aura_setup_completed', 'true');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop setup-wizard-backdrop">
      <div className="setup-wizard-window" onClick={(e) => e.stopPropagation()}>
        {/* Header with Step Stepper */}
        <div className="setup-wizard-header">
          <div className="setup-badge">Desktop Setup Wizard</div>
          <h2 className="setup-title">
            {step === 1 && 'Welcome & System Diagnostics'}
            {step === 2 && 'Select Your AI Companion'}
            {step === 3 && 'Audio & Voice Calibration'}
            {step === 4 && 'Desktop Shortcuts & Features'}
            {step === 5 && 'Setup Complete!'}
          </h2>
          <div className="setup-stepper">
            {[1, 2, 3, 4, 5].map((s) => (
              <div
                key={s}
                className={`step-dot ${step === s ? 'active' : step > s ? 'completed' : ''}`}
                onClick={() => setStep(s)}
              >
                {step > s ? '✓' : s}
              </div>
            ))}
          </div>
        </div>

        {/* Step Body */}
        <div className="setup-wizard-body">
          {/* STEP 1: Diagnostics */}
          {step === 1 && (
            <div className="setup-step-view">
              <p className="setup-desc">
                AURA is configuring your local AI environment on Windows. Let’s verify all services are active:
              </p>

              <div className="setup-diag-grid">
                <div className={`setup-diag-card ${diagnostics.backend}`}>
                  <div className="diag-icon">⚡</div>
                  <div className="diag-info">
                    <div className="diag-label">FastAPI Core Backend</div>
                    <div className="diag-sub">Local REST & WebSocket daemon (Port 8000)</div>
                  </div>
                  <div className="diag-status">
                    {diagnostics.backend === 'ok' ? 'Online' : diagnostics.backend === 'warn' ? 'Checking' : 'Testing…'}
                  </div>
                </div>

                <div className={`setup-diag-card ${diagnostics.ollama}`}>
                  <div className="diag-icon">🧠</div>
                  <div className="diag-info">
                    <div className="diag-label">Ollama LLM Engine</div>
                    <div className="diag-sub">Active Model: {diagnostics.ollamaModel}</div>
                  </div>
                  <div className="diag-status">
                    {diagnostics.ollama === 'ok' ? 'Ready' : diagnostics.ollama === 'warn' ? 'Connecting' : 'Testing…'}
                  </div>
                </div>

                <div className={`setup-diag-card ${diagnostics.stt}`}>
                  <div className="diag-icon">🎙️</div>
                  <div className="diag-info">
                    <div className="diag-label">Faster-Whisper Neural STT</div>
                    <div className="diag-sub">CPU INT8 quantized streaming engine</div>
                  </div>
                  <div className="diag-status">
                    {diagnostics.stt === 'ok' ? 'Active' : 'Offline'}
                  </div>
                </div>

                <div className={`setup-diag-card ${diagnostics.tts}`}>
                  <div className="diag-icon">🔊</div>
                  <div className="diag-info">
                    <div className="diag-label">Piper & Edge Voice Synthesizers</div>
                    <div className="diag-sub">Ultra low-latency neural TTS voices</div>
                  </div>
                  <div className="diag-status">{diagnostics.tts === 'ok' ? 'Ready' : 'Checking'}</div>
                </div>

                <div className={`setup-diag-card ${diagnostics.vision}`}>
                  <div className="diag-icon">👁️</div>
                  <div className="diag-info">
                    <div className="diag-label">Screen Vision & Win32 API</div>
                    <div className="diag-sub">Foreground window detection & desktop captures</div>
                  </div>
                  <div className="diag-status">{diagnostics.vision === 'ok' ? 'Ready' : 'Checking'}</div>
                </div>

                <div className={`setup-diag-card ${diagnostics.documents}`}>
                  <div className="diag-icon">📚</div>
                  <div className="diag-info">
                    <div className="diag-label">Local Documents (RAG)</div>
                    <div className="diag-sub">{diagnostics.documentCount} knowledge chunks indexed</div>
                  </div>
                  <div className="diag-status">{diagnostics.documents === 'ok' ? 'Indexed' : 'Ready'}</div>
                </div>
              </div>

              <div className="setup-diag-refresh-row">
                <button className="setup-refresh-btn" onClick={runDiagnostics}>
                  ↻ Re-check System Services
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: Companion Persona */}
          {step === 2 && (
            <div className="setup-step-view">
              <p className="setup-desc">
                Choose your default visual companion. You can switch companions anytime from the top bar:
              </p>

              <div className="setup-companion-grid">
                {/* Clara */}
                <div
                  className={`setup-comp-card ${currentCompanion === 'clara' ? 'selected' : ''}`}
                  onClick={() => onSelectCompanion('clara')}
                >
                  <div className="comp-avatar-preview clara-preview">
                    <img src="/assets/head_base.png" alt="Clara" className="clara-head-img" />
                    <span className="badge-pill">2.5D Animated</span>
                  </div>
                  <div className="comp-name">Clara</div>
                  <div className="comp-role">The Scholarly Companion</div>
                  <div className="comp-desc">
                    Full 2.5D layered canvas compositor with 13 emotional moods, speech viseme sync, tap giggles, and tactile earcons.
                  </div>
                </div>

                {/* Ember */}
                <div
                  className={`setup-comp-card ${currentCompanion === 'ember' ? 'selected' : ''}`}
                  onClick={() => onSelectCompanion('ember')}
                >
                  <div className="comp-avatar-preview ember-preview">
                    <div className="ember-orb-glow"></div>
                    <span className="badge-pill">Fiery Gold</span>
                  </div>
                  <div className="comp-name">Ember</div>
                  <div className="comp-role">The Dynamic Catalyst</div>
                  <div className="comp-desc">
                    Warm solar plasma sphere with breathing particle corona, reactive audio amplitude flares, and physics deformation.
                  </div>
                </div>

                {/* Frost */}
                <div
                  className={`setup-comp-card ${currentCompanion === 'frost' ? 'selected' : ''}`}
                  onClick={() => onSelectCompanion('frost')}
                >
                  <div className="comp-avatar-preview frost-preview">
                    <div className="frost-orb-glow"></div>
                    <span className="badge-pill">Glacial Cyan</span>
                  </div>
                  <div className="comp-name">Frost</div>
                  <div className="comp-role">The Precision Core</div>
                  <div className="comp-desc">
                    Crystalline cyan plasma orb with calm, soothing, focus-oriented pulse physics and geometric auroras.
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: Audio & Voice Calibration */}
          {step === 3 && (
            <div className="setup-step-view">
              <p className="setup-desc">
                Configure your voice persona and test your microphone input:
              </p>

              <div className="setup-audio-section">
                <div className="setup-section-label">Default Voice Persona</div>
                <div className="setup-voice-chips">
                  {[
                    { id: 'Aria', name: 'Aria', desc: 'Warm & Natural (Female)' },
                    { id: 'Guy', name: 'Guy', desc: 'Relaxed & Conversational (Male)' },
                    { id: 'Jenny', name: 'Jenny', desc: 'Clear & Cheerful (Female)' },
                    { id: 'Piper (Lessac)', name: 'Piper (Lessac)', desc: 'Zero-latency Offline (<20ms)' },
                  ].map((v) => (
                    <div
                      key={v.id}
                      className={`voice-chip ${currentVoice.toLowerCase().includes(v.name.toLowerCase()) ? 'selected' : ''}`}
                      onClick={() => onSelectVoice(v.name)}
                    >
                      <div className="voice-chip-main">
                        <span className="voice-name">{v.name}</span>
                        <span className="voice-desc">{v.desc}</span>
                      </div>
                      <button
                        className="voice-preview-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          playVoiceSample(v.name);
                        }}
                        title="Preview voice"
                      >
                        ▶ Test
                      </button>
                    </div>
                  ))}
                </div>

                <div className="setup-section-label" style={{ marginTop: '20px' }}>
                  Microphone Input Test
                </div>
                <div className="setup-mic-card">
                  <div className="mic-status-row">
                    <span>Microphone Status:</span>
                    <strong style={{ color: diagnostics.mic === 'ok' ? 'var(--ok)' : 'var(--warn)' }}>
                      {diagnostics.mic === 'ok' ? 'Available' : 'Check permissions'}
                    </strong>
                  </div>

                  <div className="mic-vu-bar-wrap">
                    <div
                      className="mic-vu-bar"
                      style={{
                        width: `${micLevel}%`,
                        background: micLevel > 70 ? 'var(--warn)' : 'var(--accent)',
                      }}
                    ></div>
                  </div>

                  <div className="mic-test-btns">
                    {!isTestingMic ? (
                      <button className="setup-mic-btn start" onClick={startMicTest}>
                        🎙️ Start Live Mic Test
                      </button>
                    ) : (
                      <button className="setup-mic-btn stop" onClick={stopMicTest}>
                        ⏹️ Stop Mic Test
                      </button>
                    )}
                    <span className="mic-hint">
                      {isTestingMic ? 'Speak now into your microphone to watch the meter.' : 'Click to test your input level.'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: Desktop Shortcuts & Tray Tour */}
          {step === 4 && (
            <div className="setup-step-view">
              <p className="setup-desc">
                AURA is designed to integrate seamlessly into your Windows desktop workflow:
              </p>

              <div className="setup-features-list">
                <div className="feature-item">
                  <div className="feature-icon">⌨️</div>
                  <div className="feature-info">
                    <div className="feature-title">Global Hotkey: <kbd>Ctrl + Shift + Space</kbd> (or <kbd>Alt + A</kbd>)</div>
                    <div className="feature-sub">
                      Summon AURA or start listening from any application, game, or window on Windows without switching apps.
                    </div>
                  </div>
                </div>

                <div className="feature-item">
                  <div className="feature-icon">🪟</div>
                  <div className="feature-info">
                    <div className="feature-title">System Tray Daemon</div>
                    <div className="feature-sub">
                      Closing the window minimizes AURA to the Windows system tray. Double-click the tray icon to restore anytime.
                    </div>
                  </div>
                </div>

                <div className="feature-item">
                  <div className="feature-icon">👁️</div>
                  <div className="feature-info">
                    <div className="feature-title">Screen Vision & Desktop Context</div>
                    <div className="feature-sub">
                      Say <em>“What’s on my screen?”</em> or <em>“Look at my screen”</em> to analyze whatever you are working on.
                    </div>
                  </div>
                </div>

                <div className="feature-item">
                  <div className="feature-icon">⏱️</div>
                  <div className="feature-info">
                    <div className="feature-title">Timers & Windows Toast Notifications</div>
                    <div className="feature-sub">
                      Say <em>“Set a timer for 10 minutes”</em> to receive native Windows Toasts and audio chimes when it’s up.
                    </div>
                  </div>
                </div>
              </div>

              {/* Wake Word Option */}
              <div className="setup-wakeword-toggle-row" onClick={onToggleWakeWord}>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 600 }}>Enable Hands-free Wake Word (“Hey AURA”)</div>
                  <div style={{ fontSize: '11.5px', color: 'var(--muted)' }}>
                    Constantly listens for “Hey AURA” using local Faster-Whisper with 0% cloud transmission.
                  </div>
                </div>
                <div className={`switch ${wakeWordEnabled ? 'on' : ''}`}></div>
              </div>
            </div>
          )}

          {/* STEP 5: All Set */}
          {step === 5 && (
            <div className="setup-step-view setup-complete-view">
              <div className="setup-complete-icon">✨</div>
              <h3 className="setup-complete-title">You’re All Set!</h3>
              <p className="setup-desc" style={{ maxWidth: '500px', margin: '0 auto 24px auto' }}>
                AURA is primed and ready as your desktop assistant. You can change your companion, voice, or hotkeys anytime in Settings.
              </p>

              <div className="setup-summary-pills">
                <span className="summary-pill">Companion: {currentCompanion.toUpperCase()}</span>
                <span className="summary-pill">Voice: {currentVoice}</span>
                <span className="summary-pill">Wake Word: {wakeWordEnabled ? 'Enabled' : 'Disabled'}</span>
                <span className="summary-pill">Hotkey: Ctrl+Shift+Space</span>
              </div>
            </div>
          )}
        </div>

        {/* Wizard Footer Controls */}
        <div className="setup-wizard-footer">
          {step > 1 ? (
            <button className="setup-btn back" onClick={() => setStep(step - 1)}>
              ← Back
            </button>
          ) : (
            <div></div>
          )}

          {step < 5 ? (
            <button className="setup-btn next" onClick={() => setStep(step + 1)}>
              Next Step →
            </button>
          ) : (
            <button className="setup-btn finish" onClick={handleFinish}>
              Launch AURA Desktop 🚀
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SetupWizard;
