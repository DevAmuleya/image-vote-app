import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : "http://localhost:8000/api";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { "Content-Type": "application/json" }
});

// Attach the session JWT to every request automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("session_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ─── Error handler ────────────────────────────────────────────────────────────

export const handleApiError = (error) => {
  console.error("API Error:", {
    response: error.response?.data,
    status: error.response?.status,
    message: error.message
  });

  if (error.response) {
    const status = error.response.status;
    const detail =
      error.response.data?.detail ||
      error.response.data?.message ||
      "An error occurred";

    switch (status) {
      case 400: return `Validation Error: ${detail}`;
      case 401: return `Unauthorised: ${detail}`;
      case 403: return `Forbidden: ${detail}`;
      case 404: return `Not Found: ${detail}`;
      case 409: return `You have already voted on this post. You are not eligible to vote again.`;
      case 500: return `Server Error: ${detail}`;
      default:  return `Error (${status}): ${detail}`;
    }
  } else if (error.request) {
    return "Network Error: Could not reach the server. Ensure the backend is running on http://localhost:8000";
  }
  return error.message ? `Request Error: ${error.message}` : "An unexpected error occurred.";
};


export const facebookLogin = async (accessToken) => {
  try {
    const res = await api.post("/auth/facebook", { access_token: accessToken });
    if (!res.data.success) throw new Error("Login failed");
    return res.data;
  } catch (error) {
    throw new Error(handleApiError(error));
  }
};

// ─── Posts ────────────────────────────────────────────────────────────────────

// Compress an image file using canvas — reduces payload before upload
const compressImage = (file, maxPx = 1920, quality = 0.92) =>
  new Promise((resolve) => {
    // GIFs can't be canvas-compressed meaningfully — pass through as-is
    if (file.type === "image/gif") return resolve(file);
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      const scale = Math.min(1, maxPx / Math.max(img.width, img.height));
      const w = Math.round(img.width * scale);
      const h = Math.round(img.height * scale);
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      canvas.getContext("2d").drawImage(img, 0, 0, w, h);
      canvas.toBlob(
        (blob) => resolve(new File([blob], file.name, { type: "image/jpeg" })),
        "image/jpeg",
        quality
      );
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
    img.src = url;
  });

export const createPost = async (files) => {
  try {
    if (!files || files.length < 3 || files.length > 5) {
      throw new Error("Must select 3-5 images");
    }

    const validTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];
    for (const file of files) {
      if (!validTypes.includes(file.type)) {
        throw new Error(`Invalid file type: ${file.name}. Allowed: JPG, PNG, GIF, WEBP`);
      }
    }

    // Compress all images in parallel before sending
    const compressed = await Promise.all(files.map((f) => compressImage(f)));

    const formData = new FormData();
    compressed.forEach((file) => formData.append("files", file));

    const res = await api.post("/posts", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 60000,
    });

    if (!res.data.success) throw new Error(res.data.error || "Failed to create post");
    return res.data;
  } catch (error) {
    throw new Error(handleApiError(error));
  }
};

// Short-lived in-memory cache for getPost — avoids re-fetching on re-renders
const _postCache = new Map(); // code -> { data, expiresAt }
const POST_CACHE_TTL = 15_000; // 15 seconds

export const getPost = async (code, { bust = false } = {}) => {
  try {
    if (!code) throw new Error("Invalid shareable code");
    const cached = _postCache.get(code);
    if (!bust && cached && Date.now() < cached.expiresAt) return cached.data;
    const res = await api.get(`/posts/${code}`);
    if (!res.data.success) throw new Error(res.data.error || "Post not found");
    _postCache.set(code, { data: res.data, expiresAt: Date.now() + POST_CACHE_TTL });
    return res.data;
  } catch (error) {
    throw new Error(handleApiError(error));
  }
};


export const castVote = async (postId, photoId, comment = null) => {
  try {
    if (!postId || !photoId) throw new Error("post_id and photo_id are required");
    const res = await api.post(`/posts/${postId}/vote`, {
      photo_id: photoId,
      comment: comment ? comment.trim().slice(0, 1000) : null
    });
    if (!res.data.success) throw new Error(res.data.error || "Vote failed");
    return res.data;
  } catch (error) {
    throw new Error(handleApiError(error));
  }
};


export const getPostResults = async (postId) => {
  try {
    if (!postId) throw new Error("post_id is required");
    const res = await api.get(`/posts/${postId}/results`);
    if (!res.data.success) throw new Error(res.data.error || "Failed to fetch results");
    return res.data;
  } catch (error) {
    throw new Error(handleApiError(error));
  }
};
