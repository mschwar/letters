### 1. PRD.md (Product Requirements Document)

codeMarkdown

```
# Product Requirements Document (PRD): Bahá’í Guidance Engine

## 1. Executive Summary
The Bahá’í Guidance Engine is a local-first, "Docs-as-Code" knowledge management system designed to ingest, process, store, and semantically search letters from the Universal House of Justice. It replaces physical binders and static PDFs with a living, searchable Knowledge Graph.

## 2. Target Audience
*   **Primary User:** Tech-savvy Bahá’í researchers, archivists, or institution members.
*   **Needs:** Rapid access to specific guidance, thematic correlation across decades, and offline availability.

## 3. Core Philosophy
*   **Docs-as-Code:** The "Database" is a Git repository of Markdown files with YAML frontmatter.
*   **Local Sovereignty:** No cloud dependencies for storage. The user owns the data.
*   **Semantic Intelligence:** Search is based on meaning (vectors), not just keywords.

## 4. In Scope Features

### 4.1. Ingestion Pipeline (ETL)
*   **Trigger:** Automated detection of new PDF files in an `/inbox` directory.
*   **Processing:**
    *   **OCR:** Extract text from PDFs.
    *   **Metadata Extraction (AI):** Automatically identify Date, Recipient, and Source.
    *   **Summarization (AI):** Generate a 1-sentence summary and 3-5 thematic tags.
    *   **Conversion:** Save as Markdown with standardized YAML frontmatter.
    *   **Archival:** Move original PDF to `/archive/YYYY/`.

### 4.2. Knowledge Base (Storage)
*   **Format:** Markdown files stored in `/content/messages/YYYY/`.
*   **Schema:** Strict YAML frontmatter (see BACKEND_STRUCTURE.md).
*   **Versioning:** Git-based history.

### 4.3. User Interface (Frontend)
*   **Library View:** Chronological list of messages with filters (Date, Recipient, Tags).
*   **Reader View:** Distraction-free reading mode with typography optimized for long-form text.
*   **Smart Search:**
    *   Keyword search (fuzzy matching).
    *   Semantic Question/Answer (RAG) - e.g., "What is the guidance on the junior youth program?"

## 5. Out of Scope
*   Mobile Native App (Responsive Web App only).
*   User Authentication (Local tool, single user assumed).
*   Cloud Sync (Assumed handled by user's OS/Dropbox/iCloud).

## 6. Success Criteria
*   **Accuracy:** Extracted dates must be ISO 8601 compliant.
*   **Speed:** Search results return in <200ms.
*   **latency:** Ingestion of a new PDF takes <10 seconds.
*   **Legibility:** Reader view scores 95+ on accessibility/readability metrics.
```

---

### 2. APP_FLOW.md

codeMarkdown

```
# App Flow & Navigation

## 1. The Ingestion Flow (Background Process)
1.  **User Action:** User drops `Letter.pdf` into `./inbox` folder.
2.  **System Action:** Python watcher detects file event.
3.  **Process:**
    *   Extract Text.
    *   **Decision Point:** Is text readable?
        *   *Yes:* Proceed.
        *   *No:* Run OCR -> Proceed.
    *   Send text to LLM for Metadata extraction.
    *   Generate Markdown file.
    *   Generate Vector Embeddings -> Add to ChromaDB.
4.  **Outcome:** `Letter.pdf` moved to `./archive`. New `.md` file appears in Library.

## 2. The Reading Flow (UI)
1.  **Home / Dashboard:**
    *   Displays "Recent Messages" (Last 3 months).
    *   Displays "Statistics" (Total letters, top tags).
2.  **Library Route (`/library`):**
    *   User sees a paginated table of all letters.
    *   **Action:** User filters by "Tag: Education".
    *   **System:** Updates list.
    *   **Action:** User clicks a Letter Title.
3.  **Reader Route (`/message/[id]`):**
    *   Displays full Markdown content.
    *   **Sidebar:** Shows Metadata (Date, Recipient) and "Linked Messages" (Backlinks).
    *   **Action:** User clicks a [[WikiLink]].
    *   **Transition:** Navigates to the linked message.

## 3. The Search Flow (RAG)
1.  **Search Modal (`Cmd+K`):**
    *   User types natural language query: "How do we handle funds?"
2.  **System Processing:**
    *   Vectorizes query.
    *   Queries ChromaDB for top 5 chunks.
    *   Sends chunks + query to LLM to synthesize answer.
3.  **Results Display:**
    *   Shows "AI Summary" (The synthesized answer).
    *   Shows "Source Citations" (Cards linking to specific paragraphs in the Markdown files).
```

