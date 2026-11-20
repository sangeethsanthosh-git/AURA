/**
 * Companion Audio & Playful Interaction Effects
 * Synthesizes zero-latency tactile tap sounds, musical giggle chirps,
 * vocal giggles, and visual floating sparkle/heart particle bursts.
 */

import type { CompanionType } from '../types';

let audioCtx: AudioContext | null = null;

function getAudioContext(): AudioContext {
  if (!audioCtx) {
    const AudioCtxClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    audioCtx = new AudioCtxClass();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

/**
 * Play a cute tactile tap / poke sound effect.
 */
export function playTapSound(companion: CompanionType = 'clara'): void {
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;

    if (companion === 'clara') {
      // Warm, bouncy bubble-pop chirp
      const osc = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(420, now);
      osc.frequency.exponentialRampToValueAtTime(840, now + 0.05);
      osc.frequency.exponentialRampToValueAtTime(520, now + 0.12);

      osc2.type = 'triangle';
      osc2.frequency.setValueAtTime(840, now);
      osc2.frequency.exponentialRampToValueAtTime(1080, now + 0.06);
      osc2.frequency.exponentialRampToValueAtTime(650, now + 0.12);

      gain.gain.setValueAtTime(0.28, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.14);

      osc.connect(gain);
      osc2.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc2.start(now);
      osc.stop(now + 0.15);
      osc2.stop(now + 0.15);
    } else if (companion === 'ember') {
      // Playful fiery spark pop
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(320, now);
      osc.frequency.exponentialRampToValueAtTime(960, now + 0.04);
      osc.frequency.exponentialRampToValueAtTime(400, now + 0.1);

      gain.gain.setValueAtTime(0.24, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.13);
    } else {
      // Frost: Crisp digital chime blip
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(660, now);
      osc.frequency.exponentialRampToValueAtTime(1320, now + 0.04);

      gain.gain.setValueAtTime(0.22, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.16);
    }
  } catch (err) {
    console.debug('Error playing tap sound:', err);
  }
}

/**
 * Play a musical laughing / giggling burst.
 * Simulates a cheerful rhythmic syllable flutter ("He-he-he-hee!").
 */
export function playGiggleSound(companion: CompanionType = 'clara'): void {
  try {
    const ctx = getAudioContext();
    const startTime = ctx.currentTime + 0.02;

    // Rhythmic syllable parameters for giggling laughter [delay, baseFreq, peakFreq, duration, volume]
    const giggleNotes = [
      { t: 0.00, f0: 740, f1: 860, d: 0.08, vol: 0.22 }, // "He"
      { t: 0.08, f0: 840, f1: 960, d: 0.08, vol: 0.25 }, // "he"
      { t: 0.16, f0: 980, f1: 1120, d: 0.09, vol: 0.28 }, // "he"
      { t: 0.26, f0: 1140, f1: 1300, d: 0.14, vol: 0.32 }, // "hee~"
      { t: 0.38, f0: 1040, f1: 940, d: 0.16, vol: 0.20 }, // release
    ];

    giggleNotes.forEach((note) => {
      const noteStart = startTime + note.t;
      const osc = ctx.createOscillator();
      const overtone = ctx.createOscillator();
      const gain = ctx.createGain();

      if (companion === 'frost') {
        osc.type = 'sawtooth';
        overtone.type = 'sine';
      } else if (companion === 'ember') {
        osc.type = 'triangle';
        overtone.type = 'sine';
      } else {
        osc.type = 'sine';
        overtone.type = 'triangle';
      }

      // Melodic frequency contour with joyful vocal upward bend
      osc.frequency.setValueAtTime(note.f0, noteStart);
      osc.frequency.exponentialRampToValueAtTime(note.f1, noteStart + note.d * 0.6);
      osc.frequency.exponentialRampToValueAtTime(note.f0 * 0.95, noteStart + note.d);

      overtone.frequency.setValueAtTime(note.f0 * 1.5, noteStart);
      overtone.frequency.exponentialRampToValueAtTime(note.f1 * 1.5, noteStart + note.d * 0.6);

      // Fast percussive laughter envelope
      gain.gain.setValueAtTime(0.001, noteStart);
      gain.gain.linearRampToValueAtTime(note.vol, noteStart + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.001, noteStart + note.d);

      osc.connect(gain);
      overtone.connect(gain);
      gain.connect(ctx.destination);

      osc.start(noteStart);
      overtone.start(noteStart);
      osc.stop(noteStart + note.d + 0.02);
      overtone.stop(noteStart + note.d + 0.02);
    });
  } catch (err) {
    console.debug('Error playing giggle sound:', err);
  }
}

/**
 * Optional vocal giggle using SpeechSynthesis with cute giggly pitch.
 */
const CLARA_GIGGLES = [
  "Hehe! That tickles!",
  "Tee-hee! Stop that, it tickles!",
  "Hehehe! Oh, you poked me!",
  "Hehe! You're so silly!",
  "Ahaha! That's my tickle spot!",
  "Hehehe, I'm right here with you!",
  "Hehe! You found me!",
];

const EMBER_GIGGLES = [
  "Sizzle! That sparks joy!",
  "Whoosh! You tickled my flames!",
  "Hehe! Warming up right here!",
  "Crackles and giggles!",
];

const FROST_GIGGLES = [
  "Beep-boop! Giggle protocol initiated!",
  "Chirp! Sensory probe detected, hehe!",
  "Optics tickled! Processing laughter…",
  "Beep! Playful tap registered!",
];

export function getRandomGiggle(companion: CompanionType = 'clara'): string {
  const list = companion === 'clara' ? CLARA_GIGGLES : companion === 'ember' ? EMBER_GIGGLES : FROST_GIGGLES;
  return list[Math.floor(Math.random() * list.length)];
}

/**
 * Vocalize a giggly phrase through WebSpeech if enabled.
 */
export function vocalizeGiggle(text: string, companion: CompanionType = 'clara'): void {
  if (!('speechSynthesis' in window)) return;
  try {
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.rate = 1.14;
    utter.pitch = companion === 'clara' ? 1.45 : companion === 'ember' ? 1.3 : 1.6;

    const voices = window.speechSynthesis.getVoices();
    const chosen = voices.find((v) => /jenny|natural|serena|zira|female/i.test(v.name)) || voices[0];
    if (chosen) utter.voice = chosen;

    window.speechSynthesis.speak(utter);
  } catch {}
}

/**
 * Spawn floating cheerful particles (hearts, stars, sparkles) from tap coordinate.
 */
export function spawnTapSparkles(x: number, y: number): void {
  const symbols = ['💖', '✨', '⭐', '🌸', '💕', '💫', '🎉', '🥰'];
  const count = 7 + Math.floor(Math.random() * 5);

  const container = document.createElement('div');
  container.className = 'tap-sparkles-container';
  container.style.position = 'fixed';
  container.style.left = '0';
  container.style.top = '0';
  container.style.width = '100vw';
  container.style.height = '100vh';
  container.style.pointerEvents = 'none';
  container.style.zIndex = '9999';
  document.body.appendChild(container);

  for (let i = 0; i < count; i++) {
    const el = document.createElement('span');
    el.className = 'tap-sparkle';
    el.textContent = symbols[Math.floor(Math.random() * symbols.length)];

    const angle = Math.random() * Math.PI * 2;
    const distance = 40 + Math.random() * 85;
    const destX = x + Math.cos(angle) * distance;
    const destY = y + Math.sin(angle) * distance - 35; // Slight upward buoyancy
    const rotate = (Math.random() - 0.5) * 60;
    const scale = 0.8 + Math.random() * 0.7;

    el.style.position = 'absolute';
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
    el.style.fontSize = `${16 + Math.random() * 10}px`;
    el.style.opacity = '1';
    el.style.transform = 'translate(-50%, -50%) scale(0.3)';
    el.style.transition = 'transform 0.75s cubic-bezier(0.18, 0.89, 0.32, 1.28), opacity 0.75s ease-out';
    el.style.filter = 'drop-shadow(0 2px 6px rgba(240, 100, 40, 0.4))';
    el.style.userSelect = 'none';

    container.appendChild(el);

    // Trigger animation on next animation frame
    requestAnimationFrame(() => {
      el.style.transform = `translate(${destX - x}px, ${destY - y}px) rotate(${rotate}deg) scale(${scale})`;
      setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = `translate(${destX - x}px, ${destY - y - 40}px) rotate(${rotate * 1.5}deg) scale(${scale * 0.6})`;
      }, 450);
    });
  }

  // Auto clean up after animation completes
  setTimeout(() => {
    container.remove();
  }, 1000);
}
