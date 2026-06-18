import React, { useRef, useEffect } from 'react';
import { Plus, Mic } from 'lucide-react';

interface ChatInputProps {
  inputMessage: string;
  setInputMessage: (msg: string) => void;
  handleSendMessage: (e: React.FormEvent) => void;
  isThinking: boolean;
}

export default function ChatInput({
  inputMessage,
  setInputMessage,
  handleSendMessage,
  isThinking,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize the textarea height based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
    }
  }, [inputMessage]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const form = e.currentTarget.form;
      if (form) {
        form.requestSubmit();
      }
    }
  };

  return (
    <form 
      onSubmit={handleSendMessage} 
      className="px-[22px] pb-[20px] max-w-[885px] w-full mx-auto shrink-0 select-none flex flex-col items-center bg-transparent border-none"
    >
      <div 
        className="bg-[#2c2c2a] rounded-[20px] border border-white/[0.03] focus-within:border-[#8b5cf6]/45 w-full transition-all duration-300 flex flex-col"
        style={{
          paddingTop: '20px',
          paddingBottom: '14px',
          paddingLeft: '21px',
          paddingRight: '21px',
        }}
      >
        {/* Text Area */}
        <textarea
          ref={textareaRef}
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Write a message..."
          disabled={isThinking}
          className="bg-transparent border-none text-[#eeeeee] w-full outline-none resize-none placeholder-zinc-500/60 tracking-wide scrollbar-none"
          style={{
            fontSize: '20px',
            lineHeight: '28px',
            minHeight: '90px',
            maxHeight: '180px',
            fontFamily: 'inherit',
            fontWeight: 300,
            paddingTop: '3px',
          }}
          rows={1}
          onKeyDown={handleKeyDown}
        />

        {/* Action Row */}
        <div className="flex items-center justify-between mt-[16px] w-full bg-transparent">
          {/* Left side actions (Plus Attachment) */}
          <div className="flex items-center gap-[12px]">
            <button 
              type="button"
              onClick={() => alert('Attachments are managed in the Workspace root.')}
              title="Add files or images"
              className="text-zinc-400 hover:text-white transition-colors cursor-pointer flex items-center justify-center p-1 hover:scale-105"
            >
              <Plus size={24} strokeWidth={2} />
            </button>
          </div>

          {/* Right side actions (Mic & Send Button) */}
          <div className="flex items-center gap-[14px]">
            <button 
              type="button"
              onClick={() => alert('Voice input coming soon.')}
              title="Voice input"
              className="text-zinc-400 hover:text-white transition-colors cursor-pointer flex items-center justify-center p-1 hover:scale-105"
            >
              <Mic size={21} strokeWidth={2} />
            </button>

            {isThinking ? (
              <button
                type="button"
                title="Stop generating"
                className="w-[28px] h-[28px] rounded-full flex items-center justify-center border-none cursor-pointer transition-all duration-200 bg-white/10 text-white hover:scale-105"
              >
                <svg viewBox="0 0 24 24" width="13" height="13" fill="white">
                  <rect x="5" y="5" width="14" height="14" rx="2" />
                </svg>
              </button>
            ) : (
              <button
                type="submit"
                disabled={isThinking || !inputMessage.trim()}
                className={`w-[28px] h-[28px] rounded-full flex items-center justify-center border-none transition-all duration-300 ${
                  inputMessage.trim()
                    ? 'bg-red-500 text-white shadow-[0_3px_10px_rgba(239,68,68,0.4)] hover:scale-105 cursor-pointer'
                    : 'bg-white/5 text-zinc-600 cursor-not-allowed'
                }`}
              >
                <svg
                  viewBox="0 0 24 24"
                  width="15"
                  height="15"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="12" y1="19" x2="12" y2="5"></line>
                  <polyline points="5 12 12 5 19 12"></polyline>
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Centered Disclaimer Footer */}
      <div 
        className="text-center text-zinc-500 select-text"
        style={{
          marginTop: '10px',
          fontSize: '12px',
          fontWeight: 400,
          letterSpacing: '0.015em',
        }}
      >
        Aethelis is AI and can make mistakes. Please double-check responses.
      </div>
    </form>
  );
}
