import { useState } from "react";
import { Star, ThumbsUp, ThumbsDown } from "lucide-react";
import { motion } from "framer-motion";

interface SatisfactionRatingProps {
  onRating: (rating: number, feedback?: string) => void;
  messageId: string;
}

const SatisfactionRating = ({ onRating, messageId }: SatisfactionRatingProps) => {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [rating, setRating] = useState<number | null>(null);

  const handleRating = (selectedRating: number) => {
    setRating(selectedRating);
    if (selectedRating <= 3) {
      setShowFeedback(true);
    } else {
      onRating(selectedRating);
    }
  };

  const submitFeedback = () => {
    if (rating !== null) {
      onRating(rating, feedback);
      setShowFeedback(false);
      setFeedback("");
    }
  };

  const skipFeedback = () => {
    if (rating !== null) {
      onRating(rating);
      setShowFeedback(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-3 rounded-lg border border-border/50 bg-card/50 p-3"
    >
      <div className="mb-2">
        <p className="text-sm font-medium text-foreground mb-2">
          How satisfied are you with this response?
        </p>
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map((star) => (
              <motion.button
                key={star}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => handleRating(star)}
                className={`p-1 rounded transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none ${
                  rating === star
                    ? "text-yellow-500"
                    : "text-gray-400 hover:text-yellow-400"
                }`}
                aria-label={`Rate ${star} star${star !== 1 ? "s" : ""}`}
              >
                <Star className={`h-4 w-4 ${rating === star ? "fill-current" : ""}`} aria-hidden="true" />
              </motion.button>
            ))}
          </div>
          <div className="flex gap-1 ml-4">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => handleRating(5)}
              className={`p-2 rounded-full transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none ${
                rating === 5
                  ? "bg-green-100 text-green-700"
                  : "bg-gray-100 text-gray-600 hover:bg-green-50 hover:text-green-600"
              }`}
              aria-label="Thumbs up"
            >
              <ThumbsUp className="h-4 w-4" aria-hidden="true" />
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => handleRating(1)}
              className={`p-2 rounded-full transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none ${
                rating === 1
                  ? "bg-red-100 text-red-700"
                  : "bg-gray-100 text-gray-600 hover:bg-red-50 hover:text-red-600"
              }`}
              aria-label="Thumbs down"
            >
              <ThumbsDown className="h-4 w-4" aria-hidden="true" />
            </motion.button>
          </div>
        </div>
      </div>

      {showFeedback && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="mt-3 space-y-2"
        >
          <p className="text-sm text-muted-foreground">
            Could you help us improve? What was unsatisfactory about this response?
          </p>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Please share your feedback..."
            aria-label="Please explain why the response was unsatisfactory"
            className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/60 resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
            rows={3}
          />
          <div className="flex gap-2">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={submitFeedback}
              className="flex-1 rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm font-medium hover:bg-primary/90 transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
            >
              Submit Feedback
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={skipFeedback}
              className="rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
            >
              Skip
            </motion.button>
          </div>
        </motion.div>
      )}

      {rating !== null && !showFeedback && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-2 text-xs text-muted-foreground"
        >
          Thank you for your feedback!
        </motion.div>
      )}
    </motion.div>
  );
};

export default SatisfactionRating;
