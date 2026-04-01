import type { Track } from '../api/client'

interface TrackCardProps {
  track: Track
  index: number
}

/** YouTube SVG icon (simplified play-button shape) */
function YouTubeIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4 fill-current" aria-hidden="true">
      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
    </svg>
  )
}

/** SoundCloud SVG icon */
function SoundCloudIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4 fill-current" aria-hidden="true">
      <path d="M1.175 12.225c-.046 0-.089.034-.099.08l-.233 1.154.233 1.105c.01.045.053.08.099.08.045 0 .09-.035.099-.08l.255-1.105-.27-1.154c-.009-.045-.054-.08-.084-.08zm-.899.828c-.06 0-.111.048-.12.108l-.156.998.156.965c.009.06.06.108.12.108.063 0 .114-.048.12-.108l.18-.965-.18-.998c-.006-.06-.057-.108-.12-.108zm4.069-.108c-.09 0-.165.073-.165.165v2.19c0 .09.075.165.165.165h.435v-2.52h-.435zm-1.5.42c-.09 0-.165.073-.165.165v1.77c0 .09.075.165.165.165h.435v-2.1h-.435zm-1.5-.315c-.09 0-.165.073-.165.165v2.085c0 .09.075.165.165.165h.435v-2.415h-.435zm6.27-4.515c-.3 0-.585.06-.855.165-.195-2.43-2.22-4.335-4.71-4.335-1.275 0-2.43.48-3.3 1.275C.705 6.42.165 7.545.165 8.79v6.195c0 .63.51 1.14 1.14 1.14h11.34c.63 0 1.14-.51 1.14-1.14V9.84c0-2.1-1.71-3.81-3.81-3.81z" />
    </svg>
  )
}

export default function TrackCard({ track, index }: TrackCardProps) {
  const { title, artist, vibe, youtube_link, soundcloud_link } = track

  return (
    <div
      className="
        group flex items-start gap-3 sm:gap-4 px-3 sm:px-4 py-3 sm:py-3
        border-l-4 border-purple-500
        bg-gray-800/40 hover:bg-gray-700/50
        rounded-r-xl transition-colors duration-150
        cursor-default
        min-h-[56px]
      "
    >
      {/* Track number */}
      <span className="shrink-0 w-5 sm:w-6 text-center text-sm font-mono text-gray-500 group-hover:text-purple-400 transition-colors duration-150 mt-0.5">
        {index + 1}
      </span>

      {/* Track info */}
      <div className="flex flex-col gap-0.5 min-w-0 flex-1">
        {/* Song title */}
        <span className="font-semibold text-white leading-snug text-sm sm:text-base break-words">
          {title}
        </span>

        {/* Artist */}
        <span className="text-xs sm:text-sm text-gray-400 break-words">
          {artist}
        </span>

        {/* Vibe description */}
        <span className="text-xs italic text-purple-400/80 leading-relaxed mt-0.5 break-words">
          {vibe}
        </span>

        {/* Media links */}
        {(youtube_link || soundcloud_link) && (
          <div className="flex items-center gap-3 mt-1.5">
            {youtube_link && (
              <a
                href={youtube_link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 transition-colors duration-150"
                aria-label={`Listen to ${title} on YouTube`}
              >
                <YouTubeIcon />
                <span>YouTube</span>
              </a>
            )}
            {soundcloud_link && (
              <a
                href={soundcloud_link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-orange-400 hover:text-orange-300 transition-colors duration-150"
                aria-label={`Listen to ${title} on SoundCloud`}
              >
                <SoundCloudIcon />
                <span>SoundCloud</span>
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
