import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("roadsense_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const loginUser = async (email, password) => {
  const response = await apiClient.post("/auth/login", { email, password });
  return response.data;
};

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
  loginUser,
  sendChatbotMessage,
};
