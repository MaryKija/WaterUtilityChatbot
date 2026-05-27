import { motion } from "framer-motion";
import { CheckCheck, Bot, User, Headset } from "lucide-react";
import type { ChatMessage } from "@/types/chat";
import SatisfactionRating from "./SatisfactionRating";
import { submitFeedback } from "@/services/api";

interface MessageBubbleProps {
  message: ChatMessage;
  index?: number;
  key?: string | number;
}

const MessageBubble = ({ message, index = 0 }: MessageBubbleProps) => {
  const isUser = message.sender === "user";
  const isAgent = message.sender === "agent";
  const time = message.timestamp.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 18, scale: 0.92, x: isUser ? 20 : -20 }}
      animate={{ opacity: 1, y: 0, scale: 1, x: 0 }}
      transition={{
        duration: 0.4,
        delay: index * 0.06,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      className={`group flex items-end gap-2 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      {/* Floating avatar icon */}
      <motion.div
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: index * 0.06 + 0.15, duration: 0.3, type: "spring", stiffness: 400, damping: 15 }}
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full shadow-md transition-shadow duration-300 ${
          isUser
            ? "bg-primary/15 shadow-primary/10 group-hover:shadow-primary/25 group-hover:shadow-lg"
            : isAgent
              ? "bg-emerald-500/15 shadow-emerald-500/10 group-hover:shadow-emerald-500/25 group-hover:shadow-lg"
              : "bg-primary/10 shadow-primary/10 group-hover:shadow-primary/25 group-hover:shadow-lg"
        }`}
      >
        <motion.div
          animate={{ y: [0, -2, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut", delay: index * 0.3 }}
        >
          {isUser ? (
            <User className="h-3.5 w-3.5 text-primary" />
          ) : isAgent ? (
            <Headset className="h-3.5 w-3.5 text-emerald-600" />
          ) : (
            <Bot className="h-3.5 w-3.5 text-primary" />
          )}
        </motion.div>
      </motion.div>

      {/* Bubble + meta */}
      <div className={`flex max-w-[75%] flex-col ${isUser ? "items-end" : "items-start"}`}>
        {!isUser && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: index * 0.06 + 0.2 }}
            className="mb-1 ml-1 text-[10px] font-medium text-muted-foreground"
          >
            {isAgent ? "Customer Service" : "Assistant"}
          </motion.span>
        )}

        <motion.div
          whileHover={{
            scale: 1.015,
            boxShadow: isUser
              ? "0 6px 24px -4px hsl(var(--primary) / 0.18)"
              : "0 6px 24px -4px hsl(var(--primary) / 0.12)",
          }}
          transition={{ duration: 0.2 }}
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm transition-shadow duration-300 ${
            isUser
              ? "rounded-br-md bg-chat-user-bubble text-foreground group-hover:shadow-md group-hover:shadow-primary/10"
              : isAgent
                ? "rounded-bl-md border border-emerald-500/30 bg-emerald-500/10 text-foreground group-hover:shadow-md group-hover:shadow-emerald-500/10"
                : "rounded-bl-md border border-border/50 bg-chat-bot-bubble text-foreground group-hover:shadow-md group-hover:shadow-primary/10"
          }`}
          dangerouslySetInnerHTML={{ __html: formatMessage(message.text) }}
        />

        {message.attachment && message.attachment.type === "statement_card" && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ delay: 0.15, duration: 0.3 }}
            className="mt-3 w-full max-w-sm rounded-xl border border-primary/20 bg-gradient-to-br from-primary/10 to-primary/5 p-4 shadow-inner"
          >
            <div className="flex items-center justify-between border-b border-border/30 pb-2 mb-3">
              <div>
                <span className="text-[10px] font-bold text-primary/80 uppercase tracking-wider">Statement ID</span>
                <div className="text-xs font-semibold font-mono text-foreground">{message.attachment.id}</div>
              </div>
              <span className="rounded-full bg-primary/20 px-2.5 py-0.5 text-[9px] font-bold text-primary uppercase">
                {message.attachment.label}
              </span>
            </div>

            <div className="flex justify-between items-center mb-4">
              <div>
                <span className="text-[10px] font-medium text-muted-foreground uppercase">Amount Due</span>
                <div className="text-2xl font-extrabold text-foreground font-display">{message.attachment.amount}</div>
              </div>
              <div className="text-right">
                <span className="text-[10px] font-medium text-muted-foreground uppercase">Due Date</span>
                <div className="text-xs font-bold text-foreground">{message.attachment.due_date}</div>
              </div>
            </div>

            <button
              type="button"
              onClick={() => alert(`Opening Statement details for ${message.attachment?.id}...`)}
              className="w-full rounded-lg bg-primary py-2 text-center text-xs font-bold text-primary-foreground shadow-md transition-all hover:bg-primary/95 active:scale-98"
            >
              {message.attachment.action}
            </button>
          </motion.div>
        )}

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: index * 0.06 + 0.3 }}
          className={`mt-1 flex items-center gap-1.5 px-1 text-[10px] text-muted-foreground ${
            isUser ? "flex-row-reverse" : ""
          }`}
        >
          <span>{time}</span>
          {isUser && <CheckCheck className="h-3 w-3 text-primary" />}
        </motion.div>

        {message.showSatisfactionRating && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: index * 0.06 + 0.5 }}
            className="mt-2"
          >
            <SatisfactionRating
              messageId={message.id}
              onRating={(rating, feedback) => {
                void submitFeedback({
                  sessionId: message.id,
                  rating,
                  textFeedback: feedback,
                }).catch((err) => {
                  console.error("Failed to submit feedback", err);
                });
              }}
            />
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

function formatMessage(text: string): string {
  // Strip any remaining markdown bold/italic markers that may come from the backend
  // and convert newlines to <br> for display. No colours, no highlights, no badges.
  return text
    .replace(/\*\*(.*?)\*\*/g, "$1")   // **bold** → plain
    .replace(/\*(.*?)\*/g, "$1")        // *italic* → plain
    .replace(/\n/g, "<br />");
}

export default MessageBubble;
