import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { facebookLogin } from "../api";

const AuthContext = createContext(null);

const FB_APP_ID = import.meta.env.VITE_FB_APP_ID;
const FB_SDK_VERSION = "v21.0";


function loadFacebookSDK() {
  return new Promise((resolve) => {
    if (window.FB) {
      resolve(window.FB);
      return;
    }

    window.fbAsyncInit = function () {
      window.FB.init({
        appId: FB_APP_ID,
        cookie: true,
        xfbml: false,
        version: FB_SDK_VERSION,
      });
      resolve(window.FB);
    };

    if (!document.getElementById("facebook-sdk")) {
      const script = document.createElement("script");
      script.id = "facebook-sdk";
      script.src = "https://connect.facebook.net/en_US/sdk.js";
      script.async = true;
      script.defer = true;
      script.crossOrigin = "anonymous";
      document.head.appendChild(script);
    }
  });
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem("fb_user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [accessToken, setAccessToken] = useState(
    () => localStorage.getItem("session_token") || null
  );
  const [sdkReady, setSdkReady] = useState(false);
  const [loading, setLoading] = useState(true);

  // Load the SDK and check existing login state on mount
  useEffect(() => {
    loadFacebookSDK().then((FB) => {
      setSdkReady(true);

      // FB.getLoginStatus is blocked on HTTP (only works on HTTPS).
      // On HTTP (local dev), skip it and restore from localStorage instead.
      if (window.location.protocol === "https:") {
        FB.getLoginStatus((response) => {
          if (
            response.status === "connected" &&
            response.authResponse?.accessToken
          ) {
            const token = response.authResponse.accessToken;
            handleTokenReceived(token).finally(() => setLoading(false));
          } else {
            // Check if we already have a valid session JWT
            if (!accessToken) {
              setLoading(false);
            } else {
              // Session JWT still in localStorage — user is already logged in
              setLoading(false);
            }
          }
        });
      } else {
        // HTTP — restore session from localStorage session token directly
        if (accessToken) {
          // Session JWT present — no need to call FB, just mark loaded
          setLoading(false);
        } else {
          setLoading(false);
        }
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTokenReceived = useCallback(async (token) => {
    try {
      const data = await facebookLogin(token);
      setUser(data.user);
      // Store the session JWT (not the FB token) — all future requests use this
      setAccessToken(data.session_token);
      localStorage.setItem("session_token", data.session_token);
      localStorage.setItem("fb_user", JSON.stringify(data.user));
    } catch {
      // Token invalid — clear state
      clearAuth();
    }
  }, []);

  const login = useCallback(() => {
    if (!sdkReady) return;

    window.FB.login(
      (response) => {
        if (response.authResponse?.accessToken) {
          handleTokenReceived(response.authResponse.accessToken);
        }
      },
      { scope: "public_profile" }
    );
  }, [sdkReady, handleTokenReceived]);


  const loginWithToken = useCallback(
    (token) => handleTokenReceived(token),
    [handleTokenReceived]
  );

  const clearAuth = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    localStorage.removeItem("session_token");
    localStorage.removeItem("fb_user");
  }, []);

  const logout = useCallback(() => {
    // Clear local state immediately — don't wait on FB SDK (fails on HTTP)
    clearAuth();
    // Best-effort FB session revoke (works on HTTPS / production)
    try {
      if (window.FB && sdkReady) {
        window.FB.logout(() => {});
      }
    } catch (_) {}
  }, [sdkReady, clearAuth]);

  return (
    <AuthContext.Provider value={{ user, accessToken, sdkReady, loading, login, loginWithToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
