import React, { useEffect, useId, useRef, useState } from 'react';
import {
  ExternalLink,
  X,
  Sparkles,
  Mic,
  ArrowUp,
  Square,
  Paperclip,
  RotateCcw,
  Copy,
  Check,
  Globe,
  Volume2,
} from 'lucide-react';
import type { ChatMessage, WikiImage, AssistantState } from '../hooks/useAuraSocket';
import { MarkdownRenderer } from './MarkdownRenderer';

interface ChatViewProps {
  messages: ChatMessage[];
  state: AssistantState;
  activeModel: string;
  activeVoice: string;
  deepSearchActive: boolean;
  onSendText: (text: string) => void;
  onStartListening: () => void;
  onStopAudio: () => void;
  onOpenSettings: () => void;
  onToggleDeepSearch?: (enabled: boolean) => void;
  disabled?: boolean;
}

const getProxyImageUrl = (rawUrl: string): string => {
  if (!rawUrl) return '';
  if (typeof window !== 'undefined' && window.location.port === '8000') {
    return `/api/wiki-image?url=${encodeURIComponent(rawUrl)}`;
  }
  return `http://127.0.0.1:8000/api/wiki-image?url=${encodeURIComponent(rawUrl)}`;
};

const getFollowUpSuggestions = (lastAssistantMessage?: ChatMessage): string[] => {
  if (!lastAssistantMessage || !lastAssistantMessage.content) {
    return [
      'Tell me more about this in detail.',
      'Can you explain this with a practical example?',
      'What are the key takeaways I should remember?',
    ];
  }
  const text = lastAssistantMessage.content.toLowerCase();
  if (text.includes('quantum') || text.includes('physics')) {
    return [
      'What are practical applications of quantum computing today?',
      'How does quantum entanglement differ from classical physics?',
      'What are the biggest engineering hurdles in quantum chips?',
    ];
  }
  if (text.includes('code') || text.includes('script') || text.includes('typescript') || text.includes('python')) {
    return [
      'Can you add unit tests for this code?',
      'How would you optimize this for high concurrency?',
      'Can you show how to handle edge cases and retries?',
    ];
  }
  if (text.includes('space') || text.includes('apollo') || text.includes('moon')) {
    return [
      'What scientific experiments were conducted on the lunar surface?',
      'How did the Apollo guidance computer work?',
      'What are the upcoming Artemis missions planning to do?',
    ];
  }
  return [
    'Can you elaborate on the second point?',
    'What are the pros and cons of this approach?',
    'Are there any alternative viewpoints or recent updates?',
  ];
};

