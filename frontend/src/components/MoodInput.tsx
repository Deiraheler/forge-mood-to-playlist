import { useState, useEffect, useCallback, useRef, forwardRef } from 'react'

const PLACEHOLDER_EXAMPLES = [
  '3am can\'t sleep…',
  'driving through rain…',
  'post-breakup energy…',
  'first day of summer…',
  'deep in the zone…',
  'sunday morning slow…',
]

const CURATING_MESSAGES = [
  'Tuning into your vibe…',
  'Scanning the sonic universe…',
  'Matching moods to melodies…',
  'Digging through the crates…',
  'Reading between the frequencies…',
  'Consulting the music oracle…',
  'Finding your perfect sound…',
  'Assembling the tracklist…',
]

interface MoodInputProps {
  value: string
  onChange: (value: string) => void
  onGenerate: (mood: string) => void
  isLoading?: boolean
}

const MoodInput = forwardRef<HTMLDivElement, MoodInputProps>(
  function MoodInput({ value, onChange, onGenerate, isLoading = false }, ref) {
    const [placeholderIndex, setPlaceholderIndex] = useState(0)
    const [displayedPlaceholder, setDisplayedPlaceholder] = useState('')
    const [isDeleting, setIsDeleting] = useState(false)
    const [charIndex, setCharIndex] = useState(0)
    const [curatingMsg, setCuratingMsg] = useState(CURATING_MESSAGES[0])
    const curatingIndexRef = useRef(0)

    // Typewriter effect for placeholder cycling
    useEffect(() => {
      if (value) return // Don't animate if user has typed something

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
    }, [value, charIndex, isDeleting, placeholderIndex])

    // Cycle through curating messages while loading
    useEffect(() => {
      if (!isLoading) return
      const start = Math.floor(Math.random() * CURATING_MESSAGES.length)
      curatingIndexRef.current = start
      setCuratingMsg(CURATING_MESSAGES[start])

      const interval = setInterval(() => {
        curatingIndexRef.current = (curatingIndexRef.current + 1) % CURATING_MESSAGES.length
        setCuratingMsg(CURATING_MESSAGES[curatingIndexRef.current])
      }, 1800)

      return () => clearInterval(interval)
    }, [isLoading])

    const handleSubmit = useCallback(() => {
      const trimmed = value.trim()
      if (!trimmed || isLoading) return
      onGenerate(trimmed)
    }, [value, isLoading, onGenerate])

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSubmit()
      }
    }

    return (
      <div ref={ref} className="w-full max-w-2xl mx-auto flex flex-col gap-3 sm:gap-4">
        <div className="relative">
          <textarea
            value={value}
            onChange={e => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={displayedPlaceholder || 'Describe your mood or situation…'}
            aria-label="Describe your mood or situation"
            aria-describedby="mood-hint"
            rows={3}
            disabled={isLoading}
            className="
              w-full resize-none
              rounded-xl
              bg-gray-800
              text-white
              placeholder-gray-500
              px-4 py-3 sm:px-5 sm:py-4
              text-base sm:text-lg leading-relaxed
              border border-gray-700
              outline-none
              focus:ring-2 focus:ring-purple-500 focus:border-transparent
              transition-all duration-200
              disabled:opacity-50 disabled:cursor-not-allowed
            "
          />
          <span
            id="mood-hint"
            className="absolute bottom-2.5 right-3 sm:bottom-3 sm:right-4 text-xs text-gray-600 select-none hidden sm:inline"
            aria-hidden="true"
          >
            {value.length > 0 && `${value.length} chars · Enter to generate`}
          </span>
        </div>

        <button
          onClick={handleSubmit}
          disabled={!value.trim() || isLoading}
          aria-label={isLoading ? 'Generating playlist…' : 'Generate playlist from mood'}
          className="
            w-full py-4
            min-h-[52px]
            rounded-xl
            font-semibold text-base sm:text-lg text-white
            bg-gradient-to-r from-purple-600 via-pink-500 to-orange-400
            hover:from-purple-500 hover:via-pink-400 hover:to-orange-300
            active:scale-[0.98]
            transition-all duration-200
            shadow-lg shadow-purple-900/40
            disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none disabled:active:scale-100
            cursor-pointer
            touch-manipulation
            btn-glow
          "
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span className="transition-opacity duration-500 text-sm sm:text-base">{curatingMsg}</span>
            </span>
          ) : (
            '✨ Generate Playlist'
          )}
        </button>
      </div>
    )
  }
)

export default MoodInput
