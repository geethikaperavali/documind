/**
 * DOCUMIND FRONTEND CONFIGURATION
 * Centralized settings for API endpoints and Supabase Auth client.
 */

const CONFIG = {
  // Backend API base URL
  API_BASE_URL: (window.location.port === "8000" || window.location.port === "3000")
    ? `${window.location.origin}/api`
    : "http://localhost:8000/api",

  // Supabase Configuration
  // Initialized dynamically from backend or localStorage, with default fallback
  SUPABASE_URL: localStorage.getItem("documind_supabase_url") || "",
  SUPABASE_ANON_KEY: localStorage.getItem("documind_supabase_anon_key") || "",

  // Polling intervals
  DOCUMENT_POLL_INTERVAL_MS: 3000,
  
  // App Routes
  ROUTES: {
    HOME: "/index.html",
    DASHBOARD: "/index.html",
    DOCUMENTS: "/documents.html",
    CHAT: "/chat.html",
    RESEARCH: "/research.html",
    COMPARE: "/compare.html",
    EXPLORER: "/explorer.html",
    ACTION: "/action.html",
    MONITOR: "/monitor.html",
    SETTINGS: "/settings.html",
    LOGIN: "/login.html",
    SIGNUP: "/signup.html",
    FORGOT_PASSWORD: "/forgot-password.html",
    RESET_PASSWORD: "/reset-password.html"
  }
};

// Export to window
window.CONFIG = CONFIG;
