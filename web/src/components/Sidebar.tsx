import { Plus, MessageSquare, Inbox, Briefcase, Search, Settings, Sidebar as SidebarIcon } from 'lucide-react';

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
    <div className="w-80 flex flex-col border-r border-white/[0.06] bg-[#1f1f1e] h-full overflow-hidden flex-shrink-0 font-sans select-none">
      {/* Header */}
      <div className="p-5 flex items-center justify-between flex-shrink-0">
        <span className="text-xl font-black tracking-tight text-white flex items-center">
          RexiO Agent<span className="text-[#8b5cf6] ml-0.5">.</span>
        </span>
        <button
          onClick={fetchStatus}
          title={`Sync status: ${backendStatus.status}`}
          className="text-white opacity-60 hover:opacity-100 transition-opacity p-1.5 flex items-center justify-center cursor-pointer"
        >
          <SidebarIcon size={18} />
        </button>
      </div>

      {/* Navigation List */}
      <div className="px-2.5 flex flex-col gap-0.5 flex-shrink-0">
        {/* New Chat */}
        <button
          onClick={handleCreateSession}
          className="w-full bg-transparent border-0 rounded-xl py-2 px-3 flex items-center gap-3 text-[#b4b4b0] hover:text-white hover:bg-white/[0.04] transition-all cursor-pointer text-left"
        >
          <Plus size={18} strokeWidth={2.5} />
          <span className="text-sm font-bold">New chat</span>
        </button>

        {/* Chats */}
        <button
          onClick={() => {}}
          className="w-full bg-transparent border-0 rounded-xl py-2 px-3 flex items-center gap-3 text-white bg-white/[0.04] transition-all cursor-pointer text-left"
        >
          <MessageSquare size={16} />
          <span className="text-sm">Chats</span>
        </button>

        {/* Projects */}
        <button
          onClick={() => alert('Projects are locked to Workspace configurations.')}
          className="w-full bg-transparent border-0 rounded-xl py-2 px-3 flex items-center gap-3 text-[#b4b4b0] hover:text-white hover:bg-white/[0.04] transition-all cursor-pointer text-left"
        >
          <Inbox size={16} />
          <span className="text-sm">Projects</span>
        </button>

        {/* Customize */}
        <button
          onClick={() => {}}
          className="w-full bg-transparent border-0 rounded-xl py-2 px-3 flex items-center gap-3 text-[#b4b4b0] hover:text-white hover:bg-white/[0.04] transition-all cursor-pointer text-left"
        >
          <Briefcase size={16} />
          <span className="text-sm">Customize</span>
        </button>
      </div>

      {/* Recents Header */}
      <div className="flex items-center justify-between px-5 pt-5 pb-1.5 flex-shrink-0">
        <span className="text-xs font-semibold text-[#52525b] uppercase tracking-wider">Recents</span>
        <Search size={14} className="text-[#52525b] hover:text-white cursor-pointer transition-colors" />
      </div>

      {/* Sessions list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5 custom-scrollbar">
        {conversations.length === 0 ? (
          <div className="text-center py-8 text-xs text-[#52525b]">No chats yet</div>
        ) : (
          conversations.map((conv) => {
            const isActive = activeConvId === conv.id;
            return (
              <button
                key={conv.id}
                onClick={() => setActiveConvId(conv.id)}
                className={`w-full text-left truncate block py-2 px-4 rounded-xl text-sm transition-all border cursor-pointer ${
                  isActive
                    ? 'bg-white/[0.08] border-white/[0.12] text-white font-semibold'
                    : 'bg-transparent border-transparent hover:bg-white/[0.04] text-[#b4b4b0] hover:text-white'
                }`}
              >
                {conv.summary || conv.id}
              </button>
            );
          })
        )}
      </div>

      {/* User Profile Footer */}
      <div className="border-t border-white/[0.05] p-4 flex-shrink-0">
        <div className="w-full bg-white/[0.03] border border-white/[0.06] rounded-2xl p-3 flex items-center gap-3">
          {/* Avatar (Left) */}
          <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-[#8b5cf6] to-[#d946ef] flex items-center justify-center font-bold text-white text-sm flex-shrink-0 select-none">
            S
          </div>

          {/* Name and Metadata (Middle) */}
          <div className="flex-1 min-w-0 text-left">
            <p className="margin-0 font-semibold text-sm text-gray-200 truncate leading-tight">Sijan</p>
            <p className="margin-0 text-[11px] text-[#8a8a85] truncate mt-0.5">Developer plan</p>
          </div>

          {/* Settings button (Right) */}
          <button className="bg-none border-0 text-[#52525b] hover:text-white cursor-pointer p-1 flex items-center justify-center transition-colors flex-shrink-0">
            <Settings size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
