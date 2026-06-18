import { useState } from 'react';
import { X, Globe, FileText, Terminal, Zap, ArrowLeft } from 'lucide-react';

export interface ExecutionStep {
  thought: string;
  tool: string;
  args: string;
  observation: string;
}

interface StepsSummaryModalProps {
  steps: ExecutionStep[];
  onClose: () => void;
}

type DrillDown =
  | { type: 'thought'; content: string }
  | { type: 'tool'; step: ExecutionStep };

function getToolIcon(tool: string) {
  if (/search|web|browse/i.test(tool)) return Globe;
  if (/file|read|write/i.test(tool)) return FileText;
  if (/exec|python|run|code/i.test(tool)) return Terminal;
  return Zap;
}

function getActionLabel(tool: string, args: string): string {
  try {
    if (/web_search|search_web/i.test(tool)) {
      const m = args.match(/query=["'](.+?)["']/);
      return `Searched for "${m ? m[1] : args}"`;
    }
    if (/read_file/i.test(tool)) {
      const m = args.match(/path=["'](.+?)["']/);
      return `Read ${m ? m[1].split('/').pop() : args}`;
    }
    if (/write_file/i.test(tool)) {
      const m = args.match(/path=["'](.+?)["']/);
      return `Wrote ${m ? m[1].split('/').pop() : args}`;
    }
    if (/execute_python|run_python/i.test(tool)) return 'Executed Python code';
  } catch {}
  return tool.replace(/_/g, ' ');
}

export default function StepsSummaryModal({ steps, onClose }: StepsSummaryModalProps) {
  const [drillDown, setDrillDown] = useState<DrillDown | null>(null);

  if (drillDown) {
    if (drillDown.type === 'thought') {
      return (
        <div className="fixed inset-0 z-50 bg-[#161616] flex flex-col" style={{ animation: 'rexio-fadein 0.2s ease-out' }}>
          <div className="flex items-center px-5 py-4 border-b border-white/[0.07]">
            <button
              onClick={() => setDrillDown(null)}
              className="mr-4 text-gray-500 hover:text-white transition-colors"
            >
              <ArrowLeft size={20} />
            </button>
            <h2 className="text-white font-semibold text-base">Thought process</h2>
          </div>
          <div className="flex-1 overflow-y-auto px-6 py-5 custom-scrollbar">
            <p className="text-white text-base leading-relaxed whitespace-pre-wrap">{drillDown.content}</p>
          </div>
        </div>
      );
    }

    const { step } = drillDown;
    const label = getActionLabel(step.tool, step.args);
    const Icon = getToolIcon(step.tool);
    return (
      <div className="fixed inset-0 z-50 bg-[#161616] flex flex-col" style={{ animation: 'rexio-fadein 0.2s ease-out' }}>
        <div className="flex items-center px-5 py-4 border-b border-white/[0.07]">
          <button
            onClick={() => setDrillDown(null)}
            className="mr-4 text-gray-500 hover:text-white transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <Icon size={16} className="text-gray-400 mr-2" />
          <h2 className="text-white font-semibold text-base">{label}</h2>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5 custom-scrollbar">
          <div>
            <p className="text-[#666] text-xs font-mono uppercase tracking-widest mb-2">Args</p>
            <p className="text-gray-300 text-sm font-mono bg-white/[0.04] border border-white/[0.06] p-3 rounded-xl whitespace-pre-wrap break-all">
              {step.args}
            </p>
          </div>
          <div>
            <p className="text-[#666] text-xs font-mono uppercase tracking-widest mb-2">Result</p>
            <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">{step.observation}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col justify-end"
      onClick={onClose}
    >
      {/* Scrim */}
      <div className="absolute inset-0 bg-black/50" />

      <div
        className="relative bg-[#1a1a1a] rounded-t-3xl max-h-[75vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
        style={{ animation: 'slideUp 0.28s cubic-bezier(0.32,0.72,0,1)' }}
      >
        {/* Drag handle */}
        <div className="flex justify-center pt-3 pb-1 flex-shrink-0">
          <div className="w-9 h-1 rounded-full bg-white/[0.15]" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 flex-shrink-0">
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
            <X size={20} />
          </button>
          <h2 className="text-white font-semibold text-base">Summary</h2>
          <div className="w-5" />
        </div>

        {/* Timeline */}
        <div className="flex-1 overflow-y-auto px-5 pb-10 pt-1 custom-scrollbar">
          {steps.map((step, idx) => {
            const Icon = getToolIcon(step.tool);
            const label = getActionLabel(step.tool, step.args);
            const isLast = idx === steps.length - 1;

            return (
              <div key={idx} className="flex gap-4">
                {/* Left rail */}
                <div className="flex flex-col items-center w-7 flex-shrink-0">
                  {/* Thought dot */}
                  <div className="w-2 h-2 rounded-full bg-[#484848] mt-2 flex-shrink-0" />
                  <div className="w-px bg-white/[0.07] flex-1 my-1" />
                  {/* Tool icon bubble */}
                  <div className="w-7 h-7 rounded-full bg-white/[0.06] border border-white/[0.08] flex items-center justify-center flex-shrink-0">
                    <Icon size={13} className="text-gray-400" />
                  </div>
                  <div className="w-px bg-white/[0.07] flex-1 my-1" />
                  {/* Observation dot */}
                  <div className={`w-2 h-2 rounded-full bg-[#484848] flex-shrink-0 ${isLast ? 'mb-2' : 'mb-0'}`} />
                  {!isLast && <div className="w-px bg-white/[0.07] flex-1 my-1" />}
                </div>

                {/* Right content */}
                <div className="flex-1 pb-5 space-y-2 min-w-0">
                  {/* Thought */}
                  {step.thought && (
                    <button
                      onClick={() => setDrillDown({ type: 'thought', content: step.thought })}
                      className="w-full text-left group"
                    >
                      <p className="text-[#777] text-sm leading-snug line-clamp-2 mt-1.5 group-hover:text-gray-300 transition-colors">
                        {step.thought}
                      </p>
                    </button>
                  )}

                  {/* Tool action */}
                  <button
                    onClick={() => setDrillDown({ type: 'tool', step })}
                    className="w-full text-left group"
                  >
                    <p className="text-white font-semibold text-sm leading-snug group-hover:text-gray-200 transition-colors">
                      {label}
                    </p>
                  </button>

                  {/* Observation */}
                  {step.observation && (
                    <button
                      onClick={() => setDrillDown({ type: 'tool', step })}
                      className="w-full text-left group"
                    >
                      <p className="text-[#777] text-sm leading-snug line-clamp-2 group-hover:text-gray-300 transition-colors">
                        {step.observation}
                      </p>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
