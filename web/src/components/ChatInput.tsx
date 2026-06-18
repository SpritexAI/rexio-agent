import { Send } from 'lucide-react';

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
  return (
    <div className="p-4 border-t border-white/[0.06] bg-[#0f0f0f]">
      <form onSubmit={handleSendMessage} className="flex items-center space-x-3">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Ask Aethelis to find details, execute code, or build a tool..."
          disabled={isThinking}
          className="flex-1 bg-white/[0.03] border border-white/[0.08] text-white rounded-xl py-3 px-4 outline-none focus:border-[#8b5cf6] transition-all text-sm disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={isThinking || !inputMessage.trim()}
          className="p-3 bg-[#8b5cf6] hover:bg-[#7c3aed] disabled:bg-white/[0.04] text-white rounded-xl hover:shadow-md transition-all duration-150 disabled:text-gray-600"
        >
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
