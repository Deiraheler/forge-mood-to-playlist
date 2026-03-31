import { useState, useCallback, useRef, useEffect } from 'react'
import MoodInput from './components/MoodInput'
import ErrorBanner from './components/ErrorBanner'
import PlaylistHeader from './components/PlaylistHeader'
import TrackList from './components/TrackList'
import SkeletonPlaylist from './components/SkeletonPlaylist'
import { generatePlaylist, type PlaylistResponse } from './api/client'

const MOOD_SUGGESTIONS = [
  '3am thoughts',
  'road trip energy',
  'rainy sunday',
  'gym beast mode',
  'falling in love',
]

function App() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [playlist, setPlaylist] = useState<PlaylistResponse | null>(null)
  const [moodValue, setMoodValue] = useState('')
  const [playlistKey, setPlaylistKey] = useState(0)
  const inputRef = useRef<HTMLDivElement>(null)
  const bgRef = useRef<HTMLDivElement>(null)

  // Scroll-based parallax: shift the background gradient hue as user scrolls
  useEffect(() => {
    const el = document.documentElement
    let rafId: number
    const onScroll = () => {
      rafId = requestAnimationFrame(() => {
        const scrollY = window.scrollY
        const maxScroll = document.body.scrollHeight - window.innerHeight
        const progress = maxScroll > 0 ? scrollY / maxScroll : 0
        // Smoothly shift hue from 270 (purple) → 220 (blue) as user scrolls down
        const hue = Math.round(270 - progress * 50)
        el.style.setProperty('--bg-hue', String(hue))
      })
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      cancelAnimationFrame(rafId)
    }
  }, [])

  const handleGenerate = useCallback(async (mood: string) => {
    setError(null)
    setPlaylist(null)
    setIsLoading(true)
    try {
      const result = await generatePlaylist(mood)
      setPlaylist(result)
      setPlaylistKey(k => k + 1)
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Something went wrong. Please try again.'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const handleTryAnother = useCallback(() => {
    setPlaylist(null)
    setError(null)
    setMoodValue('')
    setTimeout(() => {
      inputRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 50)
  }, [])

  const handleChipClick = useCallback((chip: string) => {
    setMoodValue(chip)
    handleGenerate(chip)
    setTimeout(() => {
      inputRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 50)
  }, [handleGenerate])

  return (
    <div ref={bgRef} className="min-h-screen bg-dynamic flex flex-col">
      {/* Header */}
      <header className="py-6 sm:py-8 text-center px-4">
        <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
          🎵 Mood-to-Playlist
        </h1>
        <p className="mt-2 text-gray-400 text-xs sm:text-sm">
          Describe your mood and get a playlist that fits.
        </p>
      </header>

      {/* Main content area */}
      <main className="flex-1 flex flex-col items-center justify-start px-3 sm:px-4 md:px-6 pt-4 sm:pt-8 pb-16 gap-4">
        {error && (
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        )}

        <MoodInput
          ref={inputRef}
          value={moodValue}
          onChange={setMoodValue}
          onGenerate={handleGenerate}
          isLoading={isLoading}
        />

        {/* Mood suggestion chips */}
        <div className="w-full max-w-2xl mx-auto flex flex-wrap gap-2 justify-center">
          {MOOD_SUGGESTIONS.map(chip => (
            <button
              key={chip}
              onClick={() => handleChipClick(chip)}
              disabled={isLoading}
              className="
                px-4 py-2 sm:py-1.5
                min-h-[40px] sm:min-h-0
                rounded-full
                text-sm font-medium
                bg-gray-800 text-gray-300
                border border-gray-700
                hover:border-purple-500 hover:text-purple-300 hover:bg-gray-700
                active:scale-95
                transition-all duration-150
                disabled:opacity-40 disabled:cursor-not-allowed
                cursor-pointer
                touch-manipulation
              "
            >
              {chip}
            </button>
          ))}
        </div>

        {/* Loading skeleton */}
        {isLoading && <SkeletonPlaylist />}

        {/* Playlist result — animates in when it first appears */}
        {!isLoading && playlist && (
          <div
            key={playlistKey}
            className="w-full max-w-2xl mx-auto mt-4 sm:mt-6 flex flex-col gap-0 playlist-enter"
          >
            <PlaylistHeader playlist={playlist} />
            <TrackList tracks={playlist.tracks} />

            {/* Try Another Mood */}
            <div className="mt-8 flex justify-center px-2">
              <button
                onClick={handleTryAnother}
                className="
                  w-full sm:w-auto
                  px-8 py-3.5 sm:py-3
                  min-h-[48px] sm:min-h-0
                  rounded-full
                  font-semibold text-white text-base
                  bg-gray-800 border border-gray-600
                  hover:border-purple-500 hover:bg-gray-700 hover:text-purple-300
                  active:scale-95
                  transition-all duration-200
                  shadow-md
                  cursor-pointer
                  touch-manipulation
                "
              >
                🔄 Try Another Mood
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
