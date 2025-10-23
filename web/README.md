# BioMind Web (Next.js)

A new React/Next.js web app that replaces the previous Streamlit UI. It mirrors the Collections-first UX with Agents and a Search page shell.

## Stack
- Next.js 14 (App Router)
- React 18 + TypeScript
- Tailwind CSS (preconfigured)

## Development
1. Install Node 18+ (or use nvm)
2. Install deps
   - npm install
3. Run dev server
   - npm run dev
4. App runs at http://localhost:3000

## Backend wiring
- Set `NEXT_PUBLIC_API_BASE` to your FastAPI base URL (e.g. http://localhost:8000)
- See `lib/api.ts` for a starting client; extend with your endpoints

## Pages
- /search — Search shell (segmented control, query box, advanced)
- /collections — Collections list (create CTA + rows)
- /collections/[name] — Collection detail with Add overlay
- /agents — Agents gallery (coming soon)

## Note
This is an initial scaffold. We’ll iterate to:
- Bind pages to real API endpoints (RAG search, collections CRUD)
- Add polished components (shadcn/ui), icons, and toasts
- Implement auth if needed