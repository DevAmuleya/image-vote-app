import { useState } from "react";
import { useAuth } from "../contexts/AuthContext";

const IS_LOCALHOST = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

export default function LoginPage() {
  const { login, loginWithToken, sdkReady, loading } = useAuth();
  const [showDevFallback, setShowDevFallback] = useState(false);
  const [devToken, setDevToken] = useState("");
  const [devLoading, setDevLoading] = useState(false);
  const [devError, setDevError] = useState("");

  const handleDevLogin = async () => {
    const t = devToken.trim();
    if (!t) return;
    setDevLoading(true);
    setDevError("");
    try {
      await loginWithToken(t);
    } catch {
      setDevError("Token rejected — make sure it is a valid user access token.");
    } finally {
      setDevLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-indigo-800 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-2xl p-10 max-w-md w-full text-center">
        {/* App identity */}
        <div className="mb-8">
          <p className="text-5xl mb-4">📸</p>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Image Vote</h1>
          <p className="text-gray-500 text-sm leading-relaxed">
            Upload a set of photos, share a unique link, and let your friends
            vote for their favourite.
          </p>
        </div>

        {/* How it works */}
        <div className="grid grid-cols-3 gap-4 mb-8 text-center">
          {[
            ["📤", "Upload", "3-5 photos"],
            ["🔗", "Share", "Unique link"],
            ["🗳️", "Vote", "One pick each"],
          ].map(([icon, title, desc]) => (
            <div key={title} className="bg-gray-50 rounded-lg p-3">
              <p className="text-2xl">{icon}</p>
              <p className="font-semibold text-gray-700 text-sm">{title}</p>
              <p className="text-xs text-gray-400">{desc}</p>
            </div>
          ))}
        </div>

        {/* ── Facebook Login button (always shown) ──────────────────────── */}
        <button
          onClick={login}
          disabled={!sdkReady || loading}
          className={`w-full flex items-center justify-center gap-3 py-3 px-6 rounded-lg font-semibold text-white transition ${
            sdkReady && !loading
              ? "bg-[#1877F2] hover:bg-[#166FE5] shadow-lg hover:shadow-xl"
              : "bg-gray-300 cursor-not-allowed"
          }`}
        >
          <svg className="w-5 h-5 fill-white" viewBox="0 0 24 24">
            <path d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047V9.41c0-3.025 1.792-4.697 4.533-4.697 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.93-1.956 1.886v2.286h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.1 24 12.073z"/>
          </svg>
          {loading ? "Loading..." : !sdkReady ? "Initialising..." : "Continue with Facebook"}
        </button>

        <p className="text-xs text-gray-400 mt-4">
          By signing in you agree to our terms. We only access your public profile.
        </p>

        {/* ── Dev fallback (localhost only, hidden by default) ────────────── */}
        {IS_LOCALHOST && (
          <div className="mt-6">
            <button
              onClick={() => setShowDevFallback(v => !v)}
              className="text-xs text-gray-400 underline hover:text-gray-600"
            >
              {showDevFallback ? "Hide" : "Having trouble? Use a dev token instead"}
            </button>

            {showDevFallback && (
              <div className="mt-3 space-y-2 text-left">
                <textarea
                  value={devToken}
                  onChange={(e) => setDevToken(e.target.value)}
                  placeholder="Paste a Facebook user access token from Graph API Explorer…"
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs font-mono resize-none focus:outline-none focus:border-blue-400"
                />
                {devError && <p className="text-red-600 text-xs">{devError}</p>}
                <button
                  onClick={handleDevLogin}
                  disabled={devLoading || !devToken.trim()}
                  className={`w-full py-2.5 rounded-lg font-semibold text-sm text-white transition ${
                    devLoading || !devToken.trim()
                      ? "bg-gray-300 cursor-not-allowed"
                      : "bg-gray-700 hover:bg-gray-800"
                  }`}
                >
                  {devLoading ? "Verifying…" : "Sign in with token"}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

