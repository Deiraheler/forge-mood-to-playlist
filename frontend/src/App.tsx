import MoodInput from './components/MoodInput'

function App() {
  const handleGenerate = (mood: string) => {
    // API call will be wired up in a later task
    console.log('Generate playlist for:', mood)
  }

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
      <main className="flex-1 flex flex-col items-center justify-start px-4 pt-8">
        <MoodInput onGenerate={handleGenerate} />
      </main>
    </div>
  )
}

export default App
