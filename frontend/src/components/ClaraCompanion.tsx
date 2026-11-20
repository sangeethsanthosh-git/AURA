import React, { useEffect, useRef } from 'react';
import type { AssistantState } from '../types';

export interface ClaraCompanionProps {
  state: AssistantState;
  amp?: number;
  speechText?: string;
  activeMood?: string;
  onEmoteChange?: (mood: string) => void;
  className?: string;
}

interface EmotionValues {
  tilt: number;
  pitch: number;
  eyes: 'open' | 'shut' | 'wink';
  mouth: 'rest' | 'laugh' | 'speak';
  blush: number;
  wink: number;
}

/* 13 Natural Illustrated Expressions Matrix */
export const EMO: Record<string, EmotionValues> = {
  neutral:   { tilt: 0,    pitch: 0,   eyes: 'open', mouth: 'rest',  blush: 0.08, wink: 0 },
  happy:     { tilt: 2.5,  pitch: -1,  eyes: 'open', mouth: 'rest',  blush: 0.45, wink: 0 },
  laugh:     { tilt: 4.0,  pitch: -2,  eyes: 'shut', mouth: 'laugh', blush: 0.65, wink: 0 },
  think:     { tilt: -4.5, pitch: -2,  eyes: 'open', mouth: 'rest',  blush: 0.10, wink: 0 },
  curious:   { tilt: -3.5, pitch: 1.5, eyes: 'open', mouth: 'rest',  blush: 0.15, wink: 0 },
  listen:    { tilt: -1.5, pitch: 1.5, eyes: 'open', mouth: 'rest',  blush: 0.15, wink: 0 },
  surprised: { tilt: 0,    pitch: -2,  eyes: 'open', mouth: 'speak', blush: 0.20, wink: 0 },
  sad:       { tilt: -2.5, pitch: 2.5, eyes: 'open', mouth: 'rest',  blush: 0.05, wink: 0 },
  confused:  { tilt: -5.0, pitch: -1,  eyes: 'open', mouth: 'rest',  blush: 0.12, wink: 0 },
  shy:       { tilt: 3.5,  pitch: 2.0, eyes: 'open', mouth: 'rest',  blush: 0.85, wink: 0 },
  playful:   { tilt: 3.0,  pitch: 0,   eyes: 'wink', mouth: 'rest',  blush: 0.40, wink: 1.0 },
  sleepy:    { tilt: -2.0, pitch: 3.0, eyes: 'shut', mouth: 'rest',  blush: 0.08, wink: 0 },
  concerned: { tilt: -2.5, pitch: 1.5, eyes: 'open', mouth: 'rest',  blush: 0.15, wink: 0 }
};

export const MOOD_LABELS: Record<string, string> = {
  neutral: 'Calm',
  happy: 'Happy',
  laugh: 'Laugh',
  think: 'Think',
  curious: 'Curious',
  listen: 'Attentive',
  surprised: 'Gasp',
  sad: 'Sad',
  confused: 'Puzzled',
  shy: 'Blush',
  playful: 'Playful',
  sleepy: 'Sleepy',
  concerned: 'Concerned'
};

export function emoFor(t: string): string {
  const lower = t.toLowerCase();
  if (/haha|joke|funny|laugh|windows|cold/.test(lower)) return 'laugh';
  if (/sorry|cannot|error|unable|sad|unfortunately/.test(lower)) return 'sad';
  if (/secret|between us|wink|shh/.test(lower)) return 'playful';
  if (/fantastic|amazing|compliment|pretty|sweet|love|day/.test(lower)) return 'shy';
  if (/whoa|wow|quantum|black hole|gravity/.test(lower)) return 'surprised';
  if (/tired|rest|tea|sleepy|stretch/.test(lower)) return 'sleepy';
  if (/worried|problem|help|issue|trouble/.test(lower)) return 'concerned';
  if (/\?|what|how|why|schedule/.test(lower)) return 'curious';
  return 'happy';
}

