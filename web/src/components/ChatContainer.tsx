import { useState, type RefObject } from 'react';
import { Clock, ChevronRight } from 'lucide-react';
import StepsSummaryModal, { type ExecutionStep } from './StepsSummaryModal';

interface Message {
  role: string;
  content: string;
  steps?: ExecutionStep[];
  created_at?: string;
}

interface ChatContainerProps {
  messages: Message[];
  isThinking: boolean;
  thinkingStep: { thought: string; tool: string; args: string } | null;
  activeStepLog: ExecutionStep[];
  messagesEndRef: RefObject<HTMLDivElement | null>;
}

function renderContent(text: string) {
  if (!text) return '';

  // Escape HTML tags first
  let escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Extract fenced code blocks: ```lang ... ```
  const codeBlocks: string[] = [];
  escaped = escaped.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, __, code) => {
    const placeholder = `__CODE_BLOCK_PLACEHOLDER_${codeBlocks.length}__`;
    codeBlocks.push(`<pre class="rexio-code-block"><code>${code.trim()}</code></pre>`);
    return placeholder;
  });

  // Extract inline code: `code`
  const inlineCodes: string[] = [];
  escaped = escaped.replace(/`([^`\n]+)`/g, (_, code) => {
    const placeholder = `__INLINE_CODE_PLACEHOLDER_${inlineCodes.length}__`;
    inlineCodes.push(`<code class="rexio-inline-code">${code}</code>`);
    return placeholder;
  });

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

  // Bold: **text**
  escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-white">$1</strong>');

  // Headings
  escaped = escaped.replace(/^### (.*$)/gim, '<h3 class="rexio-h3">$1</h3>');
  escaped = escaped.replace(/^## (.*$)/gim, '<h2 class="rexio-h2">$1</h2>');
  escaped = escaped.replace(/^# (.*$)/gim, '<h1 class="rexio-h1">$1</h1>');

  // Bullet lists: - item
  escaped = escaped.replace(/^[-*] (.+)/gm, '<li class="rexio-li">$1</li>');
  escaped = escaped.replace(/(<li class="rexio-li">.*<\/li>\n?)+/g, match => `<ul class="rexio-ul">${match}</ul>`);

  // Markdown links: [text](url)
  escaped = escaped.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, text, url) => {
    return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="rexio-link">${text}</a>`;
  });

  // Plain URLs (not already inside an href)
  escaped = escaped.replace(/(?<!href=")https?:\/\/[^\s<>"&,)]+/g, (url) => {
    return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="rexio-link">${url}</a>`;
  });

  // Convert newlines to breaks
  escaped = escaped.replace(/\n/g, '<br/>');

  // Restore inline code blocks
  inlineCodes.forEach((html, i) => {
    escaped = escaped.replace(new RegExp(`__INLINE_CODE_PLACEHOLDER_${i}__`, 'g'), html);
  });

  // Restore fenced code blocks
  codeBlocks.forEach((html, i) => {
    escaped = escaped.replace(new RegExp(`__CODE_BLOCK_PLACEHOLDER_${i}__`, 'g'), html);
  });

  // Clean up double spacing next to block tags
  escaped = escaped.replace(/<br\/>(?=<\/?(ul|li|table|thead|tbody|tr|th|td|pre|code|h1|h2|h3))/g, '');
  escaped = escaped.replace(/(<\/(ul|table|pre|h1|h2|h3)>)<br\/>/g, '$1');

  return escaped;
}

function getChipLabel(steps: ExecutionStep[]): string {
  const last = steps[steps.length - 1];
  if (!last) return 'View steps';
  if (/web_search|search_web/i.test(last.tool)) {
    const m = last.args.match(/query=["'](.+?)["']/);
    return m ? `Searched "${m[1]}"` : 'Web search';
  }
  if (/read_file/i.test(last.tool)) {
    const m = last.args.match(/path=["'](.+?)["']/);
    return m ? `Read ${m[1].split('/').pop()}` : 'Read file';
  }
  if (/write_file/i.test(last.tool)) {
    const m = last.args.match(/path=["'](.+?)["']/);
    return m ? `Wrote ${m[1].split('/').pop()}` : 'Wrote file';
  }
  if (/execute_python|run_python/i.test(last.tool)) return 'Executed code';
  return last.tool.replace(/_/g, ' ');
}

export default function ChatContainer({
  messages,
  isThinking,
  thinkingStep,
  activeStepLog,
  messagesEndRef,
}: ChatContainerProps) {
  const [selectedSteps, setSelectedSteps] = useState<ExecutionStep[] | null>(null);
  const [showLive, setShowLive] = useState(false);

  return (
    <>
    <div className="flex-1 flex flex-col bg-transparent relative overflow-hidden">
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
                    <div className="max-w-[82%] rexio-user-content bg-[#2C2C2E] text-white border border-white/[0.04] shadow-sm whitespace-pre-wrap break-words select-text">
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
              
              const hasSteps = msg.steps && msg.steps.length > 0;
              return (
                <div key={index} className="flex flex-col items-start mb-6 px-1 w-full">
                  {/* Icon row + steps chip side by side */}
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-9 h-9 flex items-center justify-center flex-shrink-0 select-none">
                      <img
                        src="/rexio_core_icon.svg"
                        alt="RexiO"
                        className="w-7 h-7 opacity-95"
                      />
                    </div>
                    {hasSteps && (
                      <button
                        onClick={() => setSelectedSteps(msg.steps!)}
                        className="flex items-center gap-1.5 text-[#666] hover:text-[#999] transition-colors text-xs select-none"
                      >
                        <Clock size={11} />
                        <span className="truncate max-w-[260px]">{getChipLabel(msg.steps!)}</span>
                        <ChevronRight size={11} />
                      </button>
                    )}
                  </div>
                  {/* AI Content */}
                  <div
                    className="rexio-ai-content pl-1 w-full text-[#f2f2f2] select-text"
                    dangerouslySetInnerHTML={{ __html: renderContent(msg.content) }}
                  />
                </div>
              );
            })
          )}

          {isThinking && (
            <div className="flex flex-col items-start mb-6 px-1 w-full">
              <div className="flex items-center gap-3">
                <div
                  className="w-9 h-9 flex items-center justify-center flex-shrink-0 select-none"
                  style={{ animation: 'rexio-pulse-scale 0.8s ease-in-out infinite' }}
                >
                  <img
                    src="/rexio_core_icon.svg"
                    alt="RexiO"
                    className="w-7 h-7"
                    style={{ animation: 'rexio-spin 2s linear infinite' }}
                  />
                </div>
                {thinkingStep?.tool && (
                  <button
                    onClick={() => setShowLive(true)}
                    className="flex items-center gap-1.5 text-[#666] hover:text-[#999] transition-colors text-xs select-none"
                    style={{ animation: 'rexio-fadein 0.2s ease-out' }}
                  >
                    <Clock size={11} />
                    <span className="truncate max-w-[260px]">{getChipLabel([{ thought: thinkingStep.thought, tool: thinkingStep.tool, args: thinkingStep.args, observation: '' }])}</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse ml-0.5" />
                  </button>
                )}
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
    </div>

    {selectedSteps && (
      <StepsSummaryModal
        steps={selectedSteps}
        onClose={() => setSelectedSteps(null)}
      />
    )}

    {showLive && (() => {
      const liveSteps: ExecutionStep[] = [
        ...activeStepLog,
        ...(thinkingStep?.tool ? [{ thought: thinkingStep.thought, tool: thinkingStep.tool, args: thinkingStep.args, observation: '...' }] : []),
      ];
      return liveSteps.length > 0 ? (
        <StepsSummaryModal
          steps={liveSteps}
          onClose={() => setShowLive(false)}
        />
      ) : null;
    })()}
    </>
  );
}
