import { useState, useEffect } from "react";
import { createPost } from "../api";

export default function PhotoUpload({ onUploadComplete }) {
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (files.length === 0) {
      setPreviews([]);
      return;
    }
    const urls = files.map((f) => URL.createObjectURL(f));
    setPreviews(urls);
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, [files]);

  const handleFileChange = (e) => {
    const selected = Array.from(e.target.files);
    if (selected.length < 3 || selected.length > 5) {
      setError("Please select between 3 and 5 images.");
      setFiles([]);
    } else {
      setError("");
      setFiles(selected);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (files.length === 0) return;

    setLoading(true);
    setError("");

    try {
      const data = await createPost(files);
      setFiles([]);
      if (onUploadComplete) {
        onUploadComplete(data.shareable_code, data.post_id, data.photos_count);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {/* Drop zone */}
        <div className="border-2 border-dashed border-gray-300 p-6 rounded-lg text-center hover:bg-gray-50 transition">
          <input
            type="file"
            multiple
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
            id="fileInput"
            disabled={loading}
          />
          <label htmlFor="fileInput" className="cursor-pointer text-gray-600 hover:text-gray-900">
            <p className="text-lg font-semibold">Click to select photos (3–5)</p>
            <p className="text-sm text-gray-400 mt-1">JPG, PNG, GIF or WEBP</p>
          </label>
        </div>

        {/* Preview grid */}
        {previews.length > 0 && (
          <div className="grid grid-cols-3 gap-3">
            {previews.map((src, idx) => (
              <div key={idx}>
                <img
                  src={src}
                  alt={`Preview ${idx + 1}`}
                  className="w-full h-24 object-cover rounded-lg border border-gray-200"
                />
                <p className="text-xs text-gray-400 mt-1 truncate text-center">
                  {files[idx]?.name}
                </p>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || files.length === 0}
          className={`w-full py-3 rounded-lg font-semibold text-white transition flex items-center justify-center gap-2 ${
            loading || files.length === 0
              ? "bg-gray-300 cursor-not-allowed"
              : "bg-blue-600 hover:bg-blue-700 shadow-md"
          }`}
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Publishing…
            </>
          ) : "🚀 Create Post"}
        </button>
      </form>
    </div>
  );
}
