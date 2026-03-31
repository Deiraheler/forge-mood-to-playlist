/**
 * SkeletonPlaylist — shown while the AI generates a playlist.
 * Mirrors the layout of PlaylistHeader + 10 TrackCard rows with
 * staggered pulse delays for a wave-like loading feel.
 */
export default function SkeletonPlaylist() {
  return (
    <div
      className="w-full max-w-2xl mx-auto mt-4 sm:mt-6 flex flex-col gap-0 skeleton-playlist"
      aria-label="Loading playlist…"
      aria-busy="true"
      data-testid="skeleton-playlist"
    >
      {/* ── Header skeleton (mirrors PlaylistHeader) ── */}
      <div className="rounded-2xl bg-gray-800/60 border border-gray-700/50 overflow-hidden shadow-xl shadow-black/40 skeleton-fade-in">
        {/* Top band */}
        <div className="flex items-end gap-4 sm:gap-5 p-4 sm:p-5 md:p-6">
          {/* Album-art square */}
          <div className="shrink-0 w-20 h-20 sm:w-24 sm:h-24 md:w-32 md:h-32 rounded-xl bg-gray-700/70 skeleton-pulse" />

          {/* Text block */}
          <div className="flex flex-col gap-2.5 min-w-0 flex-1">
            {/* "PLAYLIST" label */}
            <div className="h-3 w-16 rounded bg-gray-700/70 skeleton-pulse" style={{ animationDelay: '80ms' }} />
            {/* Playlist name — two lines */}
            <div className="h-6 sm:h-7 w-3/4 rounded-lg bg-gray-700/70 skeleton-pulse" style={{ animationDelay: '120ms' }} />
            <div className="h-5 w-1/2 rounded-lg bg-gray-700/60 skeleton-pulse" style={{ animationDelay: '160ms' }} />
            {/* Mood badge */}
            <div className="h-6 w-28 rounded-full bg-gray-700/50 skeleton-pulse" style={{ animationDelay: '200ms' }} />
          </div>
        </div>

        {/* Description bar */}
        <div className="px-4 sm:px-5 md:px-6 pb-4 sm:pb-5 flex flex-col gap-2">
          <div className="h-3.5 w-full rounded bg-gray-700/50 skeleton-pulse" style={{ animationDelay: '240ms' }} />
          <div className="h-3.5 w-5/6 rounded bg-gray-700/40 skeleton-pulse" style={{ animationDelay: '280ms' }} />
        </div>
      </div>

      {/* ── Track row skeletons (mirrors TrackCard × 10) ── */}
      {Array.from({ length: 10 }).map((_, i) => (
        <div
          key={i}
          className="
            flex items-start gap-3 sm:gap-4 px-3 sm:px-4 py-3
            border-l-4 border-purple-500/30
            bg-gray-800/40 rounded-r-xl
            skeleton-fade-in
            min-h-[56px]
          "
          style={{ animationDelay: `${i * 45}ms` }}
        >
          {/* Track number */}
          <div
            className="shrink-0 w-5 sm:w-6 h-4 rounded bg-gray-700/60 mt-1 skeleton-pulse"
            style={{ animationDelay: `${320 + i * 45}ms` }}
          />

          {/* Track info */}
          <div className="flex flex-col gap-1.5 flex-1 min-w-0">
            {/* Title */}
            <div
              className="h-4 rounded bg-gray-700/70 skeleton-pulse"
              style={{
                width: `${55 + ((i * 17) % 35)}%`,
                animationDelay: `${360 + i * 45}ms`,
              }}
            />
            {/* Artist */}
            <div
              className="h-3 rounded bg-gray-700/50 skeleton-pulse"
              style={{
                width: `${30 + ((i * 13) % 30)}%`,
                animationDelay: `${400 + i * 45}ms`,
              }}
            />
            {/* Vibe */}
            <div
              className="h-3 rounded bg-purple-900/30 skeleton-pulse"
              style={{
                width: `${45 + ((i * 11) % 40)}%`,
                animationDelay: `${440 + i * 45}ms`,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
