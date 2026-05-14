# SkillSync Frontend

SkillSync is a cloud-based learning analytics platform designed to help students better understand their academic performance and receive AI-generated study support.

This repository contains the frontend application for the SkillSync platform. The repository also contains backend-related resources and integration materials.

Backend-specific documentation is located within the `backend/` directory.

---

# Frontend Overview

The frontend is responsible for the student-facing experience of the SkillSync platform.

Current implemented pages:

- Dashboard
- Study Plan
- Study Tips
- Adaptive Quiz

The frontend currently provides:

- Global application layout
- Sidebar navigation
- Shared page structure
- Responsive interface design
- Static frontend integration structure for backend connectivity
- Supabase authentication integration
- Application-level session timeout handling

---

# Current Frontend Features

## Global Layout

- Responsive application shell
- Sidebar navigation
- Shared page layout
- Consistent page styling
- Mobile-responsive interface support

## Dashboard

Displays:

- Student dashboard interface
- Learning analytics layout
- Performance overview sections

## Study Plan

Displays:

- Study planning interface
- Revision structure layout
- Learning organisation sections

## Study Tips

Displays:

- Study tips interface
- Learning recommendation sections
- Revision guidance layout

## Adaptive Quiz

Displays:

- Adaptive quiz interface
- Quiz interaction layout
- Revision question sections

---

# Session Management

SkillSync implements application-level session timeout handling using Supabase Authentication and client-side activity tracking.

## Current Security Features

- Protected routes for authenticated users only
- Supabase Auth session management
- Automatic redirect after logout
- Application-level inactivity session timeout
- Token-based API authentication between frontend and backend

## Inactivity Timeout

To improve session security, SkillSync automatically signs users out after 20 minutes of inactivity.

User activity events monitored include:

- Mouse movement
- Keyboard input
- Mouse clicks
- Scrolling
- Touch interactions

If no activity is detected within the timeout period:

1. The current Supabase session is terminated
2. The user is redirected back to the login/landing page
3. Protected pages become inaccessible until authentication is restored

The timeout system is implemented globally through a shared `SessionTimeout` component integrated into the application layout.

---

# Tech Stack

## Frontend

- Next.js
- React
- TypeScript
- CSS
- Supabase Authentication

---

# Project Structure

```text
src/
│
├── app/
│   ├── dashboard/
│   ├── study-plan/
│   ├── study-tips/
│   ├── adaptive-quiz/
│   ├── globals.css
│   └── layout.tsx
│
├── components/
│   ├── Sidebar.tsx
│   ├── ProfileHeader.tsx
│   └── SessionTimeout.tsx
│
├── public/
│   └── icons/
│
└── app/lib/
    └── supabaseClient.ts
```

---

# Frontend Pages

| Route | Purpose |
|---|---|
| `/dashboard` | Main dashboard page |
| `/study-plan` | Study plan page |
| `/study-tips` | Study tips page |
| `/adaptive-quiz` | Adaptive quiz page |

---

# Installation

Clone the repository:

```bash
git clone https://github.com/20224948/SkillSync.git
```

Navigate into the project directory:

```bash
cd SkillSync
```

Install dependencies:

```bash
npm install
```

Run the development server:

```bash
npm run dev
```

The application will run on:

```text
http://localhost:3000
```

---

# Authentication and Backend Integration

SkillSync uses Supabase Authentication for user login and session management.

The frontend communicates with the hosted SkillSync backend API using bearer-token authentication.

The frontend is responsible for:

- Handling user authentication
- Managing authenticated sessions
- Rendering student learning analytics
- Displaying AI-generated study support
- Handling frontend routing and navigation
- Managing inactivity-based session termination

---

# Deployment

The frontend application is designed to be deployed as a cloud-hosted web application.

Current deployment considerations include:

- Azure frontend hosting
- Supabase authentication services
- Hosted backend API integration
- Moodle integration support
- Responsive browser compatibility
