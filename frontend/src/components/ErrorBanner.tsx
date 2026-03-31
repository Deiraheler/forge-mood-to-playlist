interface ErrorBannerProps {
  message: string
  onDismiss: () => void
}

export default function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="
        w-full max-w-2xl mx-auto
        flex items-start gap-3
        rounded-xl
        bg-red-950/60
        border border-red-500/40
        px-5 py-4
        text-red-300
        shadow-lg shadow-red-900/20
        animate-fade-in
      "
    >
      {/* Icon */}
      <span className="mt-0.5 shrink-0 text-red-400 text-lg" aria-hidden="true">
        ⚠️
      </span>

      {/* Message */}
      <p className="flex-1 text-sm leading-relaxed">{message}</p>

      {/* Dismiss button */}
      <button
        onClick={onDismiss}
        aria-label="Dismiss error"
        className="
          shrink-0
          text-red-400 hover:text-red-200
          transition-colors duration-150
          cursor-pointer
          p-0.5
          rounded
          focus:outline-none focus:ring-2 focus:ring-red-500
        "
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="w-4 h-4"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>
    </div>
  )
}
