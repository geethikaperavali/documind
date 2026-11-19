/**
 * DOCUMIND SETTINGS & USER PROFILE CONTROLLER
 */

document.addEventListener("DOMContentLoaded", async () => {
  const authenticated = await window.authManager.requireAuth();
  if (!authenticated) return;

  setupProfileForm();
  setupApiSettingsForm();
  setupSignOutButton();

  await loadUserProfile();
  await checkSystemStatus();
});

async function loadUserProfile() {
  try {
    const res = await window.apiClient.get("/profile");
    const profile = res.profile || {};

    const emailInput = document.getElementById("profile-email");
    const nameInput = document.getElementById("profile-name");
    const avatarInput = document.getElementById("profile-avatar");

    if (emailInput) emailInput.value = profile.email || window.authManager.user?.email || "";
    if (nameInput) nameInput.value = profile.full_name || "";
    if (avatarInput) avatarInput.value = profile.avatar_url || "";

  } catch (err) {
    console.error("[Settings] Error loading profile:", err);
  }
}

function setupProfileForm() {
  const form = document.getElementById("profile-form");
  const saveBtn = document.getElementById("btn-save-profile");
  const alertEl = document.getElementById("profile-alert");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.textContent = "Saving...";
    }
    if (alertEl) alertEl.style.display = "none";

    const fullName = document.getElementById("profile-name").value.trim();
    const avatarUrl = document.getElementById("profile-avatar").value.trim();

    try {
      await window.apiClient.put("/profile", {
        full_name: fullName,
        avatar_url: avatarUrl
      });

      // Update local auth metadata
      if (window.authManager.user) {
        window.authManager.user.user_metadata = {
          ...window.authManager.user.user_metadata,
          full_name: fullName,
          avatar_url: avatarUrl
        };
        window.authManager.updateUserUI();
      }

      showAlert(alertEl, "Profile updated successfully!", "success");
    } catch (err) {
      showAlert(alertEl, "Failed to update profile: " + err.message, "error");
    } finally {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.textContent = "Save Changes";
      }
    }
  });
}

function setupApiSettingsForm() {
  const form = document.getElementById("api-settings-form");
  const geminiInput = document.getElementById("gemini-api-key");
  const alertEl = document.getElementById("api-alert");

  // Load cached custom key
  if (geminiInput) {
    geminiInput.value = localStorage.getItem("documind_gemini_key") || "";
  }

  if (!form) return;

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const val = geminiInput.value.trim();
    if (val) {
      localStorage.setItem("documind_gemini_key", val);
      showAlert(alertEl, "Gemini API key saved to local browser storage.", "success");
    } else {
      localStorage.removeItem("documind_gemini_key");
      showAlert(alertEl, "Using server-side GEMINI_API_KEY from environment.", "success");
    }
  });
}

async function checkSystemStatus() {
  const supabaseStatusEl = document.getElementById("status-supabase");
  const geminiStatusEl = document.getElementById("status-gemini");

  try {
    const res = await window.apiClient.get("/health");

    if (supabaseStatusEl) {
      if (res.supabase_configured) {
        supabaseStatusEl.innerHTML = `<span class="badge badge-ready">Connected</span>`;
      } else {
        supabaseStatusEl.innerHTML = `<span class="badge badge-failed">Not Configured</span>`;
      }
    }

    if (geminiStatusEl) {
      const hasLocalKey = Boolean(localStorage.getItem("documind_gemini_key"));
      if (res.gemini_configured || hasLocalKey) {
        geminiStatusEl.innerHTML = `<span class="badge badge-ready">Connected (${res.gemini_model || "gemini-2.0-flash"})</span>`;
      } else {
        geminiStatusEl.innerHTML = `<span class="badge badge-warning">Key Required</span>`;
      }
    }

  } catch (err) {
    console.error("[Settings] Health check failed:", err);
  }
}

function setupSignOutButton() {
  const btn = document.getElementById("btn-signout-main");
  if (btn) {
    btn.addEventListener("click", () => {
      if (confirm("Are you sure you want to sign out?")) {
        window.authManager.signOut();
      }
    });
  }
}

function showAlert(el, msg, type) {
  if (!el) return;
  el.textContent = msg;
  el.className = `alert ${type === "success" ? "alert-success" : "alert-error"} show`;
  setTimeout(() => {
    el.classList.remove("show");
  }, 4000);
}
