/**
 * DOCUMIND BRANDED LOADING EXPERIENCE
 * Displays the clean DocuMind logo and "DocuMind Document Intelligence"
 * and smoothly enters into the dashboard after loading.
 */

(function () {
  const path = window.location.pathname;
  const isAuthPage = path.includes("login") ||
                     path.includes("signup") ||
                     path.includes("forgot") ||
                     path.includes("reset");

  // Auth pages handle their own minimal loading states
  if (isAuthPage) return;

  const isInternalNav = sessionStorage.getItem("documind_internal_nav") === "true";
  sessionStorage.removeItem("documind_internal_nav");

  // Track user clicks on internal links for fast page-to-page transitions
  document.addEventListener("click", (e) => {
    const link = e.target.closest("a");
    if (link && link.href && link.origin === window.location.origin) {
      const dest = link.pathname;
      if (!dest.includes("login") && !dest.includes("signup") && !dest.includes("forgot")) {
        sessionStorage.setItem("documind_internal_nav", "true");
      }
    }
  }, true);

  // If this is an internal link transition, skip full boot screen
  if (isInternalNav) {
    window.dismissAppLoader = function () {};
    return;
  }

  // Inject critical loader styles immediately into head so it renders with 0ms latency
  const styleEl = document.createElement("style");
  styleEl.textContent = `
    body.app-loading .app-container {
      opacity: 0 !important;
      pointer-events: none !important;
    }
    body.app-ready .app-container {
      opacity: 1 !important;
      transition: opacity 0.35s ease-out !important;
    }
    .documind-initial-loader {
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      right: 0 !important;
      bottom: 0 !important;
      width: 100vw !important;
      height: 100vh !important;
      z-index: 2147483647 !important;
      background: #ffffff !important;
      display: flex !important;
      flex-direction: column !important;
      align-items: center !important;
      justify-content: center !important;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
      transition: opacity 0.45s cubic-bezier(0.16, 1, 0.3, 1), transform 0.45s cubic-bezier(0.16, 1, 0.3, 1) !important;
      will-change: opacity, transform !important;
    }
    .documind-initial-loader.fade-out {
      opacity: 0 !important;
      transform: scale(1.03) !important;
      pointer-events: none !important;
    }
    .loader-brand-wrapper {
      display: flex !important;
      flex-direction: column !important;
      align-items: center !important;
      justify-content: center !important;
      text-align: center !important;
      user-select: none !important;
    }
    .loader-logo-ring {
      position: relative !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      margin-bottom: 20px !important;
    }
    .loader-brand-icon-svg {
      width: 72px !important;
      height: 72px !important;
      filter: drop-shadow(0 10px 25px rgba(37, 99, 235, 0.35)) !important;
      animation: logoBreathAnim 2.2s ease-in-out infinite !important;
    }
    @keyframes logoBreathAnim {
      0%, 100% {
        transform: scale(1);
        filter: drop-shadow(0 10px 22px rgba(37, 99, 235, 0.3));
      }
      50% {
        transform: scale(1.05);
        filter: drop-shadow(0 14px 32px rgba(37, 99, 235, 0.48));
      }
    }
    .loader-brand-title {
      font-size: 34px !important;
      font-weight: 700 !important;
      color: #0f172a !important;
      letter-spacing: -0.03em !important;
      line-height: 1.1 !important;
      margin-bottom: 6px !important;
    }
    .loader-brand-subtitle {
      font-size: 13px !important;
      font-weight: 600 !important;
      color: #64748b !important;
      letter-spacing: 0.14em !important;
      text-transform: uppercase !important;
      line-height: 1.2 !important;
      margin-bottom: 28px !important;
    }
    .loader-progress-track {
      width: 150px !important;
      height: 3.5px !important;
      background: #f1f5f9 !important;
      border-radius: 9999px !important;
      overflow: hidden !important;
      position: relative !important;
    }
    .loader-progress-fill {
      height: 100% !important;
      width: 25% !important;
      background: linear-gradient(90deg, #2563eb, #38bdf8) !important;
      border-radius: 9999px !important;
      box-shadow: 0 0 14px rgba(37, 99, 235, 0.7) !important;
      transition: width 0.9s cubic-bezier(0.16, 1, 0.3, 1) !important;
      animation: progressGlowAnim 1.6s ease-in-out infinite alternate !important;
    }
    @keyframes progressGlowAnim {
      0% { opacity: 0.75; }
      100% { opacity: 1; }
    }
  `;
  document.head.appendChild(styleEl);

  // Ensure body/html has app-loading state immediately
  document.documentElement.classList.add("app-loading");
  if (document.body) {
    document.body.classList.add("app-loading");
  } else {
    document.addEventListener("DOMContentLoaded", () => {
      document.body.classList.add("app-loading");
    });
  }

  // Create clean loading element: JUST Logo + DocuMind Document Intelligence + sleek progress bar
  const loaderEl = document.createElement("div");
  loaderEl.id = "documind-app-loader";
  loaderEl.className = "documind-initial-loader";

  loaderEl.innerHTML = `
    <div class="loader-brand-wrapper">
      <div class="loader-logo-ring">
        <svg class="loader-brand-icon-svg" viewBox="0 0 54 54" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="54" height="54" rx="16" fill="url(#brandGradLoader)"/>
          <path d="M17 14H27C33.0751 14 38 18.9249 38 25C38 31.0751 33.0751 36 27 36H17V14Z" stroke="#ffffff" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="27" cy="25" r="3.8" fill="#ffffff"/>
          <circle cx="38" cy="25" r="2.8" fill="#60a5fa"/>
          <circle cx="17" cy="14" r="2.8" fill="#93c5fd"/>
          <circle cx="17" cy="36" r="2.8" fill="#93c5fd"/>
          <defs>
            <linearGradient id="brandGradLoader" x1="0" y1="0" x2="54" y2="54" gradientUnits="userSpaceOnUse">
              <stop stop-color="#2563eb"/>
              <stop offset="1" stop-color="#1d4ed8"/>
            </linearGradient>
          </defs>
        </svg>
      </div>
      <div class="loader-brand-title">DocuMind</div>
      <div class="loader-brand-subtitle">Document Intelligence</div>
      <div class="loader-progress-track">
        <div class="loader-progress-fill" id="loader-progress-fill"></div>
      </div>
    </div>
  `;

  // Attach loader to documentElement (<html>) immediately, and body when available.
  // NEVER attach to <head> because <head> is display:none by browser default!
  function attachLoader() {
    if (document.body) {
      if (loaderEl.parentNode !== document.body) {
        document.body.appendChild(loaderEl);
      }
    } else if (document.documentElement) {
      if (loaderEl.parentNode !== document.documentElement) {
        document.documentElement.appendChild(loaderEl);
      }
    }
  }

  attachLoader();
  document.addEventListener("DOMContentLoaded", attachLoader);

  window.dismissAppLoader = function () {
    if (!loaderEl) return;
    document.documentElement.classList.remove("app-loading");
    if (document.body) {
      document.body.classList.remove("app-loading");
      document.body.classList.add("app-ready");
    }
    loaderEl.classList.add("fade-out");
    setTimeout(() => {
      try { loaderEl.remove(); } catch (_) {}
    }, 450);
  };

  // Animate progress smoothly and enter dashboard
  const startTime = Date.now();
  const MIN_DISPLAY_MS = 1100; // Smooth, deliberate ~1.1s showcase

  // Start progress fill animation
  setTimeout(() => {
    const fill = document.getElementById("loader-progress-fill");
    if (fill) fill.style.width = "75%";
  }, 100);

  document.addEventListener("DOMContentLoaded", async () => {
    try {
      if (window.authManager) {
        await window.authManager.init();
        if (window.authManager.isAuthenticated()) {
          window.authManager.updateUserUI();
        }
      }

      // Fill to 100%
      const fill = document.getElementById("loader-progress-fill");
      if (fill) fill.style.width = "100%";

      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, MIN_DISPLAY_MS - elapsed);

      setTimeout(() => {
        window.dismissAppLoader();
      }, remaining);
    } catch (err) {
      console.warn("[DocuMind Loader] Note:", err);
      setTimeout(window.dismissAppLoader, 400);
    }
  });

  // Safety maximum timeout: never hold user more than 3 seconds
  setTimeout(() => {
    if (document.getElementById("documind-app-loader")) {
      window.dismissAppLoader();
    }
  }, 3000);
})();
