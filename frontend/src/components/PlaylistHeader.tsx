import type { PlaylistResponse } from '../api/client'

interface PlaylistHeaderProps {
  playlist: PlaylistResponse
}

/**
 * Deterministic hash of a string → number 0..1
 * Used to pick gradient colors from the mood text so each mood
 * always produces the same palette.
 */
function hashString(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (hash * 31 + str.charCodeAt(i)) >>> 0
  }
  return hash / 0xffffffff
}

/**
 * Convert a 0..1 value to an HSL hue (0..360).
 * We spread two hues ~120° apart for a rich two-stop gradient.
 */
function moodToGradient(mood: string): { from: string; to: string } {
  const h = hashString(mood)
  const hue1 = Math.round(h * 360)
  const hue2 = (hue1 + 120) % 360
  return {
    from: `hsl(${hue1}, 70%, 45%)`,
    to: `hsl(${hue2}, 80%, 35%)`,
  }
}

export default function PlaylistHeader({ playlist }: PlaylistHeaderProps) {
  const { playlist_name, mood, description } = playlist
  const { from, to } = moodToGradient(mood)

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Card */}
      <div className="rounded-2xl bg-gray-800/60 border border-gray-700/50 overflow-hidden shadow-xl shadow-black/40">
        {/* Top band — album-art placeholder + text */}
        <div className="flex items-end gap-5 p-5 sm:p-6">
          {/* Generative album-art square */}
          <div
            className="shrink-0 w-24 h-24 sm:w-32 sm:h-32 rounded-xl shadow-lg shadow-black/50 flex items-center justify-center"
            style={{
              background: `linear-gradient(135deg, ${from} 0%, ${to} 100%)`,
            }}
            aria-hidden="true"
          >
            {/* Subtle music-note icon overlay */}
            <span className="text-white/30 text-4xl select-none">♫</span>
          </div>

          {/* Text block */}
          <div className="flex flex-col gap-2 min-w-0">
            {/* "PLAYLIST" label — Spotify-style */}
            <span className="text-xs font-semibold uppercase tracking-widest text-gray-400">
              Playlist
            </span>

            {/* Playlist name */}
            <h2 className="text-2xl sm:text-3xl font-bold text-white leading-tight line-clamp-2">
              {playlist_name}
            </h2>

            {/* Mood badge */}
            <span
              className="inline-flex items-center self-start gap-1.5 mt-1
                         px-3 py-1 rounded-full text-xs font-semibold
                         bg-white/10 text-gray-200 border border-white/10
                         backdrop-blur-sm"
            >
              <span aria-hidden="true">🎭</span>
              {mood}
            </span>
          </div>
        </div>

        {/* Description bar */}
        {description && (
          <div className="px-5 sm:px-6 pb-5">
            <p className="text-sm text-gray-400 leading-relaxed">
              {description}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
