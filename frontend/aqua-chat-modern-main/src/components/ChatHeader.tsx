import { Droplets, Trash2 } from "lucide-react";
import { motion } from "framer-motion";

interface ChatHeaderProps {
  intent: string;
  confidence: string;
  onClear: () => void;
}

const ChatHeader = ({ intent, confidence, onClear }: ChatHeaderProps) => {
  // Hide confidence from customers, only show in debug mode
  const isDebugMode = import.meta.env.DEV || window.location.search.includes('debug=true');
  const showConfidence = isDebugMode && confidence;
  return (
    <div className="relative overflow-hidden bg-gradient-to-r from-primary to-[hsl(var(--chat-header-to))] px-5 py-5">
      {/* Subtle animated background pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute -top-4 -right-4 h-24 w-24 rounded-full bg-[hsl(var(--chat-glow))] blur-2xl" />
        <div className="absolute -bottom-4 -left-4 h-20 w-20 rounded-full bg-[hsl(var(--chat-glow))] blur-2xl" />
      </div>

      <div className="relative flex items-center justify-between gap-3">
        <button
          onClick={onClear}
          className="flex items-center gap-1.5 rounded-lg border border-primary-foreground/20 bg-primary-foreground/10 px-3 py-2 text-xs font-medium text-primary-foreground backdrop-blur-sm transition-all hover:bg-primary-foreground/20 hover:scale-105 active:scale-100">

          <Trash2 className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Clear</span>
        </button>

        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 text-primary-foreground">

          <Droplets className="h-5 w-5" />
          <h1 className="text-lg font-semibold tracking-tight mx-0 my-0">LgWSC Assistant</h1>
        </motion.div>

        <div className="min-w-[120px] rounded-lg bg-primary-foreground/10 px-3 py-2 text-right backdrop-blur-sm">
          <p className="text-xs font-medium text-primary-foreground/90">
            Intent: {intent}
          </p>
          {showConfidence && (
            <p className="mt-0.5 text-[10px] text-primary-foreground/70">
              {confidence}
            </p>
          )}
        </div>
      </div>
    </div>);

};

export default ChatHeader;