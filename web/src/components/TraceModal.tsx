import { Terminal } from 'lucide-react';

interface ExecutionStep {
  thought: string;
  tool: string;
  args: string;
  observation: string;
}

interface TraceModalProps {
  activeStepLog: ExecutionStep[];
  setShowLogModal: (show: boolean) => void;
}

export default function TraceModal({ activeStepLog, setShowLogModal }: TraceModalProps) {
  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6 animate-fade-in">
      <div className="w-full max-w-4xl bg-[#1f1f1e] border border-white/[0.08] rounded-2xl flex flex-col h-[80vh] shadow-2xl">
        {/* Header */}
        <div className="p-5 border-b border-white/[0.08] flex items-center justify-between bg-[#1f1f1e] rounded-t-2xl">
          <div className="flex items-center space-x-2.5 text-[#a78bfa]">
            <Terminal size={18} />
            <h3 className="font-mono font-bold text-sm">Reasoning & Action (ReAct) Trace Log</h3>
          </div>
          <button
            onClick={() => setShowLogModal(false)}
            className="text-gray-400 hover:text-white transition-colors font-mono text-sm"
          >
            [Close]
          </button>
        </div>

        {/* Trace List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-black/40 font-mono text-xs">
          {activeStepLog.map((step, idx) => (
            <div key={idx} className="border border-white/[0.06] bg-white/[0.02] rounded-xl p-4 space-y-3">
              <div className="text-[#a78bfa] font-bold border-b border-white/[0.06] pb-1.5">
                Step {idx + 1}
              </div>

              {step.thought && (
                <div>
                  <span className="text-yellow-500 font-bold block mb-1">Thought:</span>
                  <p className="text-gray-300 whitespace-pre-wrap leading-relaxed bg-black/30 p-2.5 rounded-lg border border-white/[0.04]">
                    {step.thought}
                  </p>
                </div>
              )}

              {step.tool && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <span className="text-green-500 font-bold block mb-1">Tool Action:</span>
                    <div className="bg-black/30 p-2.5 rounded-lg border border-white/[0.04] text-gray-300">
                      <span className="text-[#8b5cf6] font-bold">{step.tool}</span>({step.args})
                    </div>
                  </div>
                  <div>
                    <span className="text-[#a78bfa] font-bold block mb-1">Observation:</span>
                    <div className="bg-black/30 p-2.5 rounded-lg border border-white/[0.04] text-gray-400 overflow-x-auto whitespace-pre-wrap max-h-32">
                      {step.observation}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
