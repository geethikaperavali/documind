/**
 * DOCUMIND AUTHENTICATION MANAGER
 * Integrates Supabase Auth for Email + Google OAuth, session maintenance,
 * route guards, and UI user badge population.
 */

class AuthManager {
  constructor() {
    this.supabase = null;
    this.session = null;
    this.user = null;
    this.isInitialized = false;
    this._initPromise = null;
  }

  /**
   * Initializes Supabase Auth client by querying backend configuration
   * or reading cached credentials.
   */
  async init() {
    if (this._initPromise) return this._initPromise;

    this._initPromise = (async () => {
      // 1. Fetch public Supabase configuration from FastAPI backend
      try {
        const res = await fetch(`${window.CONFIG.API_BASE_URL}/auth/config`);
        if (res.ok) {
          const cfg = await res.json();
          if (cfg.supabase_url && cfg.supabase_anon_key) {
            window.CONFIG.SUPABASE_URL = cfg.supabase_url;
            window.CONFIG.SUPABASE_ANON_KEY = cfg.supabase_anon_key;
          }
        }
      } catch (err) {
        console.warn("[DocuMind Auth] Could not reach /api/auth/config, using existing config:", err);
      }

      const supabaseUrl = window.CONFIG.SUPABASE_URL;
      const supabaseAnonKey = window.CONFIG.SUPABASE_ANON_KEY;

      if (!supabaseUrl || !supabaseAnonKey) {
        console.warn("[DocuMind Auth] Supabase URL or Anon Key is missing. Please configure them in .env or Settings.");
      } else if (window.supabase) {
        this.supabase = window.supabase.createClient(supabaseUrl, supabaseAnonKey, {
          auth: {
            persistSession: true,
            autoRefreshToken: true,
            detectSessionInUrl: true,
            storage: window.localStorage
          }
        });

        // Get initial session
        const { data } = await this.supabase.auth.getSession();
        this.session = data.session;
        this.user = this.session ? this.session.user : null;

        // Listen for auth state changes
        this.supabase.auth.onAuthStateChange((event, session) => {
          this.session = session;
          this.user = session ? session.user : null;

          if (event === "SIGNED_OUT") {
            this.handleSignOutRedirect();
          } else if (event === "SIGNED_IN" && session) {
            this.updateUserUI();
          }
        });
      }

      this.isInitialized = true;
      return this;
    })();

    return this._initPromise;
  }

  /**
   * Returns current access token for authenticated API requests.
   */
  getAccessToken() {
    return this.session ? this.session.access_token : null;
  }

  /**
   * Check if user is authenticated.
   */
  isAuthenticated() {
    return Boolean(this.session && this.user);
  }

  /**
   * Route Guard: Protects private application pages.
   */
  async requireAuth() {
    await this.init();
    if (!this.isAuthenticated()) {
      const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `${window.CONFIG.ROUTES.LOGIN}?redirect=${returnUrl}`;
      return false;
    }
    this.updateUserUI();
    return true;
  }

  /**
   * Route Guard: Redirects already-logged-in users away from auth pages to dashboard.
   */
  async redirectIfAuthenticated() {
    await this.init();
    if (this.isAuthenticated()) {
      window.location.href = window.CONFIG.ROUTES.DASHBOARD;
      return true;
    }
    return false;
  }

  /**
   * Email & Password Sign In
   */
  async signInWithEmail(email, password) {
    await this.init();
    if (!this.supabase) {
      throw new Error("Supabase client is not configured. Please check backend settings.");
    }

    const { data, error } = await this.supabase.auth.signInWithPassword({
      email: email.trim(),
      password
    });

    if (error) {
      throw new Error(this._formatAuthError(error));
    }

    this.session = data.session;
    this.user = data.user;
    return data;
  }

  /**
   * Email & Password Sign Up
   */
  async signUpWithEmail(email, password, fullName = "") {
    await this.init();
    if (!this.supabase) {
      throw new Error("Supabase client is not configured. Please check backend settings.");
    }

    const { data, error } = await this.supabase.auth.signUp({
      email: email.trim(),
      password,
      options: {
        data: {
          full_name: fullName.trim()
        }
      }
    });

    if (error) {
      throw new Error(this._formatAuthError(error));
    }

    return data;
  }

