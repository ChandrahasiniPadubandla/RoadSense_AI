import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Send message and chat history to the chatbot backend
 */
export const sendChatbotMessage = async (message, history = []) => {
  const response = await apiClient.post("/api/chatbot/message", {
    message,
    history,
  });
  return response.data;
};

export default {
  sendChatbotMessage,
};
