import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const handleCopy = (code: string, idx: number) => {
    navigator.clipboard.writeText(code).catch(() => {});
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Simple, clean, secure markdown block parser
  const renderBlocks = () => {
    const lines = content.split('\n');
    const elements: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeLanguage = '';
    let codeContent: string[] = [];
    let codeBlockIndex = 0;

    let inTable = false;
    let tableRows: string[][] = [];

    const flushTable = (key: string) => {
      if (tableRows.length === 0) return null;
      const headers = tableRows[0];
      const rows = tableRows.slice(1);
      const tableElem = (
        <div key={key} className="overflow-x-auto my-3 rounded-xl border border-[var(--border)]">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-[var(--surface-secondary)] border-b border-[var(--border)]">
                {headers.map((h, i) => (
                  <th key={i} className="p-2.5 font-semibold text-[var(--text-primary)]">
                    {h.trim()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rIdx) => (
                <tr
                  key={rIdx}
                  className="border-b border-[var(--border)] last:border-none hover:bg-[var(--surface-secondary)]/50"
                >
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="p-2.5 text-[var(--text-secondary)]">
                      {cell.trim()}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      tableRows = [];
      inTable = false;
      return tableElem;
    };

    lines.forEach((line, lineIdx) => {
      // Code block start / end
      if (line.trim().startsWith('```')) {
        if (!inCodeBlock) {
          inCodeBlock = true;
          codeLanguage = line.trim().slice(3).trim() || 'code';
          codeContent = [];
        } else {
          // Finish code block
          const fullCode = codeContent.join('\n');
          const currentIdx = codeBlockIndex++;
          elements.push(
            <div
              key={`code-${lineIdx}`}
              className="my-3 rounded-xl overflow-hidden border border-[var(--border)] bg-[#1A1918] text-[#F5F2ED] text-xs font-mono"
            >
              <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#242321] text-[#A39E96] border-b border-[#33302C] text-[11px]">
                <span>{codeLanguage}</span>
                <button
                  type="button"
                  onClick={() => handleCopy(fullCode, currentIdx)}
                  className="flex items-center gap-1 hover:text-white transition cursor-pointer"
                >
                  {copiedIndex === currentIdx ? (
                    <>
                      <Check size={12} className="text-emerald-400" />
                      <span>Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy size={12} />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
              <pre className="p-3.5 overflow-x-auto leading-relaxed aura-scroller">
                <code>{fullCode}</code>
              </pre>
            </div>
          );
          inCodeBlock = false;
          codeContent = [];
        }
        return;
      }

      if (inCodeBlock) {
        codeContent.push(line);
        return;
      }

      // Table row detection
      if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
        // Skip separator row |---|---|
        if (/^\|[-:\s|]+\|$/.test(line.trim())) {
          return;
        }
        const cells = line
          .trim()
          .slice(1, -1)
          .split('|');
        tableRows.push(cells);
        inTable = true;
        return;
      } else if (inTable) {
        const table = flushTable(`table-${lineIdx}`);
        if (table) elements.push(table);
      }

      // Headings
      if (line.startsWith('# ')) {
        elements.push(
          <h1 key={lineIdx} className="text-xl font-bold text-[var(--text-primary)] mt-4 mb-2 tracking-tight">
            {line.slice(2)}
          </h1>
        );
        return;
      }
      if (line.startsWith('## ')) {
        elements.push(
          <h2 key={lineIdx} className="text-lg font-semibold text-[var(--text-primary)] mt-3.5 mb-1.5 tracking-tight">
            {line.slice(3)}
          </h2>
        );
        return;
      }
      if (line.startsWith('### ')) {
        elements.push(
          <h3 key={lineIdx} className="text-base font-semibold text-[var(--text-primary)] mt-3 mb-1">
            {line.slice(4)}
          </h3>
        );
        return;
      }

      // Unordered lists
      if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
        const itemText = line.trim().slice(2);
        elements.push(
          <li key={lineIdx} className="ml-5 list-disc text-[14px] text-[var(--text-primary)] leading-relaxed my-0.5">
            {renderInline(itemText)}
          </li>
        );
        return;
      }

      // Ordered lists
      const orderedMatch = line.trim().match(/^(\d+)\.\s+(.*)$/);
      if (orderedMatch) {
        elements.push(
          <li key={lineIdx} className="ml-5 list-decimal text-[14px] text-[var(--text-primary)] leading-relaxed my-0.5">
            {renderInline(orderedMatch[2])}
          </li>
        );
        return;
      }

      // Empty line / paragraph break
      if (!line.trim()) {
        elements.push(<div key={lineIdx} className="h-2" />);
        return;
      }

      // Regular paragraph
      elements.push(
        <p key={lineIdx} className="text-[14.5px] leading-relaxed text-[var(--text-primary)] my-1 select-text">
          {renderInline(line)}
        </p>
      );
    });

    if (inTable) {
      const table = flushTable('table-end');
      if (table) elements.push(table);
    }

    return elements;
  };

  // Inline formatting: **bold**, `code`, *italic*
  const renderInline = (text: string): React.ReactNode => {
    const parts: React.ReactNode[] = [];
    let remaining = text;
    let keyIdx = 0;

    while (remaining) {
      // Inline code `code`
      const codeMatch = remaining.match(/^`([^`]+)`/);
      if (codeMatch) {
        parts.push(
          <code
            key={keyIdx++}
            className="px-1.5 py-0.5 mx-0.5 rounded-md bg-[var(--surface-secondary)] text-[var(--accent)] font-mono text-[12.5px] border border-[var(--border)]"
          >
            {codeMatch[1]}
          </code>
        );
        remaining = remaining.slice(codeMatch[0].length);
        continue;
      }

      // Bold **bold**
      const boldMatch = remaining.match(/^\*\*([^*]+)\*\*/);
      if (boldMatch) {
        parts.push(
          <strong key={keyIdx++} className="font-semibold text-[var(--text-primary)]">
            {boldMatch[1]}
          </strong>
        );
        remaining = remaining.slice(boldMatch[0].length);
        continue;
      }

      // Italic *italic*
      const italicMatch = remaining.match(/^\*([^*]+)\*/);
      if (italicMatch) {
        parts.push(
          <em key={keyIdx++} className="italic text-[var(--text-primary)]">
            {italicMatch[1]}
          </em>
        );
        remaining = remaining.slice(italicMatch[0].length);
        continue;
      }

      // Standard text chunk until next special character
      const nextSpecial = remaining.search(/[`*]/);
      if (nextSpecial === -1) {
        parts.push(remaining);
        break;
      } else if (nextSpecial === 0) {
        parts.push(remaining[0]);
        remaining = remaining.slice(1);
      } else {
        parts.push(remaining.slice(0, nextSpecial));
        remaining = remaining.slice(nextSpecial);
      }
    }

    return parts;
  };

  return <div className="space-y-1">{renderBlocks()}</div>;
};
