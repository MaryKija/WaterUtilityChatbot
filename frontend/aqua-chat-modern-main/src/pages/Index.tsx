import { useState, useRef, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import ChatHeader from "@/components/ChatHeader";
import MessageBubble from "@/components/MessageBubble";
import TypingIndicator from "@/components/TypingIndicator";
import ChatInput from "@/components/ChatInput";
import WelcomeHero from "@/components/WelcomeHero";
import type { ChatMessage } from "@/types/chat";
import { sendMessage, getChatUpdates, clearChat, getSessionUserId } from "@/services/api";
import { Droplets, Shield } from "lucide-react";
import { Link } from "react-router-dom";

const getMockDate = (hours: number, minutes: number) => {
  const d = new Date();
  d.setHours(hours, minutes, 0, 0);
  return d;
};

const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  text: "Hello! I'm your LgWSC assistant. How can I help with your utility services today?",
  sender: "bot",
  timestamp: getMockDate(9, 41),
};

const MOCK_MESSAGES: ChatMessage[] = [
  WELCOME_MESSAGE,
  {
    id: "mock-2",
    text: "I have a question about my recent water bill",
    sender: "user",
    timestamp: getMockDate(9, 42),
  },
  {
    id: "mock-3",
    text: "I've found your latest statement. It looks like your usage increased by 12% compared to last month. You can view the full breakdown below:",
    sender: "bot",
    timestamp: getMockDate(9, 42),
    attachment: {
      type: "statement_card",
      id: "#W-99283",
      amount: "$142.50",
      label: "Water Usage - Oct 2023",
      due_date: "Nov 15, 2023",
      action: "View Details",
    },
  },
  {
    id: "mock-4",
    text: "Would you like to report a potential leak or set up a payment plan?",
    sender: "bot",
    timestamp: getMockDate(9, 42),
  },
];

type ChatResponse = {
  response: string;
  intent?: string;
  confidence?: number;
  tier?: string;
  auto_escalated?: boolean;
  escalation_reason?: string | null;
  escalated?: boolean;
};

const RATING_EXCLUDED_INTENTS = new Set(["general_chat", "greeting", "escalation", "error"]);

const suggestedFollowUps = [
  { label: "Check my bill", query: "I want to check my bill balance" },
  { label: "Report a fault", query: "I want to report a water fault" },
  { label: "Water quality issue", query: "I want to report a water quality issue" },
  { label: "Outage update", query: "I want an update about a water outage in Kabwe" },
  { label: "Office hours", query: "What are the LgWSC office hours?" },
  { label: "How to pay", query: "How do I pay my water bill?" },
];

