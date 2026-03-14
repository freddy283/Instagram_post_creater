const API = "http://127.0.0.1:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("aureus_token");
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

export function clearAuth() {
  localStorage.removeItem("aureus_token");
  localStorage.removeItem("aureus_refresh");
}

/** Called on any 401 — clears session and redirects to login */
function handleUnauthorized() {
  clearAuth();
  if (typeof window !== "undefined") {
    window.location.replace("/auth/login");
  }
}

async function req(method: string, path: string, body?: any, auth = true) {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth) {
    const tok = getToken();
    if (!tok) {
      handleUnauthorized();
      throw new Error("Not authenticated");
    }
    headers["Authorization"] = `Bearer ${tok}`;
  }
  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  // 401: token missing, expired or revoked — auto logout
  if (res.status === 401) {
    handleUnauthorized();
    throw new Error("Session expired. Please log in again.");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.message || `HTTP ${res.status}`);
  }
  return res.json();
}

// Auth
export const authApi = {
  register: (d: any) => req("POST", "/api/auth/register", d, false),
  login: async (email: string, password: string) => {
    const res = await fetch(`${API}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Invalid credentials");
    }
    const data = await res.json();
    localStorage.setItem("aureus_token", data.access_token);
    if (data.refresh_token) localStorage.setItem("aureus_refresh", data.refresh_token);
    return data;
  },
  logout: () => {
    clearAuth();
    window.location.href = "/";
  },
};

export const userApi = {
  me: () => req("GET", "/api/user/me"),
  update: (d: any) => req("PATCH", "/api/user/me", d),
  delete: () => req("DELETE", "/api/user/me"),
};

export const videoApi = {
  generate: () => req("POST", "/api/video/generate"),
  status: () => req("GET", "/api/video/status"),
  downloadUrl: () => `${API}/api/video/download?token=${getToken()}`,
  streamUrl: () => `${API}/api/video/stream`,
  postStreamUrl: (postId: string) => `${API}/api/video/post/${postId}/stream`,
  acknowledgePost: (postId: string) => req("POST", `/api/video/post/${postId}/acknowledge`),
};

export const postsApi = {
  list: (skip = 0, limit = 20) => req("GET", `/api/posts?skip=${skip}&limit=${limit}`),
  preview: () => req("GET", "/api/posts/preview"),
};

export const scheduleApi = {
  get: () => req("GET", "/api/schedule"),
  upsert: (d: any) => req("POST", "/api/schedule", d),
  pause: () => req("POST", "/api/schedule/pause"),
  resume: () => req("POST", "/api/schedule/resume"),
  skipNext: () => req("POST", "/api/schedule/skip-next"),
};

export const instagramApi = {
  status: () => req("GET", "/api/instagram/status"),
  authUrl: () => req("GET", "/api/instagram/auth-url"),
  disconnect: () => req("DELETE", "/api/instagram/disconnect"),
};
