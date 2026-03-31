import { useState, useCallback } from 'react'
import MoodInput from './components/MoodInput'
import ErrorBanner from './components/ErrorBanner'
import PlaylistHeader from './components/PlaylistHeader'
import TrackList from './components/TrackList'
import { generatePlaylist, type PlaylistResponse } from './api/client'

function App() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [playlist, setPlaylist] = useState<PlaylistResponse | null>(null)

  const handleGenerate = useCallback(async (mood: string) => {
    setError(null)
    setPlaylist(null)
    setIsLoading(true)
    try {
      const result = await generatePlaylist(mood)
      setPlaylist(result)
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Something went wrong. Please try again.'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex flex-col">
      {/* Header */}
      <header className="py-8 text-center">
        <h1 className="text-4xl font-bold text-white tracking-tight">
          🎵 Mood-to-Playlist
        </h1>
        <p className="mt-2 text-gray-400 text-sm">
          Describe your mood and get a playlist that fits.
        </p>
      </header>

      {/* Main content area */}
      <main className="flex-1 flex flex-col items-center justify-start px-4 pt-8 pb-16 gap-4">
        {error && (
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        )}

        <MoodInput onGenerate={handleGenerate} isLoading={isLoading} />

        {/* Loading skeleton */}
        {isLoading && (
          <div className="w-full max-w-2xl mx-auto mt-6 flex flex-col gap-3 animate-pulse">
            <div className="h-36 rounded-2xl bg-gray-800/60" />
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-16 rounded-r-xl bg-gray-800/40 border-l-4 border-purple-500/30" />
            ))}
          </div>
        )}

        {/* Playlist result */}
        {!isLoading && playlist && (
          <div className="w-full max-w-2xl mx-auto mt-6 flex flex-col gap-0">
            <PlaylistHeader playlist={playlist} />
            <TrackList tracks={playlist.tracks} />
          </div>
        )}
      </main>
    </div>
  )
}

export default App
