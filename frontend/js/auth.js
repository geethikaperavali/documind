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
    this._authListenerRegistered = false;

    // Immediately hydrate user badge from sessionStorage cache if available to prevent UI flash
    try {
      const cached = sessionStorage.getItem("documind_cached_user");
      if (cached) {
        const cachedUser = JSON.parse(cached);
        this._renderUserElements(cachedUser.full_name, cachedUser.email, cachedUser.avatar_url);
      }
    } catch (_) {}
  }

  /**
   * Initializes Supabase Auth client by reading cached credentials
   * or querying backend configuration only if credentials are not yet cached.
   */
  async init() {
    if (this._initPromise) return this._initPromise;

    this._initPromise = (async () => {
      // 1. Check if Supabase URL & Anon Key are already available locally
      let supabaseUrl = window.CONFIG.SUPABASE_URL || localStorage.getItem("documind_supabase_url");
      let supabaseAnonKey = window.CONFIG.SUPABASE_ANON_KEY || localStorage.getItem("documind_supabase_anon_key");

      // Only make a network fetch if credentials are missing
      if (!supabaseUrl || !supabaseAnonKey) {
        try {
          const res = await fetch(`${window.CONFIG.API_BASE_URL}/auth/config`);
          if (res.ok) {
            const cfg = await res.json();
            if (cfg.supabase_url && cfg.supabase_anon_key) {
              supabaseUrl = cfg.supabase_url;
              supabaseAnonKey = cfg.supabase_anon_key;
              window.CONFIG.SUPABASE_URL = supabaseUrl;
              window.CONFIG.SUPABASE_ANON_KEY = supabaseAnonKey;
              localStorage.setItem("documind_supabase_url", supabaseUrl);
              localStorage.setItem("documind_supabase_anon_key", supabaseAnonKey);
            }
          }
        } catch (err) {
          console.warn("[DocuMind Auth] Could not reach /api/auth/config, using existing config:", err);
        }
      } else {
        window.CONFIG.SUPABASE_URL = supabaseUrl;
        window.CONFIG.SUPABASE_ANON_KEY = supabaseAnonKey;
      }

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

        if (this.user) {
          this.updateUserUI();
        }

        // If returning from OAuth redirect, give Supabase a moment to parse hash/code
        const hasOAuthParams = window.location.hash.includes("access_token") || 
                               window.location.search.includes("code=");
        if (!this.session && hasOAuthParams) {
          await new Promise((resolve) => {
            const timeout = setTimeout(resolve, 3000);
            const { data: listener } = this.supabase.auth.onAuthStateChange((event, session) => {
              if (session) {
                this.session = session;
                this.user = session.user;
                clearTimeout(timeout);
                if (listener && listener.subscription) listener.subscription.unsubscribe();
                if (window.location.hash) {
                  window.history.replaceState(null, document.title, window.location.pathname + window.location.search);
                }
                this.updateUserUI();
                resolve();
              }
            });
          });
        }

        // Listen for auth state changes once
        if (!this._authListenerRegistered) {
          this._authListenerRegistered = true;
          this.supabase.auth.onAuthStateChange((event, session) => {
            this.session = session;
            this.user = session ? session.user : null;

            if (event === "SIGNED_OUT") {
              sessionStorage.removeItem("documind_cached_user");
              this.handleSignOutRedirect();
            } else if (event === "SIGNED_IN" && session) {
              this.updateUserUI();
            }
          });
        }
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
    this.setupResponsiveNav();
    return true;
  }

  /**
   * Sets up responsive mobile drawer toggle and backdrop across workspaces
   */
  setupResponsiveNav() {
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;

    let backdrop = document.querySelector(".sidebar-backdrop");
    if (!backdrop) {
      backdrop = document.createElement("div");
      backdrop.className = "sidebar-backdrop";
      document.body.appendChild(backdrop);
    }

    const header = document.querySelector(".top-header, .topbar");
    if (header) {
      let toggleBtn = header.querySelector(".btn-sidebar-toggle");
      if (!toggleBtn) {
        toggleBtn = document.createElement("button");
        toggleBtn.type = "button";
        toggleBtn.className = "btn-sidebar-toggle";
        toggleBtn.setAttribute("aria-label", "Toggle navigation");
        toggleBtn.innerHTML = `
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        `;

        const titleBlock = header.querySelector(".page-title-block, .topbar-left");
        if (titleBlock) {
          let leftGroup = header.querySelector(".header-left-group");
          if (!leftGroup) {
            leftGroup = document.createElement("div");
            leftGroup.className = "header-left-group";
            titleBlock.parentNode.insertBefore(leftGroup, titleBlock);
            leftGroup.appendChild(toggleBtn);
            leftGroup.appendChild(titleBlock);
          } else {
            leftGroup.insertBefore(toggleBtn, leftGroup.firstChild);
          }
        } else {
          header.insertBefore(toggleBtn, header.firstChild);
        }
      }

      toggleBtn.onclick = () => {
        const isOpen = sidebar.classList.toggle("mobile-open");
        backdrop.classList.toggle("active", isOpen);
      };
    }

    backdrop.onclick = () => {
      sidebar.classList.remove("mobile-open");
      backdrop.classList.remove("active");
    };

    sidebar.querySelectorAll(".nav-item").forEach(item => {
      item.onclick = () => {
        sidebar.classList.remove("mobile-open");
        backdrop.classList.remove("active");
      };
    });
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
    const avatarUrl = meta.avatar_url || "";

    // Cache profile in sessionStorage for zero-latency hydration across page navigation
    try {
      sessionStorage.setItem("documind_cached_user", JSON.stringify({
        email,
        full_name: fullName,
        avatar_url: avatarUrl
      }));
    } catch (_) {}

    this._renderUserElements(fullName, email, avatarUrl);
  }

  _renderUserElements(fullName, email, avatarUrl) {
    if (!fullName && !email) return;

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
      if (avatarUrl) {
        el.innerHTML = `<img src="${avatarUrl}" alt="${fullName}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;" />`;
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
