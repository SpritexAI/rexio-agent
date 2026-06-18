import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageSquare, 
  Terminal, 
  Cpu, 
  Send, 
  Plus, 
  Code, 
  RefreshCw,
  BookOpen
} from 'lucide-react';

interface Message {
  role: string;
  content: string;
  created_at?: string;
}

interface Conversation {
  id: string;
  created_at: string;
  platform: string;
  channel_id: string;
  summary: string | null;
}

interface Skill {
  name: string;
  description: string;
  code: string;
  created_at: string;
}

interface ExecutionStep {
  thought: string;
  tool: string;
  args: string;
  observation: string;
}

const BACKEND_URL = window.location.port === '5173' 
  ? 'http://localhost:8000' 
  : window.location.origin;

export default function App() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string>('default_web_session');
  const [messages, setMessages] = useState<Message[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [inputMessage, setInputMessage] = useState<string>('');
  const [isThinking, setIsThinking] = useState<boolean>(false);
  const [backendStatus, setBackendStatus] = useState<{status: string, model: string}>({ status: 'offline', model: '-' });
  const [activeStepLog, setActiveStepLog] = useState<ExecutionStep[]>([]);
  const [showLogModal, setShowLogModal] = useState<boolean>(false);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch initial data
  useEffect(() => {
    fetchStatus();
    fetchConversations();
    fetchSkills();
  }, []);

  // Fetch messages when active conversation changes
  useEffect(() => {
    if (activeConvId) {
      fetchMessages(activeConvId);
    }
  }, [activeConvId]);

  // Scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/status`);
      const data = await res.json();
      setBackendStatus(data);
    } catch (err) {
      setBackendStatus({ status: 'offline', model: '-' });
    }
  };

  const fetchConversations = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/conversations`);
      const data = await res.json();
      setConversations(data);
      if (data.length > 0 && !activeConvId) {
        setActiveConvId(data[0].id);
      }
    } catch (err) {
      console.error("Error fetching conversations:", err);
    }
  };

  const fetchMessages = async (id: string) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/conversations/${id}/messages`);
      const data = await res.json();
      setMessages(data.messages || []);
    } catch (err) {
      console.error("Error fetching messages:", err);
    }
  };

  const fetchSkills = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/skills`);
      const data = await res.json();
      setSkills(data.skills || []);
    } catch (err) {
      console.error("Error fetching skills:", err);
    }
  };

  const handleCreateSession = () => {
    const newId = `session_${Math.random().toString(36).substr(2, 9)}`;
    setActiveConvId(newId);
    setMessages([]);
    setActiveStepLog([]);
    // Insert a dummy conversation in state for instant UI update
    const newConv: Conversation = {
      id: newId,
      created_at: new Date().toISOString(),
      platform: 'web',
      channel_id: 'dashboard',
      summary: 'New conversation session'
    };
    setConversations(prev => [newConv, ...prev]);
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isThinking) return;

    const userText = inputMessage;
    setInputMessage('');
    setIsThinking(true);
    setActiveStepLog([]);

    // Optimistically update message log in UI
    setMessages(prev => [...prev, { role: 'user', content: userText }]);

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText,
          conversation_id: activeConvId,
          platform: 'web',
          channel_id: 'dashboard'
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const errMsg = errData.detail || "Failed to send message to agent";
        throw new Error(errMsg);
      }

      const data = await res.json();
      setMessages(data.messages || []);
      if (data.execution_log) {
        setActiveStepLog(data.execution_log);
      }
      // Refresh skills and conversations list (in case a new skill was learned or summary updated)
      fetchSkills();
      fetchConversations();
    } catch (err: any) {
      console.error("Error sending message:", err);
      setMessages(prev => [...prev, { role: 'system', content: `Error: ${err.message || "Could not reach agent backend."}` }]);
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <div className="flex h-screen w-screen bg-[#070b14] text-gray-200 overflow-hidden font-sans select-none">
      
      {/* 1. Left Sidebar: Sessions & Status */}
      <div className="w-80 flex flex-col border-r border-gray-800 bg-[#0c1220] flex-shrink-0">
        
        {/* Logo and Status Header */}
        <div className="p-5 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-600/20 text-indigo-400 rounded-lg border border-indigo-500/30">
              <Cpu size={22} className="animate-pulse" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-white flex items-center">
                Aethelis Agent <span className="text-xs text-indigo-400 ml-1.5 font-mono">☤</span>
              </h1>
              <p className="text-[10px] text-gray-500 font-mono">PERSISTENT FRAMEWORK</p>
            </div>
          </div>
          <button onClick={fetchStatus} className="text-gray-500 hover:text-gray-300 transition-colors">
            <RefreshCw size={16} />
          </button>
        </div>

        {/* Server status banner */}
        <div className="px-5 py-3 bg-[#0f172a] border-b border-gray-800 flex items-center space-x-2.5">
          <span className={`w-2 h-2 rounded-full ${backendStatus.status === 'online' ? 'bg-green-500' : 'bg-red-500 animate-ping'}`}></span>
          <span className="text-xs font-mono text-gray-400">
            Backend: {backendStatus.status === 'online' ? `Online (${backendStatus.model})` : 'Offline'}
          </span>
        </div>

        {/* Action Button */}
        <div className="p-4">
          <button 
            onClick={handleCreateSession}
            className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium shadow-md shadow-indigo-600/10 hover:shadow-indigo-600/20 transition-all duration-150 active:scale-[0.98]"
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
            conversations.map(conv => (
              <div 
                key={conv.id}
                onClick={() => setActiveConvId(conv.id)}
                className={`flex items-start space-x-3 p-3 rounded-lg cursor-pointer transition-all duration-150 group ${
                  activeConvId === conv.id 
                    ? 'bg-indigo-600/15 border border-indigo-500/20 text-white' 
                    : 'hover:bg-gray-800/40 border border-transparent text-gray-400 hover:text-gray-200'
                }`}
              >
                <MessageSquare size={18} className="mt-0.5 flex-shrink-0 text-indigo-400 group-hover:text-indigo-300" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-mono font-medium truncate">{conv.id}</p>
                  <p className="text-xs text-gray-500 truncate mt-0.5">{conv.summary || 'No summary available.'}</p>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-800 flex items-center justify-between text-xs text-gray-500 font-mono">
          <span>v0.1.0 (Beta)</span>
          <span>Nous Standard</span>
        </div>
      </div>

      {/* 2. Middle Panel: Chat Window & Trace logs */}
      <div className="flex-1 flex flex-col bg-[#080d19] relative">
        
        {/* Top Chat Header */}
        <div className="h-16 border-b border-gray-800/80 px-6 flex items-center justify-between bg-[#0a0f1d]">
          <div>
            <h2 className="text-sm font-mono font-bold text-white">ACTIVE: {activeConvId}</h2>
            <p className="text-xs text-gray-500">FastAPI Agent webhook streaming</p>
          </div>
          
          {activeStepLog.length > 0 && (
            <button 
              onClick={() => setShowLogModal(true)}
              className="flex items-center space-x-1.5 py-1.5 px-3 bg-cyan-950/40 border border-cyan-800/40 text-cyan-400 hover:bg-cyan-900/40 rounded-lg text-xs font-mono transition-all duration-150"
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
              <div className="p-4 bg-indigo-600/10 text-indigo-400 rounded-full border border-indigo-500/10 mb-4 animate-bounce">
                <Cpu size={36} />
              </div>
              <h3 className="text-lg font-semibold text-white">Ask Aethelis Agent anything</h3>
              <p className="text-sm text-gray-500 mt-2">
                Aethelis will research files, browse the web, execute scripts, and compile new tools as it goes.
              </p>
            </div>
          ) : (
            messages.map((msg, index) => {
              const isUser = msg.role === 'user';
              const isSystem = msg.role === 'system';
              return (
                <div 
                  key={index} 
                  className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-xl rounded-2xl p-4 shadow-sm border ${
                    isUser 
                      ? 'bg-indigo-600 text-white border-indigo-500/30 rounded-tr-none' 
                      : isSystem 
                        ? 'bg-red-950/20 text-red-400 border-red-900/30 rounded-tl-none font-mono text-xs'
                        : 'bg-[#111827] text-gray-200 border-gray-800 rounded-tl-none'
                  }`}>
                    {!isUser && !isSystem && (
                      <div className="flex items-center space-x-1.5 mb-1 text-xs text-indigo-400 font-bold uppercase tracking-wider">
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
              <div className="bg-[#111827] border border-gray-800 text-gray-200 rounded-2xl rounded-tl-none p-4 max-w-xl flex items-center space-x-3">
                <div className="flex space-x-1.5">
                  <div className="w-2.5 h-2.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2.5 h-2.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2.5 h-2.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
                <span className="text-xs text-gray-500 font-mono animate-pulse">Running agent reasoning loop...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-gray-800/80 bg-[#0a0f1d]">
          <form onSubmit={handleSendMessage} className="flex items-center space-x-3">
            <input 
              type="text" 
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask Aethelis to find details, execute code, or build a tool..."
              disabled={isThinking}
              className="flex-1 bg-gray-950/60 border border-gray-800 text-white rounded-xl py-3 px-4 outline-none focus:border-indigo-600 transition-all text-sm disabled:opacity-60"
            />
            <button 
              type="submit"
              disabled={isThinking || !inputMessage.trim()}
              className="p-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-800 text-white rounded-xl hover:shadow-md transition-all duration-150 disabled:text-gray-500"
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>

      {/* 3. Right Sidebar: Skills Inventory */}
      <div className="w-80 flex flex-col border-l border-gray-800 bg-[#0c1220] flex-shrink-0">
        <div className="p-5 border-b border-gray-800 flex items-center space-x-3">
          <BookOpen size={20} className="text-indigo-400" />
          <h2 className="text-sm font-bold text-white">Dynamic Skills Hub</h2>
        </div>
        
        <div className="p-4 bg-indigo-950/20 border-b border-gray-800/80">
          <p className="text-xs text-indigo-300 leading-relaxed font-sans">
            Aethelis dynamically compiles successful agent workflows into reusable Python functions and registers them as real-time tools.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Loaded Skills ({skills.length})</p>
          {skills.length === 0 ? (
            <div className="text-center py-12 text-sm text-gray-600">No custom skills compiled yet</div>
          ) : (
            skills.map(skill => (
              <div 
                key={skill.name}
                onClick={() => setSelectedSkill(skill)}
                className="p-3 bg-gray-950/40 hover:bg-gray-950/70 border border-gray-800/80 rounded-xl cursor-pointer transition-all duration-150 group"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-mono font-bold text-indigo-400 group-hover:text-indigo-300">
                    {skill.name}
                  </span>
                  <Code size={12} className="text-gray-500 group-hover:text-gray-300" />
                </div>
                <p className="text-xs text-gray-400 line-clamp-2 leading-relaxed">{skill.description}</p>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Trace Log Modal */}
      {showLogModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6 animate-fade-in">
          <div className="w-full max-w-4xl bg-[#0b1222] border border-gray-800 rounded-2xl flex flex-col h-[80vh] shadow-2xl">
            <div className="p-5 border-b border-gray-800 flex items-center justify-between bg-[#0a0f1d] rounded-t-2xl">
              <div className="flex items-center space-x-2.5 text-cyan-400">
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
            
            <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-950/40 font-mono text-xs">
              {activeStepLog.map((step, idx) => (
                <div key={idx} className="border border-gray-800 bg-[#0e172a]/60 rounded-xl p-4 space-y-3">
                  <div className="text-cyan-400 font-bold border-b border-gray-800 pb-1.5">
                    Step {idx + 1}
                  </div>
                  
                  {step.thought && (
                    <div>
                      <span className="text-yellow-500 font-bold block mb-1">Thought:</span>
                      <p className="text-gray-300 whitespace-pre-wrap leading-relaxed bg-[#0b101f] p-2.5 rounded-lg border border-gray-900">{step.thought}</p>
                    </div>
                  )}
                  
                  {step.tool && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <span className="text-green-500 font-bold block mb-1">Tool Action:</span>
                        <div className="bg-[#0b101f] p-2.5 rounded-lg border border-gray-900 text-gray-300">
                          <span className="text-indigo-400 font-bold">{step.tool}</span>({step.args})
                        </div>
                      </div>
                      <div>
                        <span className="text-indigo-400 font-bold block mb-1">Observation:</span>
                        <div className="bg-[#0b101f] p-2.5 rounded-lg border border-gray-900 text-gray-400 overflow-x-auto whitespace-pre-wrap max-h-32">
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
      )}

      {/* Skill Detail View Modal */}
      {selectedSkill && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6">
          <div className="w-full max-w-3xl bg-[#0b1222] border border-gray-800 rounded-2xl flex flex-col h-[70vh] shadow-2xl">
            <div className="p-5 border-b border-gray-800 flex items-center justify-between bg-[#0a0f1d] rounded-t-2xl">
              <div>
                <h3 className="font-mono font-bold text-sm text-indigo-400">{selectedSkill.name}</h3>
                <p className="text-xs text-gray-500 mt-1">{selectedSkill.description}</p>
              </div>
              <button 
                onClick={() => setSelectedSkill(null)}
                className="text-gray-400 hover:text-white transition-colors font-mono text-xs"
              >
                [Close]
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-5 bg-gray-950 font-mono text-xs relative">
              <pre className="text-green-400 leading-relaxed overflow-x-auto whitespace-pre-wrap select-text">{selectedSkill.code}</pre>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
