import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import PhotoGallery from "../components/PhotoGallery";
import { useAuth } from "../contexts/AuthContext";

export default function SharedView() {
  const { code } = useParams();
  const { user, login, sdkReady, loading } = useAuth();

  // Track whether we've already fired the auto-login prompt once.
  // Without this guard it would re-trigger every time sdkReady toggles.
  const didPrompt = useRef(false);

  // When the FB SDK becomes ready and the user is not signed in,
  // immediately open the Facebook sign-in dialog automatically.
  useEffect(() => {
    if (!loading && !user && sdkReady && !didPrompt.current) {
      didPrompt.current = true;
      login();
    }
  }, [loading, user, sdkReady, login]);

  // ── Auth gate ─────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 via-blue-50 to-purple-50">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-500 text-sm">Opening Facebook sign-in…</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-blue-50 to-purple-50 flex flex-col items-center justify-center px-4">

        {/* Branded card */}
        <div className="bg-white rounded-3xl shadow-xl border border-blue-100 w-full max-w-md p-8 sm:p-10 flex flex-col items-center gap-6 text-center">

          {/* Lock icon */}
          <div className="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center">
            <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 tracking-tight">
              You've been invited to vote
            </h1>
            <p className="text-gray-500 text-sm sm:text-base leading-relaxed">
              A Facebook sign-in window should have opened automatically. If it didn't appear, tap the button below.
            </p>
          </div>

          {/* Steps */}
          <div className="w-full grid grid-cols-3 gap-3 text-center">
            {[
              { n: "1", icon: "🔑", label: "Sign in" },
              { n: "2", icon: "📸", label: "Browse photos" },
              { n: "3", icon: "✅", label: "Cast your vote" },
            ].map(({ n, icon, label }) => (
              <div key={n} className="flex flex-col items-center gap-1">
                <span className="w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">{n}</span>
                <span className="text-xl">{icon}</span>
                <span className="text-xs font-medium text-gray-700">{label}</span>
              </div>
            ))}
          </div>

          {/* Facebook login button */}
          <button
            onClick={login}
            disabled={!sdkReady}
            className="w-full flex items-center justify-center gap-3 px-6 py-3.5 bg-[#1877F2] hover:bg-[#166FE5] disabled:bg-gray-300 text-white font-semibold rounded-xl shadow-md transition text-base"
          >
            <svg className="w-5 h-5 fill-white flex-shrink-0" viewBox="0 0 24 24">
              <path d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047V9.41c0-3.025 1.792-4.697 4.533-4.697 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.93-1.956 1.886v2.286h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.1 24 12.073z" />
            </svg>
            {sdkReady ? "Sign in with Facebook" : "Loading…"}
          </button>

          <p className="text-xs text-gray-400">
            We only use your public profile to identify your vote. No posting on your behalf.
          </p>
        </div>

        <p className="mt-6 text-xs text-gray-400">
          <Link to="/" className="underline hover:text-blue-500 transition">Create your own photo challenge →</Link>
        </p>
      </div>
    );
  }

  // ── Authenticated view ────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-blue-50 to-purple-50">

      {/* ── Top nav ──────────────────────────────────────────────────────── */}
      <div className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-blue-600 hover:text-blue-700 text-sm font-medium transition">
            <span>←</span>
            <span>Create a post</span>
          </Link>
          <div className="flex items-center gap-2">
            {user.picture_url && (
              <img src={user.picture_url} alt={user.name} className="w-8 h-8 rounded-full border-2 border-blue-200" />
            )}
            <span className="text-sm font-medium text-gray-700 hidden sm:block">{user.name}</span>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">

        {/* ── Hero ─────────────────────────────────────────────────────── */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 tracking-tight">
            🗳️ Photo Challenge
          </h1>
          <p className="text-gray-500 text-base sm:text-lg">
            Someone shared their photos — pick your favourite and cast your vote!
          </p>
        </div>

        {/* ── Active voter banner ───────────────────────────────────────── */}
        <div className="bg-blue-600 rounded-2xl shadow px-5 py-4 flex items-center gap-3 text-white">
          <span className="text-2xl">👆</span>
          <div>
            <p className="font-semibold text-sm">Select the photo you like most, then hit <strong>Submit Vote</strong>.</p>
            <p className="text-blue-200 text-xs mt-0.5">You can change your selection as many times as you like before submitting.</p>
          </div>
        </div>

        {/* ── Gallery card ─────────────────────────────────────────────── */}
        <div className="bg-white rounded-2xl shadow-md border border-gray-100 p-5 sm:p-8">
          <PhotoGallery postCode={code} />
        </div>

      </div>
    </div>
  );
}

