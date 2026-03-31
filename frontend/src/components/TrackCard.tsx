import type { Track } from '../api/client'

interface TrackCardProps {
  track: Track
  index: number
}

export default function TrackCard({ track, index }: TrackCardProps) {
  const { title, artist, vibe } = track

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
      </div>
    </div>
  )
}
