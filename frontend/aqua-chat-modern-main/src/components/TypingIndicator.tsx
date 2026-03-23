import { motion } from "framer-motion";

const TypingIndicator = () => {
  return (
    <div className="flex items-start gap-2">
      <div className="rounded-2xl rounded-bl-md border border-border/50 bg-chat-bot-bubble px-4 py-3 shadow-sm">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="h-2 w-2 rounded-full bg-primary/50"
              animate={{ y: [0, -6, 0] }}
              transition={{
                duration: 0.6,
                repeat: Infinity,
                delay: i * 0.15,
                ease: "easeInOut",
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default TypingIndicator;
