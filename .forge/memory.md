# Mood-to-Playlist — Project Memory

## Overview
AI-powered mood-to-playlist generator. User types a mood/situation, gets a Spotify-style playlist with song names, artists, and vibe descriptions. No auth needed.

## Monorepo Structure
- `/backend` — FastAPI Python app (port 8000)
- `/frontend` — React + TypeScript (Vite, port 5173)

## Backend
- Entry: `backend/main.py`
- Deps: fastapi, uvicorn, pydantic, httpx, redis, openai, python-dotenv
- Run: `cd backend && uvicorn main:app --reload --port 8000`

## Frontend
- Scaffolded with `npm create vite@latest . -- --template react-ts`
- Run: `cd frontend && npm install && npm run dev`
- Port: 5173

## Environment
- `backend/.env` needs: OPENAI_API_KEY, REDIS_URL
