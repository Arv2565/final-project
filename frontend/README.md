# Legal Assistant Frontend

Web UI for the AI Legal Assistant.

## Coming Soon

This directory is reserved for the frontend application.

## Recommended Stack

- **Framework**: Next.js 14 (App Router) or Vite + React
- **UI Library**: shadcn/ui with Tailwind CSS
- **State Management**: Zustand or Redux Toolkit  
- **API Client**: Axios or fetch with React Query/TanStack Query
- **WebSocket**: Socket.IO or native WebSocket API

## API Integration

The frontend will connect to the backend API:

- **Development**: `http://localhost:8000/api`
- **WebSocket**: `ws://localhost:8000/api/ws/chat`
- **Production**: TBD

## Quick Start (When Implemented)

```bash
cd frontend
npm install
npm run dev
```

## Features to Implement

- [ ] Chat interface for legal queries
- [ ] Real-time streaming responses via WebSocket
- [ ] Session management and history
- [ ] Document upload and analysis
- [ ] Multi-language support
- [ ] Responsive design (mobile, tablet, desktop)
- [ ] Dark mode support
