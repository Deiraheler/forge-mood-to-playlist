import type { Track } from '../api/client'
import TrackCard from './TrackCard'

interface TrackListProps {
  tracks: Track[]
}

export default function TrackList({ tracks }: TrackListProps) {
  return (
    <div className="w-full max-w-2xl mx-auto mt-4 flex flex-col gap-2">
      {tracks.map((track, index) => (
        <div
          key={`${track.title}-${track.artist}-${index}`}
          className="opacity-0 animate-fade-in-up"
          style={{ animationDelay: `${index * 50}ms`, animationFillMode: 'forwards' }}
        >
          <TrackCard track={track} index={index} />
        </div>
      ))}
    </div>
  )
}
