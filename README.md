# SkillSync Frontend

SkillSync is a cloud-based learning analytics platform designed to help students better understand their academic performance and receive AI-generated study support.

This repository contains the frontend application for the SkillSync platform.

The repository also contains backend-related resources and integration materials.  
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

---

# Current Frontend Features

## Global Layout
- Responsive application shell
- Sidebar navigation
- Shared page layout
- Consistent page styling

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

# Tech Stack

## Frontend
- Next.js
- React
- TypeScript
- CSS

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
│   └── ProfileHeader.tsx
│
└── public/
    └── icons/
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
