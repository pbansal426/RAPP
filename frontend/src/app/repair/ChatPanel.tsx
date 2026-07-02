'use client';

import { useEffect, useRef, useState } from 'react';
import { AssistantIcon } from '@/app/sharedIcons';

interface ChatPanelProps {
  vin: string;
  vinData: Record<string, unknown> | null;
  symptoms: string;
}

type Message = { sender: 'user' | 'bot'; text: string };

function buildOpeningMessage(vinData: Record<string, unknown> | null, symptoms: string): string {
  const make = vinData ? String(vinData.make ?? '').trim() : '';
  const model = vinData ? String(vinData.model ?? '').trim() : '';
  const vehicle = [make, model].filter(Boolean).join(' ');
  const symptomPhrase = symptoms.trim() ? ` for "${symptoms.trim().split('\n')[0]}"` : '';
  const vehiclePhrase = vehicle ? `your ${vehicle}` : 'your vehicle';
  return `Hey — I see you're working on ${vehiclePhrase}${symptomPhrase}. Have you already disconnected the battery, or are you just getting started?`;
}

export default function ChatPanel({ vinData, symptoms }: ChatPanelProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const userHasRepliedRef = useRef(false);

  // Recompute the opening message as vinData/symptoms arrive from the parent's
  // async load, but stop touching it once the user has joined the conversation.
  useEffect(() => {
    if (userHasRepliedRef.current) return;
    setMessages([{ sender: 'bot', text: buildOpeningMessage(vinData, symptoms) }]);
  }, [vinData, symptoms]);

  const handleSendMessage = () => {
    if (!chatInput.trim()) return;
    userHasRepliedRef.current = true;
    const userMsg = chatInput.trim();
    setMessages((prev) => [...prev, { sender: 'user', text: userMsg }]);
    setChatInput('');

    setTimeout(() => {
      const lower = userMsg.toLowerCase();
      let reply = 'To help you best: follow the safety guidelines in Phase 1, torque all components to OEM spec, and inspect plugs/wiring for contamination.';
      if (lower.includes('torque') || lower.includes('tighten') || lower.includes('lbs') || lower.includes('ft-lbs')) {
        reply = 'OEM Specification: Coil pack mounting bolts torque to 7.5 ft-lbs (10 Nm). Spark plugs torque to 15 ft-lbs (20 Nm) on aluminum heads.';
      } else if (lower.includes('socket') || lower.includes('tool') || lower.includes('wrench') || lower.includes('size')) {
        reply = 'Required tools: 10mm deep socket, 3-inch extension, 3/8-inch drive ratchet. If changing plugs, use a 5/8-inch spark plug socket.';
      } else if (lower.includes('corro') || lower.includes('connector')) {
        reply = 'If you see corrosion on a connector, clean it with electrical contact cleaner and a small brass brush before reconnecting — don’t force a corroded plug.';
      } else if (lower.includes('safety') || lower.includes('disconnect') || lower.includes('battery')) {
        reply = 'Safety protocol: isolate the negative 12V battery terminal first. Let the engine cool at least 45 minutes before working near it to avoid thermal burns.';
      }
      setMessages((prev) => [...prev, { sender: 'bot', text: reply }]);
    }, 600);
  };

  return (
    <aside className={`repair-chat-panel ${drawerOpen ? 'chat-drawer-open' : ''}`}>
      <button
        type="button"
        className="repair-chat-handle"
        onClick={() => setDrawerOpen((o) => !o)}
        aria-expanded={drawerOpen}
      >
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><AssistantIcon size={18} /><span>RAPP Garage Assistant</span></span>
        <span className="repair-chat-handle-chevron" aria-hidden="true">{drawerOpen ? '▾' : '▴'}</span>
      </button>

      <div className="repair-chat-body">
        {messages.map((m, idx) => (
          <div key={idx} className={`repair-chat-bubble ${m.sender === 'user' ? 'repair-chat-bubble-user' : 'repair-chat-bubble-bot'}`}>
            {m.text}
          </div>
        ))}
      </div>

      <div className="repair-chat-input-row">
        <input
          type="text"
          className="input"
          style={{ height: 48, minHeight: 48, padding: '0 12px', fontSize: '0.9rem', flex: 1 }}
          placeholder="Ask about torque, tools, safety..."
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
        />
        <button
          className="btn btn-primary"
          style={{ width: 'auto', height: 48, minHeight: 48, padding: '0 16px', fontSize: '0.9rem' }}
          onClick={handleSendMessage}
        >
          Send
        </button>
      </div>
    </aside>
  );
}
