# EDT Frontend - Employment Schedule Management System

A modern React + Vite frontend application for managing university class schedules with role-based access control (Responsable, Enseignant, Étudiant).

## Stack

- **React 19** - UI library
- **Vite** - Build tool & dev server
- **React Router v7** - Routing
- **TanStack Query v5** - Server state management
- **Zustand** - Client state management (auth)
- **Axios** - HTTP client with JWT interceptors
- **Tailwind CSS 3** - Styling
- **shadcn/ui** - Component library
- **ESLint** - Code linting

## Project Structure

```
src/
├── api/                    # API layer
│   ├── client.js          # Axios instance with interceptors
│   └── auth.js            # Authentication endpoints
├── components/
│   └── ui/                # shadcn UI components
│       ├── button.jsx
│       ├── card.jsx
│       ├── input.jsx
│       └── label.jsx
├── features/
│   └── auth/
│       └── LoginPage.jsx  # Login form
├── lib/
│   ├── constants.js       # Business logic constants (roles, statuses)
│   └── utils.js           # Utility functions
├── routes/
│   ├── index.jsx          # Router configuration
│   └── ProtectedRoute.jsx # Role-based route guard
├── store/
│   └── authStore.js       # Zustand auth state
├── App.jsx                # Root component
├── main.jsx               # Entry point
└── index.css              # Global styles + Tailwind directives
```

## Quick Start

### 1. Setup Project Structure

**Option A: Automatic (Windows)**
```bash
./setup.bat
```

**Option B: Manual (Any OS)**
```bash
npm run setup
```

This creates all directories and files in their correct locations.

### 2. Install Dependencies

```bash
npm install
```

### 3. Configure Environment

Copy `.env.example` to `.env` and update as needed:
```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

### 4. Start Development Server

```bash
npm run dev
```

The app runs on `http://localhost:3000`

## Features

### Authentication
- JWT-based login with access/refresh token flow
- Automatic token refresh on 401 responses
- Persistent auth state (localStorage)
- Role-based redirects (Responsable → `/responsable/planning`, etc.)

### Role-Based Access Control
- **Responsable**: Schedule management dashboard
- **Enseignant**: Teaching schedule view
- **Étudiant**: Personal schedule view

### API Integration
- Centralized Axios client with Bearer token injection
- Automatic JWT refresh on token expiration
- Request/response error handling
- Baseencoded state management

### UI/UX
- Dark mode support (Tailwind)
- shadcn/ui components (Card, Button, Input, Label)
- HSL-based color system for flexible theming
- Responsive design ready

## Development

### Build

```bash
npm run build
```

### Lint

```bash
npm lint
```

### Preview

```bash
npm run preview
```

## Configuration Files

- **vite.config.js** - Vite bundler & API proxy config
- **tailwind.config.js** - Tailwind theme & content paths
- **jsconfig.json** - JS path aliases (@/src)
- **postcss.config.js** - PostCSS plugins for Tailwind
- **.env** - Environment variables (local)
- **.env.example** - Environment variables template

## Backend Integration

This frontend expects a Django REST Framework backend with:

- `/api/token/` - Login endpoint (POST)
  - Request: `{ username, password }`
  - Response: `{ access, refresh, user }`

- `/api/token/refresh/` - Refresh token endpoint (POST)
  - Request: `{ refresh }`
  - Response: `{ access }`

## Next Steps

1. Implement responsive components for each role dashboard
2. Add form validation & mutations (TanStack Query)
3. Create planning/schedule display components
4. Add data fetching queries for schedules
5. Implement state synchronization with backend

---

**Created with ❤️ for EDT Université**

