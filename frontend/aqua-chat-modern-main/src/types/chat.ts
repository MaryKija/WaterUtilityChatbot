export interface ChatMessage {
  id: string;
  text: string;
  sender: "user" | "bot" | "agent";
  timestamp: Date;
<<<<<<< HEAD
=======
  showSatisfactionRating?: boolean;
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
}
