import { Cpu, RefreshCw, Plus, MessageSquare } from 'lucide-react';

interface Conversation {
  id: string;
  created_at: string;
  platform: string;
  channel_id: string;
  summary: string | null;
}

interface SidebarProps {
  conversations: Conversation[];
  activeConvId: string;
  setActiveConvId: (id: string) => void;
  backendStatus: { status: string; model: string };
  fetchStatus: () => void;
  handleCreateSession: () => void;
}

export default function Sidebar({
  conversations,
  activeConvId,
  setActiveConvId,
  backendStatus,
  fetchStatus,
  handleCreateSession,
}: SidebarProps) {
  return (
    <div className="w-80 flex flex-col border-r border-white/[0.06] bg-[#1f1f1e] flex-shrink-0">
      {/* Brand Header */}
      <div className="p-5 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-[#8b5cf6]/20 text-[#8b5cf6] rounded-lg border border-[#8b5cf6]/30">
            <Cpu size={22} className="animate-pulse" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center">
              Aethelis Agent <span className="text-xs text-[#8b5cf6] ml-1.5 font-mono">☤</span>
            </h1>
            <p className="text-[10px] text-gray-500 font-mono">PERSISTENT FRAMEWORK</p>
          </div>
        </div>
        <button onClick={fetchStatus} className="text-gray-500 hover:text-white transition-colors">
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Backend Status Banner */}
      <div className="px-5 py-3 bg-white/[0.02] border-b border-white/[0.06] flex items-center space-x-2.5">
        <span className={`w-2 h-2 rounded-full ${backendStatus.status === 'online' ? 'bg-green-500' : 'bg-red-500 animate-ping'}`}></span>
        <span className="text-xs font-mono text-gray-400">
          Backend: {backendStatus.status === 'online' ? `Online (${backendStatus.model})` : 'Offline'}
        </span>
      </div>

      {/* Action Button */}
      <div className="p-4">
        <button
          onClick={handleCreateSession}
          className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-[#8b5cf6] hover:bg-[#7c3aed] text-white rounded-lg font-medium shadow-md shadow-[#8b5cf6]/10 hover:shadow-[#8b5cf6]/20 transition-all duration-150 active:scale-[0.98]"
        >
          <Plus size={18} />
          <span>New Session</span>
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-3 space-y-1.5">
        <p className="text-xs font-semibold text-gray-500 px-2.5 uppercase tracking-wider mb-2">Sessions History</p>
        {conversations.length === 0 ? (
          <div className="text-center py-8 text-sm text-gray-600">No active sessions</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => setActiveConvId(conv.id)}
              className={`flex items-start space-x-3 p-3 rounded-lg cursor-pointer transition-all duration-150 group border ${
                activeConvId === conv.id
                  ? 'bg-white/[0.08] border-white/[0.12] text-white'
                  : 'bg-transparent border-transparent hover:bg-white/[0.04] text-[#b4b4b0] hover:text-white'
              }`}
            >
              <MessageSquare size={18} className="mt-0.5 flex-shrink-0 text-[#8b5cf6] group-hover:text-[#a78bfa]" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-mono font-medium truncate">{conv.id}</p>
                <p className="text-xs text-[#8a8a85] truncate mt-0.5">{conv.summary || 'No summary available.'}</p>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-white/[0.06] flex items-center justify-between text-xs text-[#8a8a85] font-mono">
        <span>v0.1.0 (Beta)</span>
        <span>Nous Standard</span>
      </div>
    </div>
  );
}
