import { useState, useCallback } from 'react'
import MoodInput from './components/MoodInput'
import ErrorBanner from './components/ErrorBanner'

function App() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleGenerate = useCallback(async (mood: string) => {
    setError(null)
    setIsLoading(true)
    try {
      // API call will be wired up in the API client task
      console.log('Generate playlist for:', mood)
      // Simulate async work so loading/curating UX is visible
      await new Promise(resolve => setTimeout(resolve, 2000))
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
      <main className="flex-1 flex flex-col items-center justify-start px-4 pt-8 gap-4">
        {error && (
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        )}
        <MoodInput onGenerate={handleGenerate} isLoading={isLoading} />
      </main>
    </div>
  )
}

export default App
