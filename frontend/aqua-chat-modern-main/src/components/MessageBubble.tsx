import { motion } from "framer-motion";
import { CheckCheck, Bot, User, Headset } from "lucide-react";
import type { ChatMessage } from "@/types/chat";

interface MessageBubbleProps {
  message: ChatMessage;
  index?: number;
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
      </div>
    </motion.div>
  );
};

function formatMessage(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-primary font-semibold">$1</strong>')
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/\n/g, "<br />");
}

export default MessageBubble;
