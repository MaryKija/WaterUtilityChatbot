import { useState, useRef, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import ChatHeader from "@/components/ChatHeader";
import MessageBubble from "@/components/MessageBubble";
import TypingIndicator from "@/components/TypingIndicator";
import ChatInput from "@/components/ChatInput";
import WelcomeHero from "@/components/WelcomeHero";
import type { ChatMessage } from "@/types/chat";
<<<<<<< HEAD
import { sendMessage, getChatUpdates, clearChat } from "@/services/api";
import { Shield } from "lucide-react";
=======
import { sendMessage, getChatUpdates, clearChat, getSessionUserId } from "@/services/api";
import { Droplets, Shield } from "lucide-react";
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
import { Link } from "react-router-dom";

const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
<<<<<<< HEAD
  text: "👋 Hello! I'm your **Water Utility Assistant**. I can help you with billing inquiries, water quality reports, service requests, and more. How can I help you today?",
=======
  text: "Hello! I'm the LgWSC Customer Service Assistant for Lukanga Water Supply and Sanitation Company. I can help you with billing inquiries, water quality reports, fault reporting, outage updates, and more. How can I help you today?",
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
  sender: "bot",
  timestamp: new Date(),
};

type ChatResponse = {
<<<<<<< HEAD
  reply: string;
=======
  response: string;
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
  intent?: string;
  confidence?: number;
  tier?: string;
  auto_escalated?: boolean;
  escalation_reason?: string | null;
  escalated?: boolean;
};

<<<<<<< HEAD
const Index = () => {
  const USER_ID = "demo-user";
=======
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
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [isTyping, setIsTyping] = useState(false);
  const [intent, setIntent] = useState("-");
  const [confidence, setConfidence] = useState("");
  const [isEscalated, setIsEscalated] = useState(false);
  const [updatesAfter, setUpdatesAfter] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
<<<<<<< HEAD
=======
  const isInitialChat = messages.length <= 1 && !isTyping;
>>>>>>> 9a7f394 (Initial clean commit for capstone project)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, scrollToBottom]);

  // Poll for human-agent replies while escalated.
  useEffect(() => {
    if (!isEscalated) return;

    const interval = window.setInterval(() => {
      void (async () => {
        try {
<<<<<<< HEAD
          const data = (await getChatUpdates(USER_ID, updatesAfter)) as {
=======
          const data = (await getChatUpdates(userId, updatesAfter)) as {
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
            status: "none" | "WAITING" | "ACTIVE" | "CLOSED";
            messages: Array<{ sender: "user" | "bot" | "agent"; text: string; created_at?: string }>;
            next_after: number;
          };

          if (data.status === "none" || data.status === "CLOSED") {
            setIsEscalated(false);
            setUpdatesAfter(0);
            return;
          }

          const newAgentMsgs = (data.messages ?? []).filter((m) => m.sender === "agent");
          if (newAgentMsgs.length > 0) {
            setMessages((prev) => [
              ...prev,
              ...newAgentMsgs.map((m) => ({
                id: `agent-${Date.now()}-${Math.random().toString(16).slice(2)}`,
                text: m.text,
                sender: "agent" as const,
                timestamp: new Date(m.created_at ?? Date.now()),
              })),
            ]);
          }

          setUpdatesAfter(data.next_after ?? updatesAfter);
        } catch {
          // Ignore transient polling errors.
        }
      })();
    }, 2000);

    return () => window.clearInterval(interval);
<<<<<<< HEAD
  }, [isEscalated, updatesAfter]);
=======
  }, [isEscalated, updatesAfter, userId]);
>>>>>>> 9a7f394 (Initial clean commit for capstone project)

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
<<<<<<< HEAD
        const data = (await sendMessage(text)) as ChatResponse;
        const botMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          text: data.reply,
          sender: "bot",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, botMsg]);

        if (data.escalated === true || data.intent === "escalation") {
=======
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
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
          setIsEscalated(true);
        }

        const i = data.intent ?? "-";
        const confPct = typeof data.confidence === "number" ? Math.round(data.confidence * 100) : null;
        setIntent(i);
        setConfidence(confPct != null ? `Confidence: ${confPct}%${data.tier ? ` (${data.tier})` : ""}` : data.tier ? `Tier: ${data.tier}` : "");
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
<<<<<<< HEAD
=======
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
        
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 2).toString(),
<<<<<<< HEAD
            text:
              `I couldn't reach the backend. Please ensure FastAPI is running at http://127.0.0.1:8000 ` +
              `and that the Vite proxy is enabled.\n\nError: ${msg}`,
            sender: "bot",
            timestamp: new Date(),
          },
        ]);
        setIntent("-");
=======
            text: `${errorMessage}\n\n${errorAction}\n\n_If this continues, please contact support or try speaking to an agent._`,
            sender: "bot",
            timestamp: new Date(),
            showSatisfactionRating: false,
          },
        ]);
        setIntent("error");
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
        setConfidence("");
      } finally {
        setIsTyping(false);
      }
    })();
  };

  const handleClear = async () => {
    try {
<<<<<<< HEAD
      await clearChat(USER_ID);
=======
      await clearChat(userId);
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
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
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-[hsl(185,60%,25%)] via-[hsl(200,50%,30%)] to-[hsl(220,40%,20%)] p-4">
      {/* Decorative background orbs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-20 -left-20 h-72 w-72 rounded-full bg-[hsl(var(--chat-glow))] opacity-[0.07] blur-3xl" />
        <div className="absolute -bottom-20 -right-20 h-96 w-96 rounded-full bg-primary opacity-[0.05] blur-3xl" />
      </div>

      {/* Admin shortcut (outside of chat components) */}
      <Link
        to="/admin"
        className="fixed right-4 top-4 z-50 inline-flex items-center gap-2 rounded-xl border border-white/15 bg-black/20 px-3 py-2 text-xs font-medium text-white backdrop-blur-sm transition hover:bg-black/30"
      >
        Admin Panel
        <Shield className="h-3.5 w-3.5" />
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="relative flex h-[700px] w-full max-w-[440px] flex-col overflow-hidden rounded-2xl bg-card shadow-2xl shadow-black/20 ring-1 ring-white/10"
      >
        <ChatHeader intent={intent} confidence={confidence} onClear={handleClear} />

        {/* Messages area */}
        <div className="chat-scrollbar flex flex-1 flex-col gap-3 overflow-y-auto bg-chat-bg p-4">
<<<<<<< HEAD
          {messages.length <= 1 && !isTyping && (
            <WelcomeHero onQuickAction={handleSend} />
          )}
=======
          {isInitialChat && <WelcomeHero />}
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
          {messages.map((msg, i) => (
            <MessageBubble key={msg.id} message={msg} index={i} />
          ))}
          {isTyping && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

<<<<<<< HEAD
=======
        {isInitialChat && (
          <div className="border-t border-border/60 bg-card px-4 py-2.5">
            <div className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-normal text-muted-foreground">
              <Droplets className="h-3 w-3 text-primary" />
              Quick actions
            </div>
            <div className="chat-scrollbar flex gap-2 overflow-x-auto pb-1">
              {suggestedFollowUps.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => handleSend(item.query)}
                  className="shrink-0 rounded-full border border-border bg-chat-input-bg px-3 py-1.5 text-xs font-medium text-foreground shadow-sm transition hover:border-primary/40 hover:bg-accent"
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        )}

>>>>>>> 9a7f394 (Initial clean commit for capstone project)
        <ChatInput onSend={handleSend} disabled={isTyping} />
      </motion.div>
    </div>
  );
};

export default Index;