export const ChatView: React.FC<ChatViewProps> = ({
  messages,
  state,
  activeModel,
  activeVoice,
  deepSearchActive,
  onSendText,
  onStartListening,
  onStopAudio,
  onOpenSettings,
  onToggleDeepSearch,
  disabled = false,
}) => {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const dialogRef = useRef<HTMLDialogElement | null>(null);
  const dialogTitleId = useId();

  const [selectedImage, setSelectedImage] = useState<WikiImage | null>(null);
  const [brokenUrls, setBrokenUrls] = useState<Record<string, boolean>>({});
  const [inputText, setInputText] = useState('');
  const [copiedMsgIdx, setCopiedMsgIdx] = useState<number | null>(null);

  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === 'assistant');
  const followUps = getFollowUpSuggestions(lastAssistantMsg);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, state]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [inputText]);

  // Dialog lightbox management
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (selectedImage && !dialog.open) dialog.showModal();
    else if (!selectedImage && dialog.open) dialog.close();
  }, [selectedImage]);

  const handleSend = () => {
    const trimmed = inputText.trim();
    if (!trimmed || disabled) return;
    onSendText(trimmed);
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCopyMessage = (text: string, idx: number) => {
    navigator.clipboard.writeText(text).catch(() => {});
    setCopiedMsgIdx(idx);
    setTimeout(() => setCopiedMsgIdx(null), 2000);
  };

  const handleRegenerate = (lastPrompt?: string) => {
    if (lastPrompt) {
      onSendText(lastPrompt);
    }
  };

  const isBusy = state === 'SPEAKING' || state === 'THINKING';
  const isListening = state === 'LISTENING';

  return (
    <div className="flex-1 w-full max-w-[840px] mx-auto flex flex-col justify-between h-full px-4 pt-3 pb-4">
      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto aura-scroller pr-2 flex flex-col gap-5">
        {/* Date / Session Divider */}
        <div className="flex items-center justify-center my-2">
          <div className="flex items-center gap-3 w-full max-w-sm">
            <div className="h-[1px] bg-[var(--border)] flex-1" />
            <span className="text-[11px] font-medium text-[var(--text-tertiary)] uppercase tracking-wider">
              Today
            </span>
            <div className="h-[1px] bg-[var(--border)] flex-1" />
          </div>
        </div>

        {/* Conversation turns */}
        {messages.map((msg, idx) => {
          const isUser = msg.role === 'user';
          const validImages = (msg.wiki?.images || []).filter((img) => !brokenUrls[img.url]);
          const articles = msg.wiki?.articles || [];

          return (
            <div
              key={idx}
              className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} w-full animate-in fade-in duration-150`}
            >
              {isUser ? (
                /* User Prompt Pill */
                <div className="flex flex-col items-end max-w-[80%]">
                  <div className="px-4 py-2.5 rounded-2xl bg-[var(--surface-secondary)] text-[var(--text-primary)] text-[14.5px] leading-relaxed border border-[var(--border)] shadow-2xs font-normal">
                    {msg.content}
                  </div>
                  <span className="text-[10px] text-[var(--text-tertiary)] mt-1 px-1">
                    Just now
                  </span>
                </div>
              ) : (
                /* Assistant Message Block */
                <div className="w-full flex flex-col items-start gap-2 max-w-[96%]">
                  {/* Thinking Status Block */}
                  {state === 'THINKING' && idx === messages.length - 1 && (
                    <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)] bg-[var(--surface-primary)] px-3 py-1.5 rounded-full border border-[var(--border)] animate-pulse shadow-2xs">
                      <Sparkles size={13} className="text-[var(--accent)]" />
                      <span>Thinking through reasoning & facts...</span>
                    </div>
                  )}

                  {/* Main Assistant Content with Markdown rendering */}
                  {msg.content && (
                    <div className="text-[14.5px] leading-relaxed text-[var(--text-primary)] w-full">
                      <MarkdownRenderer content={msg.content} />
                    </div>
                  )}

                  {/* Numbered Source Badges */}
                  {articles.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 mt-2">
                      {articles.map((art, aIdx) => (
                        <a
                          key={art.url}
                          href={art.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[var(--surface-primary)] hover:bg-[var(--surface-secondary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition shadow-2xs"
                        >
                          <span className="w-3.5 h-3.5 rounded-full bg-[var(--surface-secondary)] text-[var(--text-primary)] text-[9px] font-bold flex items-center justify-center">
                            {aIdx + 1}
                          </span>
                          <span className="truncate max-w-[150px]">{art.title}</span>
                          <ExternalLink size={9} className="text-[var(--text-tertiary)]" />
                        </a>
                      ))}
                    </div>
                  )}

                  {/* Wikipedia Image Gallery */}
                  {validImages.length > 0 && (
                    <div className="aura-scroller mt-2.5 flex gap-2.5 overflow-x-auto pb-1 max-w-full">
                      {validImages.map((img) => (
                        <button
                          key={img.url}
                          type="button"
                          onClick={() => setSelectedImage(img)}
                          title={img.caption || img.title}
                          className="group relative shrink-0 w-28 h-20 rounded-xl overflow-hidden border border-[var(--border)] hover:border-[var(--accent)] transition bg-[var(--surface-primary)] shadow-2xs cursor-pointer"
                        >
                          <img
                            src={getProxyImageUrl(img.url)}
                            alt={img.caption || img.title}
                            onError={() => setBrokenUrls((p) => ({ ...p, [img.url]: true }))}
                            className="w-full h-full object-cover group-hover:scale-105 transition duration-200"
                          />
                          <span className="absolute inset-x-0 bottom-0 px-1.5 py-0.5 text-[9px] text-white bg-black/60 truncate text-left">
                            {img.caption || img.title}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Message Action Bar: Copy & Regenerate */}
                  <div className="flex items-center gap-2 mt-1">
                    <button
                      type="button"
                      onClick={() => handleCopyMessage(msg.content, idx)}
                      title="Copy response"
                      className="flex items-center gap-1 text-[11px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition cursor-pointer px-1 py-0.5 rounded hover:bg-[var(--surface-secondary)]"
                    >
                      {copiedMsgIdx === idx ? (
                        <>
                          <Check size={11} className="text-emerald-500" />
                          <span>Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy size={11} />
                          <span>Copy</span>
                        </>
                      )}
                    </button>

                    {idx === messages.length - 1 && (
                      <button
                        type="button"
                        onClick={() => {
                          const lastUser = [...messages].reverse().find((m) => m.role === 'user');
                          if (lastUser) handleRegenerate(lastUser.content);
                        }}
                        title="Regenerate response"
                        className="flex items-center gap-1 text-[11px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition cursor-pointer px-1 py-0.5 rounded hover:bg-[var(--surface-secondary)]"
                      >
                        <RotateCcw size={11} />
                        <span>Regenerate</span>
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {/* Follow-up Suggestion Chips (Reference Image 2) */}
        {!isBusy && messages.length > 0 && (
          <div className="w-full flex flex-col items-center gap-1.5 mt-3 mb-2">
            {followUps.map((prompt, pIdx) => (
              <button
                key={pIdx}
                type="button"
                onClick={() => onSendText(prompt)}
                className="follow-up-chip px-4 py-1.5 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer"
              >
                {prompt}
              </button>
            ))}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Pinned Bottom Chat Composer (Reference Image 2 & 3) */}
      <div className="w-full flex justify-center pt-2">
        <div className="w-full max-w-2xl floating-bottom-pill px-4 py-2 flex items-center justify-between gap-2.5">
          {/* Left tools: Attachment, Deep Search */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => {}}
              title="Attach File"
              className="p-1 rounded-md text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-secondary)] transition cursor-pointer"
            >
              <Paperclip size={16} />
            </button>

            {onToggleDeepSearch && (
              <button
                type="button"
                onClick={() => onToggleDeepSearch(!deepSearchActive)}
                title={deepSearchActive ? 'Deep Search Active' : 'Enable Deep Search'}
                className={`p-1 rounded-md transition cursor-pointer ${
                  deepSearchActive
                    ? 'text-[#2563EB] bg-[#EFF6FF]'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                <Globe size={15} />
              </button>
            )}
          </div>

          {/* Center Text Input Area */}
          <div className="flex-1">
            <textarea
              ref={textareaRef}
              rows={1}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                isListening
                  ? 'Listening to your speech...'
                  : isBusy
                  ? 'AURA is responding...'
                  : 'Message AURA (Enter to send, Shift+Enter for newline)...'
              }
              disabled={disabled}
              className="w-full bg-transparent text-[14px] text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none resize-none leading-relaxed min-h-[24px] max-h-[120px] aura-scroller"
            />
          </div>

          {/* Right Tools: Voice Info, Mic, Send */}
          <div className="flex items-center gap-1.5">
            <span
              onClick={onOpenSettings}
              title={`Voice: ${activeVoice} · Model: ${activeModel}`}
              className="hidden sm:inline-flex items-center gap-1 text-[11px] font-medium text-[var(--text-secondary)] bg-[var(--surface-secondary)] hover:bg-[var(--border)] px-2 py-0.5 rounded-full cursor-pointer transition"
            >
              <Volume2 size={11} className="text-[var(--accent)]" />
              <span>{activeVoice}</span>
            </span>

            {/* Microphone Button */}
            <button
              type="button"
              onClick={() => {
                if (isListening) onStopAudio();
                else onStartListening();
              }}
              title={isListening ? 'Stop listening' : 'Start voice recognition (Faster-Whisper)'}
              className={`p-1.5 rounded-full transition cursor-pointer ${
                isListening
                  ? 'text-white bg-[var(--status-error)] ring-2 ring-[var(--status-error)]/30 animate-pulse'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-secondary)]'
              }`}
            >
              <Mic size={16} />
            </button>

            {/* Circular Send / Stop Button */}
            {isBusy || isListening ? (
              <button
                type="button"
                onClick={onStopAudio}
                title="Stop"
                className="w-7 h-7 rounded-full bg-rose-500 hover:bg-rose-600 text-white flex items-center justify-center transition cursor-pointer shadow-2xs ml-0.5"
              >
                <Square size={11} fill="currentColor" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSend}
                disabled={!inputText.trim() || disabled}
                title="Send (Enter)"
                className="w-7 h-7 rounded-full bg-[var(--text-primary)] hover:bg-black text-[var(--surface-primary)] flex items-center justify-center transition disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer shadow-2xs ml-0.5"
              >
                <ArrowUp size={13} strokeWidth={2.4} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Accessible Image Lightbox Dialog */}
      <dialog
        ref={dialogRef}
        aria-labelledby={dialogTitleId}
        onClose={() => setSelectedImage(null)}
        className="p-0 bg-transparent backdrop:bg-black/50 backdrop:backdrop-blur-md rounded-2xl max-w-xl w-[90vw] m-auto border-none shadow-2xl focus:outline-none"
      >
        {selectedImage && (
          <div className="relative bg-[var(--surface-primary)] rounded-2xl p-4 flex flex-col gap-3 border border-[var(--border)] shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 id={dialogTitleId} className="text-sm font-semibold text-[var(--text-primary)] truncate pr-4">
                {selectedImage.caption || selectedImage.title || 'Wikipedia Image'}
              </h3>
              <button
                type="button"
                onClick={() => setSelectedImage(null)}
                className="p-1 rounded-full text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-black/[0.05] transition cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>
            <div className="relative max-h-[60vh] flex items-center justify-center overflow-hidden rounded-xl bg-[var(--surface-secondary)]">
              <img
                src={getProxyImageUrl(selectedImage.url)}
                alt={selectedImage.caption || selectedImage.title}
                className="max-h-[60vh] w-auto object-contain rounded-xl"
              />
            </div>
            {selectedImage.caption && (
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{selectedImage.caption}</p>
            )}
          </div>
        )}
      </dialog>
    </div>
  );
};
