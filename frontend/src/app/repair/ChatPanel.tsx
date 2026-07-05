'use client';

import { useEffect, useRef, useState } from 'react';
import { AssistantIcon } from '@/app/sharedIcons';
import { api } from '@/lib/api';
import type { RepairChatRequest, RepairChatResponse, VehicleInfo } from '@/lib/types';

interface ChatPanelProps {
  vin: string;
  vinData: Record<string, unknown> | null;
  symptoms: string;
  repairSteps: string[];
}

type Message = { sender: 'user' | 'bot'; text: string };

// Gemini's free tier is a shared 20-requests/day budget across the whole
// app (VIN OCR + repair generation + this chat) -- capping real AI replies
// per vehicle keeps one chat session from exhausting it, and keeps
// per-message cost bounded regardless of tier. Once exhausted, replies
// fall back to the local canned responses below rather than erroring.
const MAX_AI_REPLIES_PER_VEHICLE = 5;

function chatCountKey(vin: string): string {
  return `rapp_chat_count_${vin}`;
}

function getChatCount(vin: string): number {
  if (typeof window === 'undefined') return 0;
  const raw = localStorage.getItem(chatCountKey(vin));
  const n = raw ? parseInt(raw, 10) : 0;
  return Number.isFinite(n) ? n : 0;
}

function incrementChatCount(vin: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(chatCountKey(vin), String(getChatCount(vin) + 1));
}

function buildOpeningMessage(vinData: Record<string, unknown> | null, symptoms: string): string {
  const make = vinData ? String(vinData.make ?? '').trim() : '';
  const model = vinData ? String(vinData.model ?? '').trim() : '';
  const vehicle = [make, model].filter(Boolean).join(' ');
  const symptomPhrase = symptoms.trim() ? ` for "${symptoms.trim().split('\n')[0]}"` : '';
  const vehiclePhrase = vehicle ? `your ${vehicle}` : 'your vehicle';
  return `Hey — I see you're working on ${vehiclePhrase}${symptomPhrase}. Have you already disconnected the battery, or are you just getting started?`;
}

// Local, zero-cost canned reply -- used whenever the real AI assistant is
// unavailable (no key configured, call failed) or this vehicle has used its
// AI replies for this session. Kept as a graceful degrade, not an error.
function cannedReply(userMsg: string): string {
  const lower = userMsg.toLowerCase();
  if (lower.includes('torque') || lower.includes('tighten') || lower.includes('lbs') || lower.includes('ft-lbs')) {
    return 'OEM Specification: Coil pack mounting bolts torque to 7.5 ft-lbs (10 Nm). Spark plugs torque to 15 ft-lbs (20 Nm) on aluminum heads.';
  }
  if (lower.includes('socket') || lower.includes('tool') || lower.includes('wrench') || lower.includes('size')) {
    return 'Required tools: 10mm deep socket, 3-inch extension, 3/8-inch drive ratchet. If changing plugs, use a 5/8-inch spark plug socket.';
  }
  if (lower.includes('corro') || lower.includes('connector')) {
    return 'If you see corrosion on a connector, clean it with electrical contact cleaner and a small brass brush before reconnecting — don’t force a corroded plug.';
  }
  if (lower.includes('safety') || lower.includes('disconnect') || lower.includes('battery')) {
    return 'Safety protocol: isolate the negative 12V battery terminal first. Let the engine cool at least 45 minutes before working near it to avoid thermal burns.';
  }
  return 'To help you best: follow the safety guidelines in Phase 1, torque all components to OEM spec, and inspect plugs/wiring for contamination.';
}

export default function ChatPanel({ vin, vinData, symptoms, repairSteps }: ChatPanelProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);
  const userHasRepliedRef = useRef(false);

  // Recompute the opening message as vinData/symptoms arrive from the parent's
  // async load, but stop touching it once the user has joined the conversation.
  useEffect(() => {
    if (userHasRepliedRef.current) return;
    setMessages([{ sender: 'bot', text: buildOpeningMessage(vinData, symptoms) }]);
  }, [vinData, symptoms]);

  const handleSendMessage = async () => {
    if (!chatInput.trim() || sending) return;
    userHasRepliedRef.current = true;
    const userMsg = chatInput.trim();
    setMessages((prev) => [...prev, { sender: 'user', text: userMsg }]);
    setChatInput('');
    setSending(true);

    const stripeSessionId = localStorage.getItem(`rapp_unlocked_${vin}`) ?? '';
    const canUseAi =
      stripeSessionId && repairSteps.length > 0 && getChatCount(vin) < MAX_AI_REPLIES_PER_VEHICLE;

    let reply: string | null = null;
    if (canUseAi) {
      try {
        const body: RepairChatRequest = {
          vin,
          vehicle: (vinData as VehicleInfo | null) ?? undefined,
          symptoms,
          repair_steps: repairSteps,
          message: userMsg,
          stripe_session_id: stripeSessionId,
        };
        const res = await api.post<RepairChatResponse>('/api/repair/chat', body);
        reply = res.reply;
        if (reply) incrementChatCount(vin);
      } catch {
        reply = null;
      }
    }

    setMessages((prev) => [...prev, { sender: 'bot', text: reply ?? cannedReply(userMsg) }]);
    setSending(false);
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
          disabled={sending}
        >
          Send
        </button>
      </div>
    </aside>
  );
}
