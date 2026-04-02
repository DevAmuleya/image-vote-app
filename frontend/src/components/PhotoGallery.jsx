import { useEffect, useState, useRef, useCallback } from "react";
import { getPost, castVote } from "../api";
import { useAuth } from "../contexts/AuthContext";

const POLL_INTERVAL = 15000; // re-fetch every 15 s to show live vote counts

export default function PhotoGallery({ postCode }) {
  const { user } = useAuth();

  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Voting state
  const [selectedPhotoId, setSelectedPhotoId] = useState(null);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [voteError, setVoteError] = useState("");

  // Full-size modal
  const [modalPhoto, setModalPhoto] = useState(null);

  const pollTimerRef = useRef(null);

  const fetchPost = useCallback(async ({ bust = false, silent = false } = {}) => {
    if (!silent) setLoading(true);
    setError("");
    try {
      const data = await getPost(postCode, { bust });
      setPost(data);
    } catch (err) {
      setError(err.message);
    } finally {
      if (!silent) setLoading(false);
    }
  }, [postCode]);

  // Start polling when component mounts; stop on unmount
  useEffect(() => {
    if (!postCode) return;
    fetchPost();
    pollTimerRef.current = setInterval(() => fetchPost({ bust: true, silent: true }), POLL_INTERVAL);
    return () => clearInterval(pollTimerRef.current);
  }, [postCode, fetchPost]);

  const handleSubmitVote = async () => {
    const photoId = selectedPhotoId;
    if (!photoId || hasVoted || !user || submitting) return;
    setVoteError("");
    setSubmitting(true);
    try {
      await castVote(post.post_id, photoId, comment.trim() || null);
      // Optimistic update: flip to results view instantly without a page reload.
      // Background silent refresh syncs the real vote counts from the server.
      setPost(prev => ({
        ...prev,
        user_vote: { photo_id: photoId, comment: comment.trim() || null },
        total_votes: (prev.total_votes ?? 0) + 1,
        photos: prev.photos.map(p =>
          p.id === photoId ? { ...p, vote_count: (p.vote_count ?? 0) + 1 } : p
        ),
      }));
      setSelectedPhotoId(null);
      setComment("");
      fetchPost({ bust: true, silent: true });
    } catch (err) {
      setVoteError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSelectPhoto = (photoId) => {
    if (hasVoted || !user || submitting) return;
    setVoteError("");
    setSelectedPhotoId(prev => (prev === photoId ? null : photoId));
  };

  // ── Loading / error states ────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="space-y-6">
        {/* Creator skeleton */}
        <div className="flex items-center gap-3 animate-pulse">
          <div className="w-10 h-10 rounded-full bg-gray-200" />
          <div className="space-y-1.5 flex-1">
            <div className="h-3.5 w-32 bg-gray-200 rounded" />
            <div className="h-3 w-20 bg-gray-200 rounded" />
          </div>
          <div className="h-3 w-16 bg-gray-200 rounded" />
        </div>
        {/* Photo grid skeleton */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[0, 1, 2].map((i) => (
            <div key={i} className="rounded-xl overflow-hidden border-2 border-gray-100 animate-pulse">
              <div className="w-full h-44 bg-gray-200" />
              <div className="p-3 space-y-2">
                <div className="h-2 w-3/4 bg-gray-200 rounded" />
                <div className="h-2 w-1/2 bg-gray-200 rounded" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded-lg">
        {error}
      </div>
    );
  }

  if (!post) return null;

  const hasVoted = !!post.user_vote;
  const userVotedPhotoId = post.user_vote?.photo_id ?? null;
  const totalVotes = post.total_votes ?? 0;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-8">

      {/* Creator info */}
      {post.creator && (
        <div className="flex items-center gap-3">
          {post.creator.picture_url && (
            <img
              src={post.creator.picture_url}
              alt={post.creator.name}
              loading="lazy"
              decoding="async"
              className="w-10 h-10 rounded-full border-2 border-blue-200"
            />
          )}
          <div>
            <p className="font-semibold text-gray-800">{post.creator.name}</p>
            <p className="text-xs text-gray-400">
              {new Date(post.created_at).toLocaleDateString(undefined, {
                year: "numeric", month: "short", day: "numeric"
              })}
            </p>
          </div>
          <span className="ml-auto text-sm text-gray-500">
            {totalVotes} vote{totalVotes !== 1 ? "s" : ""}
          </span>
        </div>
      )}

      {/* ── Already voted banner ─────────────────────────────────────────── */}
      {hasVoted && (
        <div className="bg-green-50 border border-green-300 rounded-lg px-4 py-3 text-sm text-green-800">
          ✅ You voted for <strong>photo {post.photos.findIndex(p => p.id === userVotedPhotoId) + 1}</strong>.
          {post.user_vote.comment && (
            <span> Your comment: <em>"{post.user_vote.comment}"</em></span>
          )}
        </div>
      )}

      {/* ── Photo grid ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {post.photos.map((photo, idx) => {
          const isSelected = selectedPhotoId === photo.id;
          const isUserChoice = userVotedPhotoId === photo.id;
          const votePercent =
            totalVotes > 0 ? Math.round((photo.vote_count / totalVotes) * 100) : 0;

          return (
            <div
              key={photo.id}
              className={[
                "relative rounded-xl overflow-hidden border-2 transition-all duration-200 cursor-default",
                isSelected
                  ? "border-indigo-500 shadow-lg ring-2 ring-indigo-300"
                  : isUserChoice
                  ? "border-green-500 ring-2 ring-green-300"
                  : "border-gray-200 hover:border-indigo-300",
              ].join(" ")}
            >
              {/* Image — object-cover fills the card completely, click = open modal */}
              <div
                className="w-full h-44 overflow-hidden cursor-zoom-in"
                onClick={() => setModalPhoto(photo)}
              >
                <img
                  src={photo.media_url}
                  alt={`Photo ${idx + 1}`}
                  loading="lazy"
                  decoding="async"
                  className="w-full h-full object-cover object-center transition-transform duration-200 hover:scale-105"
                />
              </div>

              {/* Selected overlay tint */}
              {isSelected && (
                <div className="absolute inset-0 bg-indigo-500 bg-opacity-10 pointer-events-none" />
              )}

              {/* Select/Deselect button — bottom-right */}
              {!hasVoted && user && (
                <button
                  onClick={(e) => { e.stopPropagation(); handleSelectPhoto(photo.id); }}
                  disabled={submitting}
                  className={`absolute bottom-3 right-3 text-xs font-semibold px-3 py-1.5 rounded-lg shadow-md transition-all ${
                    isSelected
                      ? "bg-indigo-600 hover:bg-indigo-700 text-white ring-2 ring-indigo-300"
                      : "bg-white hover:bg-indigo-50 text-indigo-700 border border-indigo-300"
                  }`}
                >
                  {isSelected ? "✓ Selected" : "Select"}
                </button>
              )}

              {/* Result bar (post-vote) */}
              {hasVoted && (
                <div className="px-3 py-2 bg-white">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-gray-500">{photo.vote_count} vote{photo.vote_count !== 1 ? "s" : ""}</span>
                    <span className="font-semibold text-gray-700">{votePercent}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-1.5 rounded-full transition-all duration-700 ${isUserChoice ? "bg-green-500" : "bg-blue-400"}`}
                      style={{ width: `${votePercent}%` }}
                    />
                  </div>
                  {isUserChoice && (
                    <p className="text-xs text-green-600 font-semibold mt-1">Your choice</p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Submit vote bar ───────────────────────────────────────────────── */}
      {!hasVoted && user && selectedPhotoId && (
        <div className="sticky bottom-4 z-20">
          <div className="bg-indigo-600 rounded-2xl shadow-xl px-5 py-4 flex flex-col gap-3 text-white">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-semibold text-sm">
                  Photo {post.photos.findIndex(p => p.id === selectedPhotoId) + 1} selected
                </p>
                <p className="text-indigo-200 text-xs mt-0.5">
                  Change your mind? Tap another photo to switch.
                </p>
              </div>
              <button
                onClick={handleSubmitVote}
                disabled={submitting}
                className="flex-shrink-0 bg-white text-indigo-700 hover:bg-indigo-50 disabled:bg-indigo-300 disabled:text-white font-bold text-sm px-5 py-2.5 rounded-xl shadow transition"
              >
                {submitting ? "Submitting…" : "Submit Vote"}
              </button>
            </div>
            <textarea
              value={comment}
              onChange={e => setComment(e.target.value)}
              placeholder="Add a comment (optional)…"
              maxLength={300}
              rows={2}
              className="w-full bg-indigo-700 text-white placeholder-indigo-300 text-sm rounded-xl px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-white/50"
            />
          </div>
        </div>
      )}

      {/* Vote error */}
      {voteError && (
        <p className="text-red-600 text-sm text-center">{voteError}</p>
      )}

      {/* Not logged in — prompt */}
      {!hasVoted && !user && (
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl px-5 py-4 text-white text-center shadow-md">
          <p className="font-bold text-base">Sign in to cast your vote</p>
          <p className="text-blue-200 text-sm mt-0.5">Use the button at the top of the page to sign in with Facebook.</p>
        </div>
      )}

      {/* ── Votes list ───────────────────────────────────────────────────── */}
      {hasVoted && post.votes?.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-semibold text-gray-700">Votes ({post.votes.length})</h3>
          {post.votes.map((vote) => {
            const photoIdx = post.photos.findIndex(p => p.id === vote.photo_id);
            return (
              <div key={vote.voter?.id} className="flex items-start gap-3 bg-gray-50 rounded-lg p-3">
                {vote.voter?.picture_url && (
                  <img
                    src={vote.voter.picture_url}
                    alt={vote.voter.name}
                    loading="lazy"
                    decoding="async"
                    className="w-8 h-8 rounded-full border border-gray-200 flex-shrink-0"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800">
                    {vote.voter?.name ?? "Anonymous"}
                    <span className="ml-2 text-gray-500 font-normal">
                      voted for photo #{photoIdx + 1}
                    </span>
                  </p>
                  {vote.comment && (
                    <p className="text-sm text-gray-600 mt-0.5 italic">"{vote.comment}"</p>
                  )}
                  <p className="text-xs text-gray-400 mt-0.5">
                    {new Date(vote.voted_at).toLocaleString()}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Full-size modal ───────────────────────────────────────────────── */}
      {modalPhoto && (
        <div
          className="fixed inset-0 bg-black bg-opacity-85 flex items-center justify-center z-50 p-4"
          onClick={() => setModalPhoto(null)}
        >
          <div
            className="relative bg-white rounded-xl shadow-2xl max-w-4xl max-h-[90vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setModalPhoto(null)}
              className="absolute top-3 right-3 bg-black bg-opacity-50 text-white rounded-full w-9 h-9 flex items-center justify-center hover:bg-red-600 transition z-10"
            >
              ✕
            </button>
            <img src={modalPhoto.media_url} alt="Full size" className="w-full h-auto" />
          </div>
        </div>
      )}
    </div>
  );
}