export const ClaraCompanion: React.FC<ClaraCompanionProps> = ({
  state,
  amp = 0,
  speechText = '',
  activeMood,
  onEmoteChange,
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // References to keep state across 60 FPS animation frames
  const stateRef = useRef<AssistantState>(state);
  const ampRef = useRef<number>(amp);
  const speechTextRef = useRef<string>(speechText);
  const activeMoodRef = useRef<string | undefined>(activeMood);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    ampRef.current = amp;
  }, [amp]);

  useEffect(() => {
    speechTextRef.current = speechText;
  }, [speechText]);

  useEffect(() => {
    activeMoodRef.current = activeMood;
  }, [activeMood]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;
    ctx.imageSmoothingQuality = 'high';

    // Load authentic 2D Disney Illustration Rig Artwork Layers (896 x 1200)
    const assets = {
      torso: new Image(),
      head: new Image(),
      mouthSpeak: new Image(),
      mouthLaugh: new Image(),
      eyesClosed: new Image(),
      eyeClosedR: new Image(),
    };

    assets.torso.src = 'assets/clara_body_torso.png';
    assets.head.src = 'assets/clara_head_base.png';
    assets.mouthSpeak.src = 'assets/clara_mouth_speak.png';
    assets.mouthLaugh.src = 'assets/clara_mouth_laugh.png';
    assets.eyesClosed.src = 'assets/clara_eyes_closed.png';
    assets.eyeClosedR.src = 'assets/clara_eye_closed_right.png';

    // State & emotion interpolation
    const cur: EmotionValues = { ...EMO.neutral };
    let tgt: EmotionValues = EMO.neutral;
    let currentMoodName = 'neutral';

    let animAmp = 0;
    let ampTarget = 0;
    let blinkProgress = 0;
    let nextBlink = performance.now() + 2400;
    let saccadeX = 0;
    let saccadeY = 0;
    let nextSaccade = performance.now() + 3200;

    let mx = 0;
    let my = 0;
    let ex = 0;
    let ey = 0;
    let vx = 0;

    const handleMouseMove = (e: MouseEvent) => {
      mx = Math.max(-4, Math.min(4, (e.clientX / window.innerWidth - 0.5) * 8));
      my = Math.max(-3, Math.min(3, (e.clientY / window.innerHeight - 0.5) * 6));
    };
    window.addEventListener('mousemove', handleMouseMove);

    let isDisposed = false;
    let animId = 0;

    const renderLoop = (now: number) => {
      if (isDisposed) return;
      if (document.hidden) {
        animId = requestAnimationFrame(renderLoop);
        return;
      }

      const currentState = stateRef.current;
      const explicitMood = activeMoodRef.current;

      // Determine emotional target
      let moodName = 'neutral';
      if (explicitMood && EMO[explicitMood]) {
        moodName = explicitMood;
      } else if (currentState === 'listening') {
        moodName = 'listen';
      } else if (currentState === 'thinking') {
        moodName = 'think';
      } else if (currentState === 'speaking') {
        moodName = speechTextRef.current ? emoFor(speechTextRef.current) : 'happy';
      } else {
        moodName = 'neutral';
      }

      if (moodName !== currentMoodName) {
        currentMoodName = moodName;
        tgt = EMO[moodName] || EMO.neutral;
        if (onEmoteChange) onEmoteChange(moodName);
      }

      // 1. Smoothly interpolate emotional targets
      for (const k in tgt) {
        const key = k as keyof EmotionValues;
        if (typeof tgt[key] === 'number') {
          (cur[key] as number) += ((tgt[key] as number) - (cur[key] as number)) * 0.12;
        } else {
          (cur[key] as any) = tgt[key];
        }
      }

      // 2. Audio Amplitude Dynamics
      if (currentState === 'speaking') {
        ampTarget = 0.35 + Math.abs(Math.sin(now / 110) * Math.cos(now / 270)) * 0.65;
        if (ampRef.current > 0.05) {
          ampTarget = Math.max(ampTarget, ampRef.current);
        }
      } else if (currentState === 'listening') {
        ampTarget = 0.2 + Math.abs(Math.sin(now / 150)) * 0.45;
      } else if (currentState === 'thinking') {
        ampTarget = 0.15;
      } else {
        ampTarget = 0.04 + (Math.sin(now / 800) + 1) * 0.03;
      }
      animAmp += (ampTarget - animAmp) * 0.2;

      // 3. Natural Blinking Engine
      if (now > nextBlink && blinkProgress <= 0) {
        blinkProgress = 1;
        const isDouble = Math.random() < 0.18;
        nextBlink = now + (isDouble ? 340 : (2400 + Math.random() * 3200));
      }
      if (blinkProgress > 0) {
        blinkProgress -= 0.095;
        if (blinkProgress < 0) blinkProgress = 0;
      }
      const blinkCurve = Math.sin(blinkProgress * Math.PI);

      // 4. Natural Eye Saccades (Micro-glances)
      if (now > nextSaccade) {
        nextSaccade = now + 2600 + Math.random() * 3200;
        saccadeX = (Math.random() - 0.5) * 0.22;
        saccadeY = (Math.random() - 0.5) * 0.16;
        setTimeout(() => {
          saccadeX = 0;
          saccadeY = 0;
        }, 380);
      }

      // 5. Mouse Parallax Easing
      const tx = currentState === 'thinking' ? -3.0 : mx + saccadeX;
      const ty = currentState === 'thinking' ? -2.5 : my + saccadeY;
      ex += (tx - ex) * 0.1;
      ey += (ty - ey) * 0.1;
      vx *= 0.88;

      // HiDPI Canvas Scaling (Device Pixel Ratio Support)
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const dw = canvas.clientWidth || 340;
      const dh = canvas.clientHeight || 455;
      if (canvas.width !== Math.round(dw * dpr) || canvas.height !== Math.round(dh * dpr)) {
        canvas.width = Math.round(dw * dpr);
        canvas.height = Math.round(dh * dpr);
      }

      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.scale(canvas.width / 896, canvas.height / 1200);

      // LAYER 1: Body & Torso Breathing
      const breath = Math.sin(now * 0.0018);
      const breathY = breath * 2.5;
      if (assets.torso.complete) {
        ctx.drawImage(assets.torso, 0, breathY, 896, 1200);
      }

      // LAYER 2: Head Transformation (Pivoting at neck anchor 480, 620)
      ctx.save();
      const pivotX = 480;
      const pivotY = 620;
      const headAngle = ((cur.tilt + ex * 0.6 + vx * 0.25) * Math.PI) / 180;
      const headPitch = cur.pitch * 2.0 + ey * 0.4;

      ctx.translate(pivotX, pivotY);
      ctx.rotate(headAngle);
      ctx.translate(-pivotX, -pivotY);
      ctx.translate(0, headPitch + breathY * 0.35);

      // Head Base (Authentic hand-drawn face, eyes, hair, glasses, rest mouth)
      if (assets.head.complete) {
        ctx.drawImage(assets.head, 0, 0, 896, 1200);
      }

      // LAYER 3: Dynamic Eye Blinking & Winking (Authentic Hand-Drawn Cels)
      if (cur.eyes === 'wink' && assets.eyeClosedR.complete) {
        ctx.save();
        ctx.globalAlpha = cur.wink;
        ctx.drawImage(assets.eyeClosedR, 0, 0, 896, 1200);
        ctx.restore();
      } else if (assets.eyesClosed.complete) {
        const effClosed = cur.eyes === 'shut' ? 1.0 : blinkCurve;
        if (effClosed > 0.02) {
          ctx.save();
          ctx.globalAlpha = effClosed;
          ctx.drawImage(assets.eyesClosed, 0, 0, 896, 1200);
          ctx.restore();
        }
      }

      // LAYER 4: Dynamic Speech & Visemes (Authentic Hand-Drawn Cels)
      if (cur.mouth === 'laugh' && assets.mouthLaugh.complete) {
        ctx.save();
        ctx.drawImage(assets.mouthLaugh, 0, 0, 896, 1200);
        ctx.restore();
      } else if (assets.mouthSpeak.complete) {
        let speakOpen = 0;
        if (currentState === 'speaking') {
          speakOpen = Math.min(1.0, animAmp * 1.4);
        } else if (cur.mouth === 'speak') {
          speakOpen = 1.0;
        }
        if (speakOpen > 0.04) {
          ctx.save();
          ctx.globalAlpha = speakOpen;
          ctx.drawImage(assets.mouthSpeak, 0, 0, 896, 1200);
          ctx.restore();
        }
      }

      // LAYER 5: Dynamic Cheek Blush Bloom
      if (cur.blush > 0.05) {
        ctx.save();
        // Left Cheek: (390, 480)
        const bGradL = ctx.createRadialGradient(390, 480, 5, 390, 480, 65);
        bGradL.addColorStop(0, `rgba(255, 85, 110, ${cur.blush * 0.45})`);
        bGradL.addColorStop(1, 'rgba(255, 85, 110, 0)');
        ctx.fillStyle = bGradL;
        ctx.beginPath();
        ctx.arc(390, 480, 65, 0, Math.PI * 2);
        ctx.fill();

        // Right Cheek: (630, 480)
        const bGradR = ctx.createRadialGradient(630, 480, 5, 630, 480, 65);
        bGradR.addColorStop(0, `rgba(255, 85, 110, ${cur.blush * 0.45})`);
        bGradR.addColorStop(1, 'rgba(255, 85, 110, 0)');
        ctx.fillStyle = bGradR;
        ctx.beginPath();
        ctx.arc(630, 480, 65, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      // LAYER 6: Specular Spectacle Glint (Moving with gaze parallax)
      ctx.save();
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.22)';
      ctx.lineWidth = 4.5;
      ctx.beginPath();
      // Left Lens Gleam
      ctx.moveTo(380 + ex * 3, 400 + ey * 2);
      ctx.lineTo(455 + ex * 3, 330 + ey * 2);
      // Right Lens Gleam
      ctx.moveTo(560 + ex * 3, 400 + ey * 2);
      ctx.lineTo(635 + ex * 3, 330 + ey * 2);
      ctx.stroke();
      ctx.restore();

      ctx.restore(); // Restore Head Node
      ctx.restore(); // Restore Master Transform

      animId = requestAnimationFrame(renderLoop);
    };

    animId = requestAnimationFrame(renderLoop);

    return () => {
      isDisposed = true;
      cancelAnimationFrame(animId);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [onEmoteChange]);

  return (
    <div className={`companion-card ${className}`}>
      <canvas
        ref={canvasRef}
        id="companionCanvas"
        width={736}
        height={917}
        aria-label="Clara, AURA's 2.5D rigged companion"
        style={{
          width: '100%',
          height: '100%',
          display: 'block',
          objectFit: 'contain',
          pointerEvents: 'none',
        }}
      />
    </div>
  );
};

export default ClaraCompanion;
