import React, { useEffect, useId, useRef, useState } from 'react';
import { ExternalLink, X, BookOpen, Sparkles, Compass } from 'lucide-react';
import type { ChatMessage, WikiImage } from '../hooks/useAuraSocket';

interface TranscriptViewProps {
  messages: ChatMessage[];
  onSelectPrompt?: (prompt: string) => void;
}

const getProxyImageUrl = (rawUrl: string): string => {
  if (!rawUrl) return '';
  if (typeof window !== 'undefined' && window.location.port === '8000') {
    return `/api/wiki-image?url=${encodeURIComponent(rawUrl)}`;
  }
  return `http://127.0.0.1:8000/api/wiki-image?url=${encodeURIComponent(rawUrl)}`;
};

// Curated starter prompts (recreating Reference Image 1)
const STARTER_PROMPTS = [
  'Give me a healthy recipe to fuel my day.',
  'Suggest a quick workout to boost my mood.',
  'Tell me about the Apollo 11 moon mission.',
  'How does quantum computing work in simple terms?',
  'What is a great way to balance movement and rest?',
];

export const TranscriptView: React.FC<TranscriptViewProps> = ({ messages, onSelectPrompt }) => {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const dialogRef = useRef<HTMLDialogElement | null>(null);
  const dialogTitleId = useId();
  const [selectedImage, setSelectedImage] = useState<WikiImage | null>(null);
  const [brokenUrls, setBrokenUrls] = useState<Record<string, boolean>>({});

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Manage native modal lightbox lifecycle
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (selectedImage && !dialog.open) {
      dialog.showModal();
    } else if (!selectedImage && dialog.open) {
      dialog.close();
    }
  }, [selectedImage]);

  // Progressive enhancement fallback for click-outside on native dialog
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog || 'closedBy' in HTMLDialogElement.prototype) return;

    const outside = (e: PointerEvent) => {
      const r = dialog.getBoundingClientRect();
      return (
        e.clientX < r.left ||
        e.clientX > r.right ||
        e.clientY < r.top ||
        e.clientY > r.bottom
      );
    };

    let pressedOutside = false;
    const onPointerDown = (e: PointerEvent) => {
      pressedOutside = outside(e);
    };
    const onPointerUp = (e: PointerEvent) => {
      if (pressedOutside && outside(e)) {
        dialog.close();
      }
    };

    dialog.addEventListener('pointerdown', onPointerDown);
    dialog.addEventListener('pointerup', onPointerUp);
    return () => {
      dialog.removeEventListener('pointerdown', onPointerDown);
      dialog.removeEventListener('pointerup', onPointerUp);
    };
  }, []);

  // Empty state: Elegant starter prompt list (Image 1 style)
  if (messages.length === 0) {
    return (
      <div className="w-full max-w-lg flex flex-col items-center justify-center py-2 px-4 animate-in fade-in duration-300">
        {/* Subtle Assistant Intro Prompt Card (Image 1 style) */}
        <div className="w-full flex flex-col items-start mb-4">
          <span className="text-[11px] font-medium text-white/90 drop-shadow-xs mb-1.5 ml-2 tracking-wide flex items-center gap-1">
            <Sparkles size={11} className="text-[#FF7E5F]" />
            AURA AI Assistant
          </span>
          <div className="px-5 py-3 rounded-2xl bg-white/80 backdrop-blur-xl border border-white/90 shadow-[0_8px_24px_rgba(235,110,65,0.12)] text-[#2B2521] text-[15px] font-medium leading-relaxed">
            Hi, what can I do for you today?
          </div>
        </div>

        {/* Suggestion Prompts List (Image 1 style) */}
        <div className="w-full flex flex-col gap-1.5 items-center">
          <div className="flex items-center gap-1.5 text-xs text-[#8A796E] font-medium mb-1">
            <Compass size={13} className="text-[#FF7E5F]" />
            <span>Try asking or tap an idea:</span>
          </div>

          <div className="w-full flex flex-col gap-1.5">
            {STARTER_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onSelectPrompt && onSelectPrompt(prompt)}
                className="w-full text-left px-4 py-2 rounded-xl text-[13px] text-[#544940] hover:text-[#1F1C1A] bg-white/40 hover:bg-white/80 backdrop-blur-md border border-white/60 hover:border-white shadow-2xs hover:shadow-sm transition-all duration-200 cursor-pointer flex items-center justify-between group"
              >
                <span className="truncate">{prompt}</span>
                <span className="text-[#A8988D] group-hover:text-[#FF6B4A] transition-transform group-hover:translate-x-0.5 text-xs">
                  →
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="luminous-scroller flex flex-col gap-3.5 w-full max-w-xl max-h-[300px] overflow-y-auto px-3 py-2">
        {messages.map((msg, idx) => {
          const validImages = (msg.wiki?.images || []).filter((img) => !brokenUrls[img.url]);
          const articles = msg.wiki?.articles || [];
          const isUser = msg.role === 'user';

          return (
            <div
              key={idx}
              className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[92%] ${
                isUser ? 'self-end' : 'self-start'
              } animate-in fade-in duration-200`}
            >
              {/* Sender Subheading (Image 1 style) */}
              <span className="text-[10px] font-medium text-[#7D6E63] mb-1 px-1 tracking-wide">
                {isUser ? 'You' : 'AURA AI Assistant'}
              </span>

              {/* Message Pill Card */}
              <div
                className={`p-3.5 rounded-[22px] backdrop-blur-xl border transition-all ${
                  isUser
                    ? 'rounded-tr-xs bg-gradient-to-br from-[#FF7E5F]/20 to-[#FEB47B]/15 border-[#FF7E5F]/30 text-[#1F1C1A] shadow-sm shadow-[#FF7E5F]/10'
                    : 'rounded-tl-xs bg-white/85 border-white/90 text-[#24201D] shadow-[0_8px_24px_rgba(235,110,65,0.1)]'
                }`}
              >
                {/* Message Text */}
                {msg.content ? (
                  <div className="text-[14px] leading-relaxed whitespace-pre-wrap select-text font-normal">
                    {msg.content}
                  </div>
                ) : msg.wiki ? (
                  <div className="text-xs text-[#8A796E] italic animate-pulse flex items-center gap-1.5">
                    <Sparkles size={12} className="text-[#FF7E5F]" />
                    Synthesizing knowledge from Wikipedia...
                  </div>
                ) : null}

                {/* Wikipedia Deep Search Image Gallery */}
                {validImages.length > 0 && (
                  <div className="luminous-scroller mt-3 flex gap-2 overflow-x-auto pb-1.5">
                    {validImages.map((img, imgIdx) => (
                      <button
                        key={img.url}
                        type="button"
                        onClick={() => setSelectedImage(img)}
                        title={img.caption || img.title}
                        className="group relative shrink-0 w-24 h-20 rounded-xl overflow-hidden border border-black/[0.08] hover:border-[#FF7E5F] transition bg-white/80 shadow-xs cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#FF7E5F]"
                      >
                        <img
                          src={getProxyImageUrl(img.url)}
                          alt={img.caption || img.title}
                          loading={imgIdx === 0 ? undefined : 'lazy'}
                          onError={() =>
                            setBrokenUrls((prev) => ({ ...prev, [img.url]: true }))
                          }
                          className="w-full h-full object-cover group-hover:scale-105 transition duration-200"
                        />
                        <span className="absolute inset-x-0 bottom-0 px-1.5 py-0.5 text-[9px] text-white bg-black/60 backdrop-blur-xs truncate text-left">
                          {img.caption || img.title}
                        </span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Wikipedia Source Articles */}
                {articles.length > 0 && (
                  <div className="mt-2.5 flex flex-wrap items-center gap-1.5 pt-2 border-t border-black/[0.05]">
                    <span className="inline-flex items-center gap-1 text-[10px] text-[#7A6E64] mr-0.5">
                      <BookOpen size={11} className="text-[#FF7E5F]" />
                      Sources:
                    </span>
                    {articles.map((art) => (
                      <a
                        key={art.url}
                        href={art.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-white/80 hover:bg-[#FFF2EB] border border-black/[0.06] hover:border-[#FF7E5F]/40 text-[#4A4038] hover:text-[#D44726] transition shadow-2xs"
                      >
                        <span className="truncate max-w-[130px]">{art.title}</span>
                        <ExternalLink size={9} />
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {/* Accessible Wikipedia Image Lightbox Modal */}
      <dialog
        ref={dialogRef}
        aria-labelledby={dialogTitleId}
        onClose={() => setSelectedImage(null)}
        className="p-0 bg-transparent backdrop:bg-black/60 backdrop:backdrop-blur-md rounded-2xl max-w-xl w-[90vw] m-auto border-none shadow-2xl focus:outline-none"
      >
        {selectedImage && (
          <div className="relative bg-white/95 rounded-2xl p-4 flex flex-col gap-3 border border-white/80 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3
                id={dialogTitleId}
                className="text-sm font-semibold text-[#1F1C1A] truncate pr-4"
              >
                {selectedImage.caption || selectedImage.title || 'Wikipedia Image'}
              </h3>
              <button
                type="button"
                onClick={() => setSelectedImage(null)}
                aria-label="Close dialog"
                className="p-1.5 rounded-full text-[#7A6E64] hover:text-[#1F1C1A] hover:bg-black/[0.05] transition cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <div className="relative max-h-[60vh] flex items-center justify-center overflow-hidden rounded-xl bg-[#F6EDE8]">
              <img
                src={getProxyImageUrl(selectedImage.url)}
                alt={selectedImage.caption || selectedImage.title}
                className="max-h-[60vh] w-auto object-contain rounded-xl"
              />
            </div>

            {selectedImage.caption && (
              <p className="text-xs text-[#5C5047] leading-relaxed">
                {selectedImage.caption}
              </p>
            )}
          </div>
        )}
      </dialog>
    </>
  );
};
