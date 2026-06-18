import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ChatContainer from './components/ChatContainer';
import ChatInput from './components/ChatInput';
import TraceModal from './components/TraceModal';

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
  const [inputMessage, setInputMessage] = useState<string>('');
  const [isThinking, setIsThinking] = useState<boolean>(false);
  const [backendStatus, setBackendStatus] = useState<{ status: string; model: string }>({
    status: 'offline',
    model: '-',
  });
  const [activeStepLog, setActiveStepLog] = useState<ExecutionStep[]>([]);
  const [showLogModal, setShowLogModal] = useState<boolean>(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch initial data
  useEffect(() => {
    fetchStatus();
    fetchConversations();
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
      console.error('Error fetching conversations:', err);
    }
  };

  const fetchMessages = async (id: string) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/conversations/${id}/messages`);
      const data = await res.json();
      setMessages(data.messages || []);
    } catch (err) {
      console.error('Error fetching messages:', err);
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
      summary: 'New conversation session',
    };
    setConversations((prev) => [newConv, ...prev]);
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isThinking) return;

    const userText = inputMessage;
    setInputMessage('');
    setIsThinking(true);
    setActiveStepLog([]);

    // Optimistically update message log in UI
    setMessages((prev) => [...prev, { role: 'user', content: userText }]);

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText,
          conversation_id: activeConvId,
          platform: 'web',
          channel_id: 'dashboard',
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const errMsg = errData.detail || 'Failed to send message to agent';
        throw new Error(errMsg);
      }

      const data = await res.json();
      setMessages(data.messages || []);
      if (data.execution_log) {
        setActiveStepLog(data.execution_log);
      }
      // Refresh conversations list
      fetchConversations();
    } catch (err: any) {
      console.error('Error sending message:', err);
      setMessages((prev) => [
        ...prev,
        { role: 'system', content: `Error: ${err.message || 'Could not reach agent backend.'}` },
      ]);
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <div className="flex h-screen w-screen bg-[#1f1f1e] text-gray-200 overflow-hidden font-sans select-none relative">
      <div 
        className="fixed inset-0 -z-10 w-full h-full pointer-events-none"
        style={{
          backgroundColor: '#1f1f1e',
          backgroundImage: 'radial-gradient(rgba(192, 132, 252, 0.05) 1.2px, transparent 1.2px)',
          backgroundSize: '32px 32px',
        }}
      />
      {/* 1. Left Sidebar: Sessions & Status */}
      <Sidebar
        conversations={conversations}
        activeConvId={activeConvId}
        setActiveConvId={setActiveConvId}
        backendStatus={backendStatus}
        fetchStatus={fetchStatus}
        handleCreateSession={handleCreateSession}
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
      />

      {/* 2. Middle Panel: Chat Window & Input Bar */}
      <div className="flex-1 flex flex-col bg-transparent relative overflow-hidden">
        <ChatContainer
          messages={messages}
          isThinking={isThinking}
          activeStepLog={activeStepLog}
          setShowLogModal={setShowLogModal}
          messagesEndRef={messagesEndRef}
        />
        
        {/* Floating Input Box Wrapper with gradient background to fade messages */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-[#1f1f1e] via-[#1f1f1e]/90 to-transparent pt-12 pb-0 z-10 pointer-events-none">
          <div className="pointer-events-auto w-full">
            <ChatInput
              inputMessage={inputMessage}
              setInputMessage={setInputMessage}
              handleSendMessage={handleSendMessage}
              isThinking={isThinking}
            />
          </div>
        </div>
      </div>

      {/* Trace Log Modal */}
      {showLogModal && (
        <TraceModal activeStepLog={activeStepLog} setShowLogModal={setShowLogModal} />
      )}
    </div>
  );
}
