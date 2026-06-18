import type { RefObject } from 'react';
import { Terminal } from 'lucide-react';

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
  messages: Message[];
  isThinking: boolean;
  activeStepLog: ExecutionStep[];
  setShowLogModal: (show: boolean) => void;
  messagesEndRef: RefObject<HTMLDivElement | null>;
}

function renderContent(text: string) {
  if (!text) return '';

  // Escape HTML tags first
  let escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Table support (matching RexiO)
  escaped = escaped.replace(/^(\|.+\|\n)((\|[-| :]+\|\n))((\|.+\|\n?)*)/gm, (match) => {
    const rows = match.trim().split('\n').filter(r => r.trim());
    if (rows.length < 2) return match;
    const headerCells = rows[0].split('|').filter(c => c.trim() !== '');
    const bodyRows = rows.slice(2);
    const thead = `<thead><tr>${headerCells.map(c => `<th class="rexio-th">${c.trim()}</th>`).join('')}</tr></thead>`;
    const tbody = `<tbody>${bodyRows.map(row => {
      const cells = row.split('|').filter(c => c.trim() !== '');
      return `<tr>${cells.map(c => `<td class="rexio-td">${c.trim()}</td>`).join('')}</tr>`;
    }).join('')}</tbody>`;
    return `<table class="rexio-table">${thead}${tbody}</table>`;
  });

  // Fenced code blocks: ```lang ... ```
  escaped = escaped.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, __, code) => {
    return `<pre class="rexio-code-block"><code>${code.trim()}</code></pre>`;
  });

  // Inline code: `code`
  escaped = escaped.replace(/`([^`\n]+)`/g, '<code class="rexio-inline-code">$1</code>');

  // Bold: **text**
  escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-white">$1</strong>');

  // Headings
  escaped = escaped.replace(/^### (.*$)/gim, '<h3 class="rexio-h3">$1</h3>');
  escaped = escaped.replace(/^## (.*$)/gim, '<h2 class="rexio-h2">$1</h2>');
  escaped = escaped.replace(/^# (.*$)/gim, '<h1 class="rexio-h1">$1</h1>');

  // Bullet lists: - item
  escaped = escaped.replace(/^[-*] (.+)/gm, '<li class="rexio-li">$1</li>');
  escaped = escaped.replace(/(<li class="rexio-li">.*<\/li>\n?)+/g, match => `<ul class="rexio-ul">${match}</ul>`);

  // Convert newlines to breaks
  escaped = escaped.replace(/\n/g, '<br/>');

  // Clean up double spacing next to block tags
  escaped = escaped.replace(/<br\/>(?=<\/?(ul|li|table|thead|tbody|tr|th|td|pre|code|h1|h2|h3))/g, '');
  escaped = escaped.replace(/(<\/(ul|table|pre|h1|h2|h3)>)<br\/>/g, '$1');

  return escaped;
}

export default function ChatContainer({
  messages,
  isThinking,
  activeStepLog,
  setShowLogModal,
  messagesEndRef,
}: ChatContainerProps) {
  return (
    <div className="flex-1 flex flex-col bg-transparent relative overflow-hidden">
      {/* Top Chat Header */}
      {activeStepLog.length > 0 && (
        <div className="h-14 px-9 flex items-center justify-end bg-transparent flex-shrink-0">
          <button
            onClick={() => setShowLogModal(true)}
            className="flex items-center space-x-1.5 py-1.5 px-3 bg-[#8b5cf6]/10 border border-[#8b5cf6]/25 text-[#a78bfa] hover:bg-[#8b5cf6]/20 rounded-lg text-xs font-mono transition-all duration-150"
          >
            <Terminal size={14} />
            <span>Trace Log ({activeStepLog.length} steps)</span>
          </button>
        </div>
      )}

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto pt-6 px-6 pb-60 custom-scrollbar">
        <div className="max-w-[1120px] w-full mx-auto flex flex-col space-y-6">
          {messages.length === 0 ? (
            <div className="flex-1 min-h-[60vh] flex flex-col items-center justify-center text-center max-w-md mx-auto">
              <div className="mb-5">
                <img
                  src="/rexio_core_icon.svg"
                  alt="RexiO"
                  className="w-14 h-14 opacity-90 drop-shadow-[0_0_18px_rgba(139,92,246,0.45)]"
                />
              </div>
              <h3 className="text-lg font-semibold text-white">Ask RexiO Agent anything</h3>
              <p className="text-sm text-[#8a8a85] mt-2">
                RexiO Agent will research files, browse the web, execute scripts, and compile new tools as it goes.
              </p>
            </div>
          ) : (
            messages.map((msg, index) => {
              const isUser = msg.role === 'user';
              const isSystem = msg.role === 'system';
              
              if (isUser) {
                return (
                  <div key={index} className="flex justify-end mb-4 pl-14 w-full">
                    <div className="max-w-[82%] rexio-user-content bg-[#2C2C2E] text-white border border-white/[0.04] shadow-sm whitespace-pre-wrap break-words">
                      {msg.content}
                    </div>
                  </div>
                );
              }
              
              if (isSystem) {
                return (
                  <div key={index} className="flex justify-start mb-4 w-full">
                    <div className="max-w-xl bg-red-950/20 text-red-400 border border-red-900/30 rounded-2xl rounded-tl-sm p-4 font-mono text-xs">
                      {msg.content}
                    </div>
                  </div>
                );
              }
              
              return (
                <div key={index} className="flex flex-col items-start mb-6 px-1 w-full">
                  <div className="w-9 h-9 flex items-center justify-center flex-shrink-0 select-none mb-2">
                    <img
                      src="/rexio_core_icon.svg"
                      alt="RexiO"
                      className="w-7 h-7 opacity-95"
                    />
                  </div>
                  {/* AI Content */}
                  <div 
                    className="rexio-ai-content pl-1 w-full text-[#f2f2f2]"
                    dangerouslySetInnerHTML={{ __html: renderContent(msg.content) }}
                  />
                </div>
              );
            })
          )}

          {isThinking && (
            <div className="flex flex-col items-start mb-6 px-1 w-full">
              <div className="w-9 h-9 flex items-center justify-center flex-shrink-0 select-none mb-2">
                <img
                  src="/rexio_core_icon.svg"
                  alt="RexiO"
                  className="w-7 h-7 opacity-95 animate-pulse"
                />
              </div>
              <div className="flex items-center space-x-3 bg-white/[0.03] border border-white/[0.08] text-gray-200 rounded-2xl rounded-tl-sm py-3 px-4 max-w-md">
                <div className="flex space-x-1.5">
                  <div className="w-2 h-2 bg-[#8b5cf6] rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-[#8b5cf6] rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-[#8b5cf6] rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
                <span className="text-xs text-gray-500 font-mono animate-pulse">Running agent reasoning loop...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
    </div>
  );
}
