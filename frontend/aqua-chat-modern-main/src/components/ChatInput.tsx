import { useState, type FormEvent } from "react";
import { Send } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

const ChatInput = ({ onSend, disabled }: ChatInputProps) => {
  const [text, setText] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-3 border-t border-border/50 bg-card px-4 py-3"
    >
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Type your message…"
        disabled={disabled}
        className="flex-1 rounded-xl border border-border bg-chat-input-bg px-4 py-3 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground/60 focus:border-primary/50 focus:bg-card focus:ring-2 focus:ring-primary/10 disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={disabled || !text.trim()}
        className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-[hsl(var(--chat-header-to))] text-primary-foreground shadow-md transition-all hover:-translate-y-0.5 hover:shadow-lg active:translate-y-0 disabled:opacity-40 disabled:hover:translate-y-0 disabled:hover:shadow-md"
      >
        <Send className="h-4.5 w-4.5" />
      </button>
    </form>
  );
};

export default ChatInput;