  /**
   * Google OAuth Sign In via Supabase Auth
   */
  async signInWithGoogle() {
    await this.init();
    if (!this.supabase) {
      throw new Error("Supabase client is not configured. Please check backend settings.");
    }

    // Determine redirect destination
    const redirectUrl = `${window.location.origin}${window.CONFIG.ROUTES.DASHBOARD}`;

    const { data, error } = await this.supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: redirectUrl,
        queryParams: {
          access_type: "offline",
          prompt: "consent"
        }
      }
    });

    if (error) {
      throw new Error(this._formatAuthError(error));
    }

    return data;
  }

  /**
   * Sends password reset email
   */
  async resetPasswordForEmail(email) {
    await this.init();
    if (!this.supabase) {
      throw new Error("Supabase client is not configured.");
    }

    const resetRedirect = `${window.location.origin}${window.CONFIG.ROUTES.RESET_PASSWORD}`;

    const { data, error } = await this.supabase.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: resetRedirect
    });

    if (error) {
      throw new Error(this._formatAuthError(error));
    }

    return data;
  }

  /**
   * Updates password after user opens password reset link
   */
  async updatePassword(newPassword) {
    await this.init();
    if (!this.supabase) {
      throw new Error("Supabase client is not configured.");
    }

    const { data, error } = await this.supabase.auth.updateUser({
      password: newPassword
    });

    if (error) {
      throw new Error(this._formatAuthError(error));
    }

    return data;
  }

  /**
   * Sign Out
   */
  async signOut() {
    await this.init();
    if (this.supabase) {
      try {
        await this.supabase.auth.signOut();
      } catch (err) {
        console.warn("[DocuMind Auth] Error signing out:", err);
      }
    }
    this.session = null;
    this.user = null;
    this.handleSignOutRedirect();
  }

  handleSignOutRedirect() {
    const isAuthPage = window.location.pathname.includes("login") ||
                       window.location.pathname.includes("signup") ||
                       window.location.pathname.includes("forgot") ||
                       window.location.pathname.includes("reset");
    if (!isAuthPage) {
      window.location.href = window.CONFIG.ROUTES.LOGIN;
    }
  }

  /**
   * Populates user profile badge in the application layout
   */
  updateUserUI() {
    if (!this.user) return;

    const email = this.user.email || "";
    const meta = this.user.user_metadata || {};
    const fullName = meta.full_name || email.split("@")[0] || "User";

    // Set Name & Email
    const nameEls = document.querySelectorAll(".user-name");
    nameEls.forEach(el => el.textContent = fullName);

    const emailEls = document.querySelectorAll(".user-email");
    emailEls.forEach(el => el.textContent = email);

    // Set Avatar Initials
    const initials = fullName
      .split(" ")
      .map(part => part.charAt(0))
      .join("")
      .toUpperCase()
      .substring(0, 2) || "U";

    const avatarEls = document.querySelectorAll(".user-avatar");
    avatarEls.forEach(el => {
      if (meta.avatar_url) {
        el.innerHTML = `<img src="${meta.avatar_url}" alt="${fullName}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;" />`;
      } else {
        el.textContent = initials;
      }
    });
  }

  _formatAuthError(error) {
    if (!error) return "An unexpected error occurred.";
    const msg = error.message || String(error);
    if (msg.includes("Invalid login credentials")) {
      return "Incorrect email or password. Please verify your credentials.";
    }
    if (msg.includes("Email not confirmed")) {
      return "Please confirm your email address via the link sent to your inbox.";
    }
    if (msg.includes("User already registered")) {
      return "An account with this email already exists. Please sign in instead.";
    }
    if (msg.includes("Password should be at least")) {
      return "Password must be at least 6 characters long.";
    }
    return msg;
  }
}

// Global singleton instance
window.authManager = new AuthManager();
