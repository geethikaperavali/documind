/**
 * DOCUMIND FRONTEND CONFIGURATION
 * Centralized settings for API endpoints and Supabase Auth client.
 * Automatically switches between local development and production Render backend.
 */

// Production Render backend URL
const PRODUCTION_BACKEND_URL = "https://documind-imh0.onrender.com";

// Determine active backend URL:
// 1. Explicit override saved by developer/user in localStorage
// 2. Local development environments (localhost or 127.0.0.1 on ports 8000, 5500, 3000, etc.)
// 3. Deployed production environments (e.g. *.vercel.app) -> PRODUCTION_BACKEND_URL
const isLocalhost = Boolean(
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1" ||
  window.location.hostname === "" ||
  window.location.protocol === "file:"
);

const BACKEND_URL = localStorage.getItem("documind_api_url") || (
  isLocalhost
    ? ((window.location.port === "8000" || window.location.port === "3000")
        ? window.location.origin
        : "http://localhost:8000")
    : PRODUCTION_BACKEND_URL
);

const CONFIG = {
  // Production fallback backend URL
  PRODUCTION_BACKEND_URL: PRODUCTION_BACKEND_URL,

  // Active Backend API base URL
  API_BASE_URL: `${BACKEND_URL.replace(/\/+$/, "")}/api`,

  // Supabase Configuration
  // Initialized dynamically from backend (/api/auth/config) or localStorage
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
