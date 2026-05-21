<<<<<<< HEAD
import { Droplets, Wallet, AlertTriangle, Gauge } from "lucide-react";
import { motion } from "framer-motion";

interface WelcomeHeroProps {
  onQuickAction: (text: string) => void;
}

const quickActions = [
  { label: "Check balance", icon: Wallet, query: "I want to check my bill balance" },
  { label: "Report outage", icon: AlertTriangle, query: "I want to report a water outage" },
  { label: "Meter reading", icon: Gauge, query: "I need my meter reading" },
];

=======
import { Droplets } from "lucide-react";
import { motion } from "framer-motion";

>>>>>>> 9a7f394 (Initial clean commit for capstone project)
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.3 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } },
};

<<<<<<< HEAD
const WelcomeHero = ({ onQuickAction }: WelcomeHeroProps) => {
=======
const WelcomeHero = () => {
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
<<<<<<< HEAD
      className="flex flex-col items-center justify-center py-8 px-4 text-center"
    >
      <motion.div
        variants={itemVariants}
        className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15"
=======
      className="flex flex-col items-center justify-center px-4 pb-4 pt-8 text-center"
    >
      <motion.div
        variants={itemVariants}
        className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 shadow-sm"
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
      >
        <motion.div
          animate={{ y: [0, -4, 0] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
        >
          <Droplets className="h-7 w-7 text-primary" />
        </motion.div>
      </motion.div>

      <motion.h2 variants={itemVariants} className="text-lg font-semibold text-foreground">
<<<<<<< HEAD
        How can we help you today?
      </motion.h2>
      <motion.p variants={itemVariants} className="mt-1.5 text-sm text-muted-foreground max-w-[260px]">
        Ask about bills, outages, meter readings, or any water service queries.
      </motion.p>

      <motion.div variants={itemVariants} className="mt-5 flex flex-wrap items-center justify-center gap-2">
        {quickActions.map((action, i) => (
          <motion.button
            key={action.label}
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5 + i * 0.12, duration: 0.35, ease: "easeOut" }}
            whileHover={{ scale: 1.06, y: -2, boxShadow: "0 4px 16px hsl(var(--primary) / 0.2)" }}
            whileTap={{ scale: 0.95 }}
            onClick={() => onQuickAction(action.query)}
            className="flex items-center gap-1.5 rounded-full border border-border bg-card px-3.5 py-2 text-xs font-medium text-foreground shadow-sm transition-colors hover:border-primary/40 hover:bg-accent"
          >
            <action.icon className="h-3.5 w-3.5 text-primary" />
            {action.label}
          </motion.button>
        ))}
      </motion.div>
=======
        Welcome to LgWSC Customer Service
      </motion.h2>
      <motion.p variants={itemVariants} className="mt-2 max-w-[280px] text-sm leading-relaxed text-muted-foreground">
        Lukanga Water Supply &amp; Sanitation Company — serving Kabwe, Kapiri Mposhi, Mkushi, Serenje, Mumbwa, Chibombo, Chisamba and surrounding districts.
      </motion.p>
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
    </motion.div>
  );
};

export default WelcomeHero;