---

### 3. TECH_STACK.md

codeMarkdown

```
# Tech Stack & Dependencies

## 1. Core Framework
*   **Runtime:** Node.js v20.x (LTS)
*   **Frontend:** Next.js 14.1.0 (App Router)
*   **Language:** TypeScript 5.3.3 (Strict Mode)

## 2. UI & Styling
*   **Styling:** Tailwind CSS 3.4.1
*   **Typography:** `@next/font` (Inter for UI, Merriweather for Content)
*   **Components:** Radix UI Primitives (via shadcn/ui latest)
*   **Icons:** Lucide React 0.300.0
*   **Markdown Renderer:** `react-markdown` 9.0.1 + `remark-gfm` + `rehype-raw`

## 3. Backend & Data (Local)
*   **Scripting (ETL):** Python 3.11
*   **Python Libraries:**
    *   `langchain` (Orchestration)
    *   `pypdf` (PDF Parsing)
    *   `watchdog` (File system events)
    *   `chromadb` (Vector Store) - Running locally
*   **LLM Interface:** `openai` (Python SDK) - Connecting to OpenAI API (MVP) or Local `ollama` endpoint.

## 4. Data Structure
*   **Primary DB:** The File System (`.md` files).
*   **Vector DB:** ChromaDB (Persisted to `./data/chroma`).

## 5. Development Tools
*   **Linting:** ESLint + Prettier
*   **Package Manager:** pnpm
```

---

### 4. FRONTEND_GUIDELINES.md

codeMarkdown

```
# Frontend Design Guidelines

## 1. Visual Philosophy
*   **Tone:** Dignified, Serene, Academic, Official.
*   **Metaphor:** " The Archivist's Desk." Clean paper, clear ink, minimal distractions.

## 2. Color Palette
*   **Backgrounds:**
    *   `bg-stone-50` (#fafaf9) - Main app background (Paper-like).
    *   `bg-white` (#ffffff) - Cards and Reading surfaces.
*   **Text:**
    *   `text-slate-900` - Primary headers.
    *   `text-slate-700` - Body text (High readability).
    *   `text-slate-500` - Metadata/Subtitles.
*   **Accents:**
    *   `text-indigo-900` - Primary Brand (Deep Royal Blue).
    *   `text-amber-600` - Highlights/Links (Gold/Tan).

## 3. Typography
*   **Headings:** `Inter` (Sans-serif). Bold, tracking-tight.
    *   H1: text-3xl, font-bold, text-slate-900.
    *   H2: text-xl, font-semibold, text-indigo-900.
*   **Body:** `Merriweather` or `Libre Baskerville` (Serif).
    *   Size: text-lg (18px).
    *   Line-height: leading-relaxed (1.75).
    *   Max-width: max-w-prose (65ch).

## 4. Component Rules
*   **Cards:** Minimalist. Thin border (`border-stone-200`), subtle shadow (`shadow-sm`). Hover: `shadow-md`, `border-indigo-100`.
*   **Buttons:**
    *   Primary: `bg-indigo-900` text-white rounded-md.
    *   Secondary: `bg-white` border `border-stone-300` text-slate-700.
*   **Tags:** Pill shape, `bg-stone-100`, `text-stone-600`, text-xs uppercase tracking-wide.

## 5. Layout
*   **Sidebar:** Fixed left (Desktop), Collapsible (Mobile).
*   **Main Content:** Centered container, max-width 1200px.
```

---

### 5. BACKEND_STRUCTURE.md

codeMarkdown

````
# Backend & Data Structure

## 1. The File Schema (Markdown Frontmatter)
Every canonical document in `/content/messages/` MUST adhere to this Zod schema:

```yaml
---
id: "UUID-v4" or "YYYY-MM-DD-slug"
title: "String (e.g., To the Conference of Counsellors)"
date: "YYYY-MM-DD" (ISO 8601)
source: "Universal House of Justice" | "International Teaching Centre"
recipient: "Bahá’ís of the World" | "Counsellors" | "NSAs"
tags: ["Array", "of", "Strings"]
summary: "One sentence string."
related_ids: ["Array", "of", "IDs"]
original_pdf_path: "/archive/2026/file.pdf"
---
````

## 2. Vector Store Schema (ChromaDB)

- **Collection Name:** guidance_vectors
    
- **Metadata Fields:** source_id, date, tags (allows filtering search results before semantic ranking).
    
- **Embedding Model:** text-embedding-3-small (OpenAI) or nomic-embed-text (Local).
    

## 3. API Routes (Next.js)

- GET /api/messages: Returns list of messages (reads frontmatter only).
    
    - Query Params: limit, tag, year.
        
- GET /api/messages/[slug]: Returns full markdown content.
    
- POST /api/search:
    
    - Body: { query: string }
        
    - Returns: { answer: string, sources: Array<Chunk> }
        

## 4. Python ETL Scripts (/scripts)

- ingest.py:
    
    1. Scans /inbox.
        
    2. Parses PDF.
        
    3. Calls LLM for extraction.
        
    4. Writes .md file.
        
    5. Updates Vector DB.
        

codeCode

````
---

### 6. IMPLEMENTATION_PLAN.md

```markdown
# Implementation Plan

