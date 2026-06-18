import type { RefObject } from 'react';
import { Cpu, Terminal } from 'lucide-react';

interface Message {
  role: string;
  content: string;
  created_at?: string;
}

interface ExecutionStep {
  thought: string;
  tool: string;
  args: string;
  observation: string;
}

interface ChatContainerProps {
  activeConvId: string;
  messages: Message[];
  isThinking: boolean;
  activeStepLog: ExecutionStep[];
  setShowLogModal: (show: boolean) => void;
  messagesEndRef: RefObject<HTMLDivElement | null>;
}

export default function ChatContainer({
  activeConvId,
  messages,
  isThinking,
  activeStepLog,
  setShowLogModal,
  messagesEndRef,
}: ChatContainerProps) {
  return (
    <div className="flex-1 flex flex-col bg-[#0f0f0f] relative overflow-hidden">
      {/* Top Chat Header */}
      <div className="h-16 border-b border-white/[0.06] px-6 flex items-center justify-between bg-[#0f0f0f] flex-shrink-0">
        <div>
          <h2 className="text-sm font-mono font-bold text-white">ACTIVE: {activeConvId}</h2>
          <p className="text-xs text-gray-500">FastAPI Agent webhook streaming</p>
        </div>

        {activeStepLog.length > 0 && (
          <button
            onClick={() => setShowLogModal(true)}
            className="flex items-center space-x-1.5 py-1.5 px-3 bg-[#8b5cf6]/10 border border-[#8b5cf6]/25 text-[#a78bfa] hover:bg-[#8b5cf6]/20 rounded-lg text-xs font-mono transition-all duration-150"
          >
            <Terminal size={14} />
            <span>Trace Log ({activeStepLog.length} steps)</span>
          </button>
        )}
      </div>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto">
            <div className="p-4 bg-[#8b5cf6]/10 text-[#8b5cf6] rounded-full border border-[#8b5cf6]/10 mb-4 animate-bounce">
              <Cpu size={36} />
            </div>
            <h3 className="text-lg font-semibold text-white">Ask Aethelis Agent anything</h3>
            <p className="text-sm text-[#8a8a85] mt-2">
              Aethelis will research files, browse the web, execute scripts, and compile new tools as it goes.
            </p>
          </div>
        ) : (
          messages.map((msg, index) => {
            const isUser = msg.role === 'user';
            const isSystem = msg.role === 'system';
            return (
              <div key={index} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-xl rounded-2xl p-4 shadow-sm border ${
                    isUser
                      ? 'bg-[#8b5cf6] text-white border-[#8b5cf6]/30 rounded-tr-none'
                      : isSystem
                      ? 'bg-red-950/20 text-red-400 border-red-900/30 rounded-tl-none font-mono text-xs'
                      : 'bg-white/[0.03] text-gray-200 border-white/[0.08] rounded-tl-none'
                  }`}
                >
                  {!isUser && !isSystem && (
                    <div className="flex items-center space-x-1.5 mb-1 text-xs text-[#8b5cf6] font-bold uppercase tracking-wider">
                      <Cpu size={12} />
                      <span>Aethelis</span>
                    </div>
                  )}
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            );
          })
        )}

        {isThinking && (
          <div className="flex justify-start">
            <div className="bg-white/[0.03] border border-white/[0.08] text-gray-200 rounded-2xl rounded-tl-none p-4 max-w-xl flex items-center space-x-3">
              <div className="flex space-x-1.5">
                <div
                  className="w-2.5 h-2.5 bg-[#8b5cf6] rounded-full animate-bounce"
                  style={{ animationDelay: '0ms' }}
                ></div>
                <div
                  className="w-2.5 h-2.5 bg-[#8b5cf6] rounded-full animate-bounce"
                  style={{ animationDelay: '150ms' }}
                ></div>
                <div
                  className="w-2.5 h-2.5 bg-[#8b5cf6] rounded-full animate-bounce"
                  style={{ animationDelay: '300ms' }}
                ></div>
              </div>
              <span className="text-xs text-gray-500 font-mono animate-pulse">Running agent reasoning loop...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
