export interface ChatMessage {
  id: string;
  text: string;
  sender: "user" | "bot" | "agent";
  timestamp: Date;
  showSatisfactionRating?: boolean;
}
