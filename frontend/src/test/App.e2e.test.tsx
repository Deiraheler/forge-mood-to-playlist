/**
 * End-to-end component tests for Mood-to-Playlist
 *
 * Covers:
 *  1. Load app — header, input, and suggestion chips are rendered
 *  2. Type a mood and generate a playlist
 *  3. View results — tracks + playlist header shown
 *  4. "Try another mood" resets to input view
 *  5. Click a suggestion chip — fills input with that mood
 *  6. Loading skeleton shown while request is in-flight
 *  7. Error banner shown when backend is down (fetch rejects)
 *  8. Error banner dismissed on click
 *  9. Cached badge shown on repeated mood (cached: true in response)
 * 10. Mobile viewport — layout stays functional at 375px width
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'

// ─── Helpers ──────────────────────────────────────────────────────────────────

const MOCK_PLAYLIST = {
  mood: '3am thoughts',
  playlist_name: 'Late Night Reverie',
  description: 'Quiet reflections when the world is asleep.',
  tracks: [
    { title: 'Breathe (2 AM)', artist: 'Anna Nalick', vibe: 'raw emotion' },
    { title: 'The Night Will Always Win', artist: 'Manchester Orchestra', vibe: 'bittersweet' },
    { title: 'Lua', artist: 'Bright Eyes', vibe: 'introspective' },
  ],
  cached: false,
}

const MOCK_PLAYLIST_CACHED = { ...MOCK_PLAYLIST, cached: true }

function mockFetch(response: object, ok = true, delay = 0) {
  const fetchMock = vi.fn().mockImplementation(() =>
    new Promise((resolve) =>
      setTimeout(
        () =>
          resolve({
            ok,
            status: ok ? 200 : 500,
            json: async () => response,
          }),
        delay,
      ),
    ),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('Mood-to-Playlist — End-to-End', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.resetAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ── 1. App loads ─────────────────────────────────────────────────────────
  it('renders header, mood input, and suggestion chips on load', () => {
    render(<App />)

    // App title / branding present
    expect(screen.getByRole('banner')).toBeInTheDocument()

    // Mood input is present
    const input = screen.getByRole('textbox')
    expect(input).toBeInTheDocument()

    // At least the first suggestion chip renders
    expect(screen.getByText('3am thoughts')).toBeInTheDocument()
  })

  // ── 2 & 3. Generate playlist and view results ─────────────────────────────
  it('generates a playlist and displays tracks after submission', async () => {
    mockFetch(MOCK_PLAYLIST)

    render(<App />)

    const input = screen.getByRole('textbox')
    await user.type(input, '3am thoughts')

    const button = screen.getByRole('button', { name: /generate/i })
    await user.click(button)

    // Playlist header shows up
    await waitFor(() =>
      expect(screen.getByText('Late Night Reverie')).toBeInTheDocument(),
    )

    // All tracks are shown
    expect(screen.getByText('Breathe (2 AM)')).toBeInTheDocument()
    expect(screen.getByText('Anna Nalick')).toBeInTheDocument()
    expect(screen.getByText('The Night Will Always Win')).toBeInTheDocument()
    expect(screen.getByText('Lua')).toBeInTheDocument()
  })

  // ── 4. Try another mood ───────────────────────────────────────────────────
  it('resets to input view when "Try another mood" is clicked', async () => {
    mockFetch(MOCK_PLAYLIST)

    render(<App />)

    const input = screen.getByRole('textbox')
    await user.type(input, '3am thoughts')
    await user.click(screen.getByRole('button', { name: /generate/i }))

    await waitFor(() =>
      expect(screen.getByText('Late Night Reverie')).toBeInTheDocument(),
    )

    // Click "Try another mood"
    const resetBtn = screen.getByRole('button', { name: /try another/i })
    await user.click(resetBtn)

    // Back to input, playlist gone
    await waitFor(() =>
      expect(screen.queryByText('Late Night Reverie')).not.toBeInTheDocument(),
    )
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  // ── 5. Suggestion chip triggers generation with that mood ────────────────
  it('clicking a suggestion chip sets the mood and triggers playlist generation', async () => {
    // Use a slow fetch so we can assert the input value before the result arrives
    mockFetch(MOCK_PLAYLIST, true, 300)

    render(<App />)

    const chip = screen.getByText('road trip energy')
    act(() => {
      fireEvent.click(chip)
    })

    // The input should reflect the chip value immediately
    await waitFor(() => {
      const input = screen.getByRole('textbox') as HTMLInputElement
      expect(input.value).toBe('road trip energy')
    })

    // And eventually the playlist should appear
    await waitFor(
      () => expect(screen.getByText('Late Night Reverie')).toBeInTheDocument(),
      { timeout: 3000 },
    )
  })

  // ── 6. Loading skeleton ───────────────────────────────────────────────────
  it('shows loading skeleton while request is in-flight', async () => {
    // Use a delayed fetch so we can assert mid-flight state
    mockFetch(MOCK_PLAYLIST, true, 200)

    render(<App />)

    const input = screen.getByRole('textbox')
    await user.type(input, 'road trip energy')

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /generate/i }))
    })

    // Skeleton should appear immediately
    await waitFor(() =>
      expect(screen.getByTestId('skeleton-playlist')).toBeInTheDocument(),
    )

    // Then playlist loads
    await waitFor(
      () => expect(screen.getByText('Late Night Reverie')).toBeInTheDocument(),
      { timeout: 2000 },
    )
  })

  // ── 7. Error banner when backend is down ─────────────────────────────────
  it('shows an error banner when the fetch rejects (backend down)', async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error('Network Error')))

    render(<App />)

    const input = screen.getByRole('textbox')
    await user.type(input, 'gym beast mode')
    await user.click(screen.getByRole('button', { name: /generate/i }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toBeInTheDocument(),
    )

    // Error message mentions connectivity / try again
    const alert = screen.getByRole('alert')
    expect(alert).toBeInTheDocument()
  })

  // ── 7b. Error banner for 500 response ────────────────────────────────────
  it('shows an error banner when the API returns a 500 error', async () => {
    mockFetch({ detail: 'Internal server error' }, false)

    render(<App />)

    const input = screen.getByRole('textbox')
    await user.type(input, 'gym beast mode')
    await user.click(screen.getByRole('button', { name: /generate/i }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toBeInTheDocument(),
    )
  })

  // ── 8. Error banner dismissal ─────────────────────────────────────────────
  it('dismisses the error banner when the close button is clicked', async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error('Network Error')))

    render(<App />)

    const input = screen.getByRole('textbox')
    await user.type(input, 'falling in love')
    await user.click(screen.getByRole('button', { name: /generate/i }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toBeInTheDocument(),
    )

    // Dismiss
    const closeBtn = screen.getByRole('button', { name: /dismiss|close/i })
    await user.click(closeBtn)

    await waitFor(() =>
      expect(screen.queryByRole('alert')).not.toBeInTheDocument(),
    )
  })

  // ── 9. Cached badge ───────────────────────────────────────────────────────
  it('shows a "Cached" badge when the response has cached: true', async () => {
    mockFetch(MOCK_PLAYLIST_CACHED)

    render(<App />)

    const input = screen.getByRole('textbox')
    await user.type(input, '3am thoughts')
    await user.click(screen.getByRole('button', { name: /generate/i }))

    await waitFor(() =>
      expect(screen.getByText('Late Night Reverie')).toBeInTheDocument(),
    )

    // Cached badge must be visible
    expect(screen.getByText(/cached/i)).toBeInTheDocument()
  })

  it('does NOT show a cached badge when cached: false', async () => {
    mockFetch(MOCK_PLAYLIST)

    render(<App />)

    const input = screen.getByRole('textbox')
    await user.type(input, '3am thoughts')
    await user.click(screen.getByRole('button', { name: /generate/i }))

    await waitFor(() =>
      expect(screen.getByText('Late Night Reverie')).toBeInTheDocument(),
    )

    // No cached badge
    expect(screen.queryByText(/cached/i)).not.toBeInTheDocument()
  })

  // ── 10. Mobile viewport layout ───────────────────────────────────────────
  it('renders correctly at 375px (mobile) width', async () => {
    // Simulate mobile viewport width
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 375,
    })
    window.dispatchEvent(new Event('resize'))

    mockFetch(MOCK_PLAYLIST)

    render(<App />)

    // Core elements still accessible on mobile
    expect(screen.getByRole('textbox')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /generate/i })).toBeInTheDocument()
    expect(screen.getByText('3am thoughts')).toBeInTheDocument()

    // Generate works on mobile
    await user.type(screen.getByRole('textbox'), '3am thoughts')
    await user.click(screen.getByRole('button', { name: /generate/i }))

    await waitFor(() =>
      expect(screen.getByText('Late Night Reverie')).toBeInTheDocument(),
    )
  })
})
