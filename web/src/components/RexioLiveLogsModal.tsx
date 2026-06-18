import { useEffect, useRef } from 'react';
import { X, Circle } from 'lucide-react';

export interface LiveLogEntry {
  id: number;
  type: 'thinking' | 'action' | 'observation' | 'answer_start' | 'separator';
  label?: string;
  content?: string;
  timestamp: string;
}

interface RexioLiveLogsModalProps {
  entries: LiveLogEntry[];
  isStreaming: boolean;
  onClose: () => void;
}

function now() {
  return new Date().toLocaleTimeString('en-US', { hour12: false });
}

export function makeThinkingEntries(thought: string, tool: string, args: string, id: { current: number }): LiveLogEntry[] {
  const entries: LiveLogEntry[] = [];
  if (thought) {
    entries.push({ id: id.current++, type: 'thinking', label: 'Thought', content: thought, timestamp: now() });
  }
  if (tool) {
    entries.push({ id: id.current++, type: 'action', label: 'Action', content: `${tool}(${args})`, timestamp: now() });
  }
  return entries;
}

export function makeObservationEntry(observation: string, id: { current: number }): LiveLogEntry {
  return { id: id.current++, type: 'observation', label: 'Observation', content: observation, timestamp: now() };
}

export function makeSeparatorEntry(id: { current: number }): LiveLogEntry {
  return { id: id.current++, type: 'separator', timestamp: now() };
}

const TYPE_CONFIG = {
  thinking: { dot: 'bg-yellow-400', label: 'text-yellow-400', content: 'text-gray-300' },
  action:   { dot: 'bg-[#a78bfa]',  label: 'text-[#a78bfa]',  content: 'text-[#c4b5fd]' },
  observation: { dot: 'bg-cyan-400', label: 'text-cyan-400',  content: 'text-gray-400' },
  answer_start: { dot: 'bg-green-400', label: 'text-green-400', content: 'text-gray-400' },
  separator: { dot: '', label: '', content: '' },
};

export default function RexioLiveLogsModal({ entries, isStreaming, onClose }: RexioLiveLogsModalProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-end p-5"
      style={{ pointerEvents: 'none' }}
    >
      {/* Modal panel */}
      <div
        className="w-full max-w-2xl h-[70vh] flex flex-col rounded-2xl overflow-hidden shadow-2xl"
        style={{
          pointerEvents: 'auto',
          background: 'rgba(10, 10, 10, 0.96)',
          border: '1px solid rgba(255,255,255,0.07)',
          animation: 'rexio-fadein 0.2s ease-out',
          backdropFilter: 'blur(24px)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/[0.06] flex-shrink-0">
          <div className="flex items-center gap-2.5">
            {/* Traffic lights */}
            <div className="flex gap-1.5">
              <span className="w-3 h-3 rounded-full bg-[#ff5f57]" />
              <span className="w-3 h-3 rounded-full bg-[#febc2e]" />
              <span className="w-3 h-3 rounded-full bg-[#28c840]" />
            </div>
            <span className="font-mono text-xs text-gray-400 ml-1">rexio-live-logs</span>
            {isStreaming && (
              <span className="flex items-center gap-1.5 ml-2">
                <Circle size={6} className="text-green-400 fill-green-400 animate-pulse" />
                <span className="text-[10px] font-mono text-green-400">LIVE</span>
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-600 hover:text-gray-300 transition-colors"
          >
            <X size={15} />
          </button>
        </div>

        {/* Log body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3 font-mono text-xs custom-scrollbar">
          {entries.length === 0 && (
            <p className="text-gray-600 italic">Waiting for agent to start...</p>
          )}

          {entries.map((entry) => {
            if (entry.type === 'separator') {
              return (
                <div key={entry.id} className="border-t border-white/[0.04] my-1" />
              );
            }

            const cfg = TYPE_CONFIG[entry.type] ?? TYPE_CONFIG.thinking;

            return (
              <div key={entry.id} className="flex gap-3 items-start" style={{ animation: 'rexio-fadein 0.2s ease-out' }}>
                {/* Timestamp */}
                <span className="text-gray-600 shrink-0 mt-0.5">{entry.timestamp}</span>

                {/* Dot */}
                <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${cfg.dot}`} />

                {/* Content */}
                <div className="flex-1 min-w-0">
                  {entry.label && (
                    <span className={`font-bold ${cfg.label} mr-2`}>{entry.label}:</span>
                  )}
                  <span className={`${cfg.content} break-words whitespace-pre-wrap leading-relaxed`}>
                    {entry.content}
                  </span>
                </div>
              </div>
            );
          })}

          {isStreaming && (
            <div className="flex gap-3 items-center">
              <span className="text-gray-600">{now()}</span>
              <span className="w-1.5 h-1.5 rounded-full bg-gray-600 animate-pulse" />
              <span className="text-gray-600 italic">running...</span>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}
