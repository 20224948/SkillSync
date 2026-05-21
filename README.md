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
- Dynamic frontend integration with the hosted SkillSync backend API
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

- Multi-course learning analytics dashboard
- Current competency mastery overview
- Learning trend visualisation
- Strengths and improvement analysis
- Overall mastery score aggregation

## Study Plan

Displays:

- AI-generated study recommendations
- Multi-course revision planning
- Learning focus organisation

## Study Tips

Displays:

- AI-generated personalised study tips
- Course-specific learning guidance
- SILO-based recommendation grouping

## Adaptive Quiz

Displays:

- Adaptive revision quizzes
- Randomised question ordering
- Course-specific competency targeting
- Weak-area focused revision support

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
- Azure Static Web Apps

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
- Aggregating multi-course student analytics
- Displaying competency progression trends
- Rendering adaptive learning recommendations

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

# Deployment

The SkillSync frontend is hosted using Azure Static Web Apps with GitHub Actions CI/CD integration.

Frontend hosting platform:

- Azure Static Web Apps

Authentication and backend services:

- Supabase Authentication
- Hosted SkillSync backend API



