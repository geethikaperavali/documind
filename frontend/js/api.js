/**
 * DOCUMIND API CLIENT
 * Centralized HTTP request helper that injects Supabase JWT access tokens
 * and handles authentication expiration and network errors.
 */

class ApiClient {
  constructor() {
    this.baseUrl = window.CONFIG.API_BASE_URL;
  }

  /**
   * Performs an authenticated fetch call to the FastAPI backend.
   */
  async request(endpoint, options = {}) {
    const url = endpoint.startsWith("http") ? endpoint : `${this.baseUrl}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
    
    // Ensure auth is initialized once and get token
    if (!window.authManager.isInitialized) {
      await window.authManager.init();
    }
    const token = window.authManager.getAccessToken();

    const headers = {
      ...(options.headers || {})
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    // Attach optional custom Gemini API key configured in user settings
    const customGeminiKey = localStorage.getItem("documind_gemini_key");
    if (customGeminiKey) {
      headers["X-Gemini-API-Key"] = customGeminiKey;
    }

    // Do not set Content-Type if sending FormData (browser sets boundary automatically)
    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      // Handle 401 Unauthorized (Expired Session)
      if (response.status === 401) {
        console.warn("[ApiClient] 401 Unauthorized received. Signing out user.");
        await window.authManager.signOut();
        throw new Error("Your session has expired. Please sign in again.");
      }

      // Parse JSON response
      let data = {};
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      } else {
        const text = await response.text();
        data = { message: text };
      }

      if (!response.ok) {
        const errorMsg = data.detail || data.message || `Request failed with status ${response.status}`;
        throw new Error(errorMsg);
      }

      return data;
    } catch (error) {
      console.error(`[ApiClient Error] ${options.method || "GET"} ${url}:`, error);
      throw error;
    }
  }

  // Convenience methods
  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: "GET" });
  }

  post(endpoint, body, options = {}) {
    const isFormData = body instanceof FormData;
    return this.request(endpoint, {
      ...options,
      method: "POST",
      body: isFormData ? body : JSON.stringify(body)
    });
  }

  put(endpoint, body, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: "PUT",
      body: JSON.stringify(body)
    });
  }

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: "DELETE" });
  }
}

window.apiClient = new ApiClient();
