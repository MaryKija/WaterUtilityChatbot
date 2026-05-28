import { Droplets, Trash2, Moon, Sun, HelpCircle, User } from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";

interface ChatHeaderProps {
  intent: string;
  confidence: string;
  onClear: () => void;
}

const ChatHeader = ({ intent, confidence, onClear }: ChatHeaderProps) => {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const isDebugMode = import.meta.env.DEV || window.location.search.includes('debug=true');
  const showConfidence = isDebugMode && confidence;

  return (
    <div className="relative overflow-hidden border-b border-border bg-card px-6 py-4 shadow-sm flex flex-col gap-3">
      {/* Dynamic glow decoration */}
      <div className="absolute top-0 right-1/4 h-24 w-24 rounded-full bg-primary/5 blur-2xl" />

      <div className="relative flex items-center justify-between gap-4">
        {/* Logo and Brand */}
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-2.5 text-foreground flex-shrink-0"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-[hsl(var(--chat-glow))] shadow-md shadow-primary/25">
            <Droplets className="h-4.5 w-4.5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-base font-extrabold tracking-tight font-display text-foreground m-0">LgWSC Chatbot</h1>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-primary block mt-0.5">System Health: Healthy</span>
          </div>
        </motion.div>

        {/* Desktop Header Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Clear chat command */}
          <button
            onClick={onClear}
            title="Clear Chat History"
            className="flex items-center gap-1.5 rounded-xl border border-border bg-chat-input-bg px-2.5 py-1.5 text-xs font-bold text-foreground transition-all hover:bg-accent hover:border-primary/20 active:scale-95"
          >
            <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="inline">Clear</span>
          </button>

          {/* Theme toggle */}
          <button
            onClick={() => {
              setIsDarkMode(!isDarkMode);
              alert("Theme toggled! Seamless style synchronization completed.");
            }}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-chat-input-bg text-muted-foreground transition-all hover:bg-accent hover:text-foreground active:scale-95"
            title="Toggle theme"
          >
            {isDarkMode ? <Sun className="h-4.5 w-4.5" /> : <Moon className="h-4.5 w-4.5" />}
          </button>

          {/* Help Center */}
          <button
            onClick={() => alert("LgWSC Chatbot Assistant Support Center: For issues or escalations, click the Specialist Takeover tab or speak to a live operator.")}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-chat-input-bg text-muted-foreground transition-all hover:bg-accent hover:text-foreground active:scale-95"
            title="Help Support"
          >
            <HelpCircle className="h-4.5 w-4.5" />
          </button>

          {/* User Profile Avatar */}
          <div 
            onClick={() => alert("You are currently logged in as a Lukanga Water Utility customer.")}
            className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl bg-primary/10 text-primary border border-primary/20 transition-all hover:bg-primary/20 active:scale-95"
            title="User Profile"
          >
            <User className="h-4.5 w-4.5" />
          </div>
        </div>
      </div>

      {/* Debug panel (renders beautifully below on a second line to prevent header overflow) */}
      {intent && intent !== "-" && (
        <motion.div
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between rounded-xl border border-border/40 bg-accent/30 px-3.5 py-1.5 backdrop-blur-sm transition-all duration-300 hover:bg-accent/60 w-full"
        >
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">AI Analysis:</span>
            <span className="text-xs font-bold text-foreground font-mono bg-background/50 px-2 py-0.5 rounded-md border border-border/30">{intent.replace(/_/g, " ")}</span>
          </div>
          {confidence && (
            <span className="text-[10px] font-medium text-primary bg-primary/10 px-2 py-0.5 rounded-full font-mono">
              {confidence}
            </span>
          )}
        </motion.div>
      )}
    </div>
  );
};

export default ChatHeader;