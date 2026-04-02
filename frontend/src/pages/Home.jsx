import { useNavigate } from "react-router-dom";
import PhotoUpload from "../components/PhotoUpload";
import { useAuth } from "../contexts/AuthContext";

export default function Home() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleUploadComplete = (shareCode, _postId, photosCount) => {
    sessionStorage.setItem("last_share_code", shareCode);
    if (photosCount) sessionStorage.setItem("last_photos_count", photosCount);
    navigate("/post-created");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-blue-600">📸 Image Vote</h1>

          {/* User menu */}
          <div className="flex items-center gap-3">
            {user.picture_url && (
              <img
                src={user.picture_url}
                alt={user.name}
                className="w-9 h-9 rounded-full border-2 border-blue-200"
              />
            )}
            <span className="text-sm font-medium text-gray-700 hidden sm:block">
              {user.name}
            </span>
            <button
              onClick={logout}
              className="text-sm text-gray-500 hover:text-red-600 transition px-2 py-1 rounded border border-gray-200 hover:border-red-300"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="container mx-auto px-4 py-10">
        <div className="max-w-xl mx-auto space-y-8">

          {/* Upload card */}
          <div className="bg-white rounded-2xl shadow-lg p-8">
            <h2 className="text-xl font-bold text-gray-800 mb-1">Create a post</h2>
            <p className="text-sm text-gray-500 mb-6">
              Upload 3–5 photos. A unique shareable link will be generated for others to vote.
            </p>
            <PhotoUpload onUploadComplete={handleUploadComplete} />
          </div>

          {/* How it works */}
          <div className="grid grid-cols-3 gap-4 text-center">
            {[
              ["📤", "Upload", "3–5 photos"],
              ["🔗", "Share", "Unique link"],
              ["🗳️", "Vote", "1 pick each"],
            ].map(([icon, title, desc]) => (
              <div key={title} className="bg-white rounded-xl shadow p-4">
                <p className="text-2xl mb-1">{icon}</p>
                <p className="font-semibold text-gray-700 text-sm">{title}</p>
                <p className="text-xs text-gray-400">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
