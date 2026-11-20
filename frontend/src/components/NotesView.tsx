import React, { useState, useEffect } from 'react';
import {
  Plus,
  Search,
  Trash2,
  FileText,
  Eye,
  Edit3,
  Calendar,
} from 'lucide-react';
import { MarkdownRenderer } from './MarkdownRenderer';

export interface Note {
  id: string;
  title: string;
  content: string;
  updatedAt: string;
}

const DEFAULT_NOTES: Note[] = [
  {
    id: 'note-1',
    title: 'AURA Personal Assistant Architecture',
    content: `# AURA Personal Assistant Architecture\n\nA local-first, low-latency conversational desktop environment.\n\n## Core Components\n- **Inference**: Ollama (Llama 3.2 3B)\n- **STT**: Faster-Whisper INT8\n- **TTS**: Dual Edge-TTS & Piper\n- **Knowledge**: Wikipedia Deep Search\n\n### Next Milestones\n1. Enhanced context caching\n2. Audio stream interruption optimization`,
    updatedAt: new Date().toLocaleDateString(),
  },
  {
    id: 'note-2',
    title: 'Speech-to-Text Benchmark Observations',
    content: `Faster-Whisper on CPU transcribes within **400ms** to **800ms** using 4 threads.\n\nEnergy threshold VAD prevents background fan noise from creating blank turns.`,
    updatedAt: new Date().toLocaleDateString(),
  },
];

export const NotesView: React.FC = () => {
  const [notes, setNotes] = useState<Note[]>(() => {
    try {
      const saved = localStorage.getItem('aura_desktop_notes');
      return saved ? JSON.parse(saved) : DEFAULT_NOTES;
    } catch {
      return DEFAULT_NOTES;
    }
  });

  const [selectedNoteId, setSelectedNoteId] = useState<string>(() => {
    return notes[0]?.id || '';
  });

  const [searchQuery, setSearchQuery] = useState('');
  const [isPreview, setIsPreview] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem('aura_desktop_notes', JSON.stringify(notes));
    } catch {}
  }, [notes]);

  const activeNote = notes.find((n) => n.id === selectedNoteId) || notes[0];

  const handleCreateNote = () => {
    const newNote: Note = {
      id: `note-${Date.now()}`,
      title: 'Untitled Note',
      content: '# Untitled Note\n\nWrite your thoughts, plans, or research here...',
      updatedAt: new Date().toLocaleDateString(),
    };
    setNotes([newNote, ...notes]);
    setSelectedNoteId(newNote.id);
    setIsPreview(false);
  };

  const handleDeleteNote = (id: string) => {
    const remaining = notes.filter((n) => n.id !== id);
    setNotes(remaining);
    if (selectedNoteId === id && remaining.length > 0) {
      setSelectedNoteId(remaining[0].id);
    }
  };

  const handleUpdateNote = (field: 'title' | 'content', value: string) => {
    if (!activeNote) return;
    setNotes((prev) =>
      prev.map((n) =>
        n.id === activeNote.id
          ? {
              ...n,
              [field]: value,
              updatedAt: new Date().toLocaleDateString(),
            }
          : n
      )
    );
  };

  const filteredNotes = notes.filter(
    (n) =>
      n.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      n.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex-1 flex h-full overflow-hidden select-none animate-in fade-in duration-200">
      {/* Notes List Column */}
      <div className="w-[280px] h-full border-r border-[var(--border)] bg-[var(--surface-primary)] flex flex-col justify-between shrink-0">
        <div className="flex flex-col h-full overflow-hidden">
          {/* Header & Create Note */}
          <div className="p-4 border-b border-[var(--border)] flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-[var(--text-primary)]">Notes</h2>
              <span className="text-[11px] text-[var(--text-secondary)]">{notes.length} documents</span>
            </div>
            <button
              type="button"
              onClick={handleCreateNote}
              title="Create New Note"
              className="p-1.5 rounded-xl bg-[var(--surface-secondary)] hover:bg-[var(--border)] text-[var(--text-primary)] transition cursor-pointer"
            >
              <Plus size={16} />
            </button>
          </div>

          {/* Search bar */}
          <div className="p-3 border-b border-[var(--border)]">
            <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl bg-[var(--surface-secondary)] border border-[var(--border)] text-xs">
              <Search size={14} className="text-[var(--text-tertiary)]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search notes..."
                className="w-full bg-transparent focus:outline-none text-[var(--text-primary)] placeholder-[var(--text-tertiary)]"
              />
            </div>
          </div>

          {/* Notes list items */}
          <div className="flex-1 overflow-y-auto aura-scroller p-2 flex flex-col gap-1">
            {filteredNotes.map((note) => {
              const isSelected = activeNote?.id === note.id;
              return (
                <div
                  key={note.id}
                  onClick={() => setSelectedNoteId(note.id)}
                  className={`p-3 rounded-xl border text-left cursor-pointer transition flex flex-col gap-1 group ${
                    isSelected
                      ? 'bg-[var(--surface-secondary)] border-[var(--accent)] shadow-2xs'
                      : 'bg-transparent hover:bg-[var(--surface-secondary)]/50 border-transparent'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[var(--text-primary)] truncate">
                      {note.title || 'Untitled Note'}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteNote(note.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 text-[var(--text-tertiary)] hover:text-rose-600 transition"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] line-clamp-2 leading-snug">
                    {note.content.replace(/[#*`_]/g, '')}
                  </p>
                  <span className="text-[9.5px] text-[var(--text-tertiary)] flex items-center gap-1 mt-0.5">
                    <Calendar size={10} />
                    {note.updatedAt}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Note Editor / Preview Column */}
      <div className="flex-1 flex flex-col h-full bg-[var(--bg-main)] overflow-hidden">
        {activeNote ? (
          <div className="flex-1 flex flex-col h-full p-6 max-w-4xl mx-auto w-full">
            {/* Editor Toolbar */}
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border)] mb-4">
              <input
                type="text"
                value={activeNote.title}
                onChange={(e) => handleUpdateNote('title', e.target.value)}
                placeholder="Note title..."
                className="text-xl font-bold bg-transparent text-[var(--text-primary)] focus:outline-none flex-1"
              />
              <button
                type="button"
                onClick={() => setIsPreview(!isPreview)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-[var(--surface-primary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer"
              >
                {isPreview ? <Edit3 size={13} /> : <Eye size={13} />}
                <span>{isPreview ? 'Edit' : 'Preview'}</span>
              </button>
            </div>

            {/* Editor Canvas */}
            <div className="flex-1 overflow-y-auto aura-scroller">
              {isPreview ? (
                <div className="p-4 bg-[var(--surface-primary)] rounded-2xl border border-[var(--border)] min-h-[400px]">
                  <MarkdownRenderer content={activeNote.content} />
                </div>
              ) : (
                <textarea
                  value={activeNote.content}
                  onChange={(e) => handleUpdateNote('content', e.target.value)}
                  placeholder="Start typing markdown notes here..."
                  className="w-full h-full min-h-[500px] bg-transparent text-[14.5px] font-mono leading-relaxed text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none resize-none select-text"
                />
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-[var(--text-tertiary)] text-xs">
            <FileText size={32} className="mb-2 opacity-50" />
            <span>Select or create a note to begin.</span>
          </div>
        )}
      </div>
    </div>
  );
};
