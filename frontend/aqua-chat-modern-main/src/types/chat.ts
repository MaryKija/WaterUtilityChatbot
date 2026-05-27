export interface ChatMessage {
  id: string;
  text: string;
  sender: "user" | "bot" | "agent";
  timestamp: Date;
  showSatisfactionRating?: boolean;
  attachment?: {
    type: "statement_card";
    id: string;
    amount: string;
    label: string;
    due_date: string;
    action: string;
  };
}