const Index = () => {
  const [userId] = useState(() => getSessionUserId());
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [isTyping, setIsTyping] = useState(false);
  const [intent, setIntent] = useState("-");
  const [confidence, setConfidence] = useState("");
  const [isEscalated, setIsEscalated] = useState(false);
  const [updatesAfter, setUpdatesAfter] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isInitialChat = messages.length <= 1 && !isTyping;

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, scrollToBottom]);

  // Establish WebSocket connection for real-time operator overrides
  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    // Fallback to localhost if host is empty (e.g. during local tests)
    const host = window.location.host || "localhost:8000";
    const wsUrl = `${protocol}//${host}/ws/chat/${userId}`;
    
    console.log("Connecting to WebSocket:", wsUrl);
    const socket = new WebSocket(wsUrl);

    socket.onmessage = (event) => {
      try {
        if (event.data === "pong") return;
        const msg = JSON.parse(event.data);
        if (msg && msg.sender === "agent") {
          setIsEscalated(true);
          setMessages((prev) => {
            // Avoid duplicate messages
            if (prev.some((m) => m.text === msg.text && m.sender === "agent")) return prev;
            return [
              ...prev,
              {
                id: `agent-${Date.now()}-${Math.random().toString(16).slice(2)}`,
                text: msg.text,
                sender: "agent" as const,
                timestamp: new Date(msg.created_at ?? Date.now()),
              }
            ];
          });
        }
      } catch (err) {
        console.error("Error parsing WebSocket message:", err);
      }
    };

    // Keepalive ping every 30 seconds
    const pingInterval = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send("ping");
      }
    }, 30000);

    return () => {
      window.clearInterval(pingInterval);
      socket.close();
    };
  }, [userId]);

  const handleSend = (text: string) => {
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      text,
      sender: "user",
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    void (async () => {
      try {
        const data = (await sendMessage(text, userId)) as ChatResponse;
        const isEscalation = data.escalated === true || data.intent === "escalation";
        const botMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          text: data.response,
          sender: "bot",
          timestamp: new Date(),
          showSatisfactionRating: !isEscalation && !RATING_EXCLUDED_INTENTS.has(data.intent ?? ""),
        };
        setMessages((prev) => [...prev, botMsg]);

        if (isEscalation) {
          setIsEscalated(true);
        }

        const i = data.intent ?? "-";
        const confPct = typeof data.confidence === "number" ? Math.round(data.confidence * 100) : null;
        setIntent(i);
        setConfidence(confPct != null ? `Confidence: ${confPct}%${data.tier ? ` (${data.tier})` : ""}` : data.tier ? `Tier: ${data.tier}` : "");
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        const isNetworkError = msg.includes('fetch') || msg.includes('network') || msg.includes('ECONNREFUSED');
        const isTimeoutError = msg.includes('timeout') || msg.includes('AbortError');
        
        let errorMessage = "I'm having trouble connecting right now.";
        let errorAction = "Please try again in a moment.";
        
        if (isNetworkError) {
          errorMessage = "Connection lost";
          errorAction = "Please check your internet connection and try again.";
        } else if (isTimeoutError) {
          errorMessage = "Request timed out";
          errorAction = "The service is taking longer than expected. Please try again.";
        } else if (msg.includes('500')) {
          errorMessage = "Service temporarily unavailable";
          errorAction = "Our systems are experiencing issues. Please try again later.";
        }
        
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 2).toString(),
            text: `${errorMessage}\n\n${errorAction}\n\n_If this continues, please contact support or try speaking to an agent._`,
            sender: "bot",
            timestamp: new Date(),
            showSatisfactionRating: false,
          },
        ]);
        setIntent("error");
        setConfidence("");
      } finally {
        setIsTyping(false);
      }
    })();
  };

  const handleClear = async () => {
    try {
      await clearChat(userId);
    } catch {
      // If clearing fails, still reset local UI state.
    }

    setMessages([WELCOME_MESSAGE]);
    setIntent("-");
    setConfidence("");
    setIsEscalated(false);
    setUpdatesAfter(0);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-[hsl(185,60%,25%)] via-[hsl(200,50%,30%)] to-[hsl(220,40%,20%)] p-4 sm:p-6">
      {/* Decorative background orbs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-20 -left-20 h-72 w-72 rounded-full bg-[hsl(var(--chat-glow))] opacity-[0.07] blur-3xl" />
        <div className="absolute -bottom-20 -right-20 h-96 w-96 rounded-full bg-primary opacity-[0.05] blur-3xl" />
      </div>

      {/* Admin shortcut (outside of chat components) */}
      <Link
        to="/admin"
        className="fixed right-4 top-4 z-50 inline-flex items-center gap-2 rounded-xl border border-white/15 bg-black/20 px-3 py-2 text-xs font-medium text-white backdrop-blur-sm transition hover:bg-black/30 animate-pulse hover:animate-none"
      >
        Admin Panel
        <Shield className="h-3.5 w-3.5" />
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="relative flex h-[800px] max-h-[90vh] w-full max-w-[440px] flex-col overflow-hidden rounded-2xl bg-card shadow-2xl shadow-black/20 ring-1 ring-white/10"
      >
        <ChatHeader intent={intent} confidence={confidence} onClear={handleClear} />

        {/* Messages area */}
        <div className="chat-scrollbar flex flex-1 flex-col gap-4 overflow-y-auto bg-chat-bg p-6">
          {isInitialChat && <WelcomeHero />}
          {messages.map((msg, i) => (
            <MessageBubble key={msg.id} message={msg} index={i} />
          ))}
          {isTyping && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        {/* Persistent Quick Actions Grid */}
        <div className="border-t border-border/60 bg-card px-6 py-3.5">
          <div className="mb-2 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            <Droplets className="h-3 w-3 text-primary animate-pulse" />
            Quick actions
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-6">
            {suggestedFollowUps.map((item) => (
              <button
                key={item.label}
                type="button"
                onClick={() => handleSend(item.query)}
                className="rounded-xl border border-border/60 bg-chat-input-bg px-3 py-2 text-xs font-semibold text-foreground shadow-sm transition-all hover:border-primary/40 hover:bg-accent/50 hover:shadow active:scale-95 text-center overflow-hidden text-ellipsis whitespace-nowrap"
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <ChatInput onSend={handleSend} disabled={isTyping} />

        {/* Footer legal warning disclaimer */}
        <div className="bg-card px-6 py-2 border-t border-border/40 text-center">
          <p className="text-[10px] font-medium text-muted-foreground/80 tracking-wide m-0">
            LgWSC assistant may provide automated information. Verify important billing details.
          </p>
        </div>
      </motion.div>
    </div>
  );
};

export default Index;
