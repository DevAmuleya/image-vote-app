import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function PostCreated() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const code        = sessionStorage.getItem("last_share_code") || "";
  const photosCount = sessionStorage.getItem("last_photos_count") || "";
  const shareUrl    = code ? `${window.location.origin}/share/${code}` : "";

  const apiBase  = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const ogUrl    = code ? `${apiBase}/api/posts/${code}/og` : "";

  const defaultMessage = `Hey! 👋 I just uploaded some photos and need your vote 🗳️\n\nClick the link below, pick your favourite photo, and submit your vote — it only takes a second!\n\n${shareUrl}`;

  const [message, setMessage] = useState(defaultMessage);
  const [copied, setCopied] = useState(false);

  const copyLink = () => {
    navigator.clipboard.writeText(message).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const shareToFacebook = () => {
    const fbShareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(ogUrl)}`;
    window.open(fbShareUrl, "_blank", "width=600,height=400,noopener,noreferrer");
  };

  const createAnother = () => {
    navigate("/");
  };

  if (!code) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-sm w-full text-center space-y-4">
          <p className="text-gray-600">No post found. Go back and create one.</p>
          <Link to="/" className="block px-5 py-2.5 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition">
            ← Back to Home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">

      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-blue-600">📸 Image Vote</h1>
          {user && (
            <div className="flex items-center gap-3">
              {user.picture_url && (
                <img src={user.picture_url} alt={user.name} className="w-9 h-9 rounded-full border-2 border-blue-200" />
              )}
              <span className="text-sm font-medium text-gray-700 hidden sm:block">{user.name}</span>
              <button
                onClick={logout}
                className="text-sm text-gray-500 hover:text-red-600 transition px-2 py-1 rounded border border-gray-200 hover:border-red-300"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-lg mx-auto space-y-6">

          {/* Success card */}
          <div className="bg-white rounded-2xl shadow-lg p-8 space-y-5">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center text-2xl flex-shrink-0">
                ✅
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-800">Post created!</h2>
                {photosCount && (
                  <p className="text-sm text-gray-500">{photosCount} photos uploaded successfully.</p>
                )}
              </div>
            </div>

            {/* Share message */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-gray-600">Share message</p>
                <span className="text-xs text-gray-400">Editable — personalise before copying</span>
              </div>
              <textarea
                value={message}
                onChange={e => setMessage(e.target.value)}
                rows={6}
                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-800 resize-none focus:outline-none focus:ring-2 focus:ring-blue-300 leading-relaxed"
              />
              <button
                onClick={copyLink}
                className={`w-full py-2.5 rounded-xl text-sm font-semibold transition ${
                  copied
                    ? "bg-green-500 text-white"
                    : "bg-blue-600 hover:bg-blue-700 text-white shadow"
                }`}
              >
                {copied ? "✓ Copied to clipboard!" : "Copy message & link"}
              </button>
              <p className="text-xs text-gray-400 text-center">
                Paste this anywhere — WhatsApp, Instagram DM, SMS, email, etc.
              </p>
            </div>

            {/* Action buttons */}
            <div className="flex gap-3 pt-1">
              <button
                onClick={shareToFacebook}
                className="flex-1 py-3 bg-[#1877F2] hover:bg-[#1565d8] text-white text-sm font-semibold rounded-lg text-center transition shadow"
              >
                Share to Facebook
              </button>
              <Link
                to={`/share/${code}`}
                className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg text-center transition shadow"
              >
                View post →
              </Link>
              <button
                onClick={createAnother}
                className="flex-1 py-3 bg-white border border-gray-300 hover:border-blue-400 text-gray-700 hover:text-blue-600 text-sm font-semibold rounded-lg transition"
              >
                + Create another
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