## Phase 1: Foundation
- [ ] 1.1 Initialize Git Repo & Next.js Project (Typescript, Tailwind).
- [ ] 1.2 Configure Folder Structure (`/content`, `/inbox`, `/archive`, `/scripts`).
- [ ] 1.3 Install Frontend Dependencies (shadcn/ui, lucide, react-markdown).
- [ ] 1.4 Create `GlobalLayout` and Apply Typography/Colors per Guidelines.

## Phase 2: The Data Layer (ETL)
- [ ] 2.1 Set up Python Virtual Environment & Install `langchain`, `pypdf`, `chromadb`.
- [ ] 2.2 Write `scripts/parse_pdf.py` (Text extraction logic).
- [ ] 2.3 Write `scripts/extract_metadata.py` (LLM connection).
- [ ] 2.4 Create 5 Sample Markdown files manually to test schema.
- [ ] 2.5 Build `ingest.py` to automate the pipeline from Inbox to Content.

## Phase 3: The Library UI
- [ ] 3.1 Build `lib/messages.ts` (Node.js utility to read/parse Frontmatter).
- [ ] 3.2 Create `/library` page (Data Table/Grid of messages).
- [ ] 3.3 Create `/message/[slug]` page (Markdown Rendering).
- [ ] 3.4 Implement "Tag" filtering logic.

## Phase 4: Intelligence (RAG)
- [ ] 4.1 Implement Vector Upsert logic in `ingest.py`.
- [ ] 4.2 Create `api/search` route (Query ChromaDB + LLM Synthesis).
- [ ] 4.3 Build "Search Modal" UI (Command Palette style).
- [ ] 4.4 Connect UI to API and display citations.

## Phase 5: Polish
- [ ] 5.1 Add "Copy Citation" button to text selection.
- [ ] 5.2 Mobile Responsiveness Check.
- [ ] 5.3 Write README.md with usage instructions.
````

---

### 7. PERSISTANT.md (The AI Context Layer)

codeMarkdown

```
# PERSISTENT CONTEXT
**READ THIS FILE FIRST.**

## Project Identity
You are building the "Bahá’í Guidance Engine." It is a Docs-as-Code knowledge management system. 
**Core Value:** Robustness, Accuracy, Dignity.

## Operational Rules
1.  **Tech Stack Adherence:** You MUST use Next.js 14 (App Router), TypeScript, Tailwind, and Python for scripts. Do not suggest other frameworks.
2.  **File Structure:**
    *   Frontend code lives in `/app` and `/components`.
    *   Content lives in `/content/messages`.
    *   ETL logic lives in `/scripts`.
3.  **Type Safety:** NO `any` types. All data interfaces must be defined in `/types`.
4.  **Styling:** Use Tailwind utility classes. Do not create CSS modules unless absolutely necessary.
5.  **Data Integrity:** The Markdown file is the Single Source of Truth. The Vector DB is a derivative index. If they conflict, the Markdown wins.

## Naming Conventions
*   **Files:** `kebab-case.ts` (e.g., `message-card.tsx`).
*   **Components:** `PascalCase` (e.g., `MessageCard`).
*   **Functions:** `camelCase` (e.g., `parseFrontmatter`).
*   **Content Files:** `YYYY-MM-DD-slug.md`.

## Forbidden Patterns
*   Do not hardcode content. All text must come from the Markdown files.
*   Do not use client-side fetching for static content. Use Server Components (`fs` operations) for the Library view.
```

---

### 8. progress.txt

codeText

```
# Project Progress Tracker

## Status: NOT STARTED

## Current Task
- Initialize project structure.

## Backlog
- [ ] Phase 1: Foundation
- [ ] Phase 2: ETL Pipeline
- [ ] Phase 3: Library UI
- [ ] Phase 4: RAG Search
- [ ] Phase 5: Polish

## Session Notes
- [DATE]: Canonical documents created. Ready for initialization.
```