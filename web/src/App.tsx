import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ChatContainer from './components/ChatContainer';
import ChatInput from './components/ChatInput';
import { type ExecutionStep } from './components/StepsSummaryModal';

interface Message {
  role: string;
  content: string;
  steps?: ExecutionStep[];
  created_at?: string;
}

interface Conversation {
  id: string;
  created_at: string;
  platform: string;
  channel_id: string;
  summary: string | null;
}

const BACKEND_URL = window.location.port === '5173'
  ? 'http://localhost:51730'
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
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
  const [thinkingStep, setThinkingStep] = useState<{ thought: string; tool: string; args: string } | null>(null);
  const [activeStepLog, setActiveStepLog] = useState<ExecutionStep[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchStatus();
    fetchConversations();
  }, []);

  useEffect(() => {
    if (activeConvId) {
      fetchMessages(activeConvId);
    }
  }, [activeConvId]);

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
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isThinking) return;

    const userText = inputMessage;
    setInputMessage('');
    setIsThinking(true);
    setThinkingStep(null);
    setActiveStepLog([]);

    setMessages((prev) => [...prev, { role: 'user', content: userText }]);

    const streamingIndex = { current: -1 };
    let firstToken = true;

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText,
          conversation_id: activeConvId,
          platform: 'web',
          channel_id: 'dashboard',
        }),
      });

      if (!res.ok || !res.body) {
        throw new Error('Stream request failed');
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data:')) continue;
          const raw = line.slice(5).trim();
          if (!raw) continue;

          try {
            const event = JSON.parse(raw);

            if (event.type === 'token') {
              if (firstToken) {
                firstToken = false;
                setIsThinking(false);
                setThinkingStep(null);
                setMessages((prev) => {
                  streamingIndex.current = prev.length;
                  return [...prev, { role: 'assistant', content: event.text }];
                });
              } else {
                setMessages((prev) => {
                  const updated = [...prev];
                  const idx = streamingIndex.current;
                  if (idx >= 0 && updated[idx]) {
                    updated[idx] = { ...updated[idx], content: updated[idx].content + event.text };
                  }
                  return updated;
                });
              }
            } else if (event.type === 'thinking') {
              setThinkingStep({ thought: event.thought || '', tool: event.tool || '', args: event.args || '' });
            } else if (event.type === 'step') {
              setActiveStepLog((prev) => [...prev, {
                thought: event.thought || '',
                tool: event.tool || '',
                args: event.args || '',
                observation: event.observation || '',
              }]);
            } else if (event.type === 'done') {
              if (event.execution_log) {
                setActiveStepLog(event.execution_log);
                setMessages((prev) => {
                  const updated = [...prev];
                  const idx = streamingIndex.current;
                  if (idx >= 0 && updated[idx]) {
                    updated[idx] = { ...updated[idx], steps: event.execution_log };
                  }
                  return updated;
                });
              }
              fetchConversations();
            } else if (event.type === 'error') {
              throw new Error(event.message);
            }
          } catch (parseErr: any) {
            if (parseErr?.message && !parseErr.message.includes('JSON')) throw parseErr;
          }
        }
      }
    } catch (err: any) {
      console.error('Stream error:', err);
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

      <div className="flex-1 flex flex-col bg-transparent relative overflow-hidden">
        <ChatContainer
          messages={messages}
          isThinking={isThinking}
          thinkingStep={thinkingStep}
          activeStepLog={activeStepLog}
          messagesEndRef={messagesEndRef}
        />

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
    </div>
  );
}
