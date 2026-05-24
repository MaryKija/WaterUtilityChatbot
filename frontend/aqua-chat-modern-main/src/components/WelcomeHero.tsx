import { Droplets } from "lucide-react";
import { motion } from "framer-motion";

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

const WelcomeHero = () => {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="flex flex-col items-center justify-center px-4 pb-4 pt-8 text-center"
    >
      <motion.div
        variants={itemVariants}
        className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 shadow-sm"
      >
        <motion.div
          animate={{ y: [0, -4, 0] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
        >
          <Droplets className="h-7 w-7 text-primary" />
        </motion.div>
      </motion.div>

      <motion.h2 variants={itemVariants} className="text-lg font-semibold text-foreground">
        Welcome to LgWSC Customer Service
      </motion.h2>
      <motion.p variants={itemVariants} className="mt-2 max-w-[280px] text-sm leading-relaxed text-muted-foreground">
        Lukanga Water Supply &amp; Sanitation Company — serving Kabwe, Kapiri Mposhi, Mkushi, Serenje, Mumbwa, Chibombo, Chisamba and surrounding districts.
      </motion.p>
    </motion.div>
  );
};

export default WelcomeHero;
