import { useState, useEffect, useCallback } from 'react'

const PLACEHOLDER_EXAMPLES = [
  '3am can\'t sleep…',
  'driving through rain…',
  'post-breakup energy…',
  'first day of summer…',
  'deep in the zone…',
  'sunday morning slow…',
]

interface MoodInputProps {
  onGenerate: (mood: string) => void
  isLoading?: boolean
}

export default function MoodInput({ onGenerate, isLoading = false }: MoodInputProps) {
  const [mood, setMood] = useState('')
  const [placeholderIndex, setPlaceholderIndex] = useState(0)
  const [displayedPlaceholder, setDisplayedPlaceholder] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const [charIndex, setCharIndex] = useState(0)

  // Typewriter effect for placeholder cycling
  useEffect(() => {
    if (mood) return // Don't animate if user has typed something

    const current = PLACEHOLDER_EXAMPLES[placeholderIndex]

    if (!isDeleting && charIndex < current.length) {
      const timeout = setTimeout(() => {
        setDisplayedPlaceholder(current.slice(0, charIndex + 1))
        setCharIndex(c => c + 1)
      }, 60)
      return () => clearTimeout(timeout)
    }

    if (!isDeleting && charIndex === current.length) {
      const timeout = setTimeout(() => setIsDeleting(true), 1800)
      return () => clearTimeout(timeout)
    }

    if (isDeleting && charIndex > 0) {
      const timeout = setTimeout(() => {
        setDisplayedPlaceholder(current.slice(0, charIndex - 1))
        setCharIndex(c => c - 1)
      }, 35)
      return () => clearTimeout(timeout)
    }

    if (isDeleting && charIndex === 0) {
      setIsDeleting(false)
      setPlaceholderIndex(i => (i + 1) % PLACEHOLDER_EXAMPLES.length)
    }
  }, [mood, charIndex, isDeleting, placeholderIndex])

  const handleSubmit = useCallback(() => {
    const trimmed = mood.trim()
    if (!trimmed || isLoading) return
    onGenerate(trimmed)
  }, [mood, isLoading, onGenerate])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="w-full max-w-2xl mx-auto flex flex-col gap-4">
      <div className="relative">
        <textarea
          value={mood}
          onChange={e => setMood(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={displayedPlaceholder || 'Describe your mood or situation…'}
          rows={4}
          disabled={isLoading}
          className="
            w-full resize-none
            rounded-xl
            bg-gray-800
            text-white
            placeholder-gray-500
            px-5 py-4
            text-lg leading-relaxed
            border border-gray-700
            outline-none
            focus:ring-2 focus:ring-purple-500 focus:border-transparent
            transition-all duration-200
            disabled:opacity-50 disabled:cursor-not-allowed
          "
        />
        <span className="absolute bottom-3 right-4 text-xs text-gray-600 select-none">
          {mood.length > 0 && `${mood.length} chars · Enter to generate`}
        </span>
      </div>

      <button
        onClick={handleSubmit}
        disabled={!mood.trim() || isLoading}
        className="
          w-full py-4
          rounded-xl
          font-semibold text-lg text-white
          bg-gradient-to-r from-purple-600 via-pink-500 to-orange-400
          hover:from-purple-500 hover:via-pink-400 hover:to-orange-300
          active:scale-[0.98]
          transition-all duration-200
          shadow-lg shadow-purple-900/40
          disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none disabled:active:scale-100
          cursor-pointer
        "
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Generating…
          </span>
        ) : (
          '✨ Generate Playlist'
        )}
      </button>
    </div>
  )
}
