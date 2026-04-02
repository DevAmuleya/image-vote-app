import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import LoginPage from "./pages/LoginPage";
import Home from "./pages/Home";
import SharedView from "./pages/SharedView";
import PostCreated from "./pages/PostCreated";

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-500 text-lg">Loading...</p>
      </div>
    );
  }

  // Shared links are always accessible without login
  // The home (upload) page requires authentication
  return (
    <Routes>
      <Route path="/share/:code" element={<SharedView />} />
      <Route path="/post-created" element={user ? <PostCreated /> : <LoginPage />} />
      <Route path="/" element={user ? <Home /> : <LoginPage />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}

export default App;
