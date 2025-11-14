# Frontend TODO (API Coverage Gap Analysis)

Generated: 2025-11-13

## Legend
- [ ] Not started
- [~] In progress / partial
- [x] Implemented

## Backend API Surface vs Frontend Implementation

### Core & Utility
- GET /api/v1/health — [x] Used in `home_page` health query.
- POST /api/v1/webhooks/run-status (register run-status webhook) — [x] UI implemented (Register Webhook button) using field `webhook_run_status_url`.

### Projects
- POST /api/v1/projects — [x] Create form (`project_create_page`) with optimistic add.
- GET /api/v1/projects — [x] Listing with search & pagination.
- GET /api/v1/projects/{id} — [x] Detail view (`project_detail_page`).
- PUT /api/v1/projects/{id} — [x] Edit (optimistic update + owner reassignment confirmation).
- DELETE /api/v1/projects/{id} — [x] Delete with confirm + toast.

### API Keys (Project-scoped)
- GET /api/v1/projects/{project_id}/api-keys — [x] List page implemented (OWNER-only; masked output without plaintext).
- POST /api/v1/projects/{project_id}/api-keys — [x] Creation modal implemented; shows plaintext once via ephemeral alert.
- DELETE /api/v1/projects/{project_id}/api-keys/{key_id} — [x] Revoke action with confirm & toast.

### Sources
Implemented subset (upload + schema/table fetch) and new enhancements.
- POST /api/v1/projects/{project_id}/sources — [x] Upload implemented (DDL & JSON). Dialect selection added; error states displayed.
- GET /api/v1/projects/{project_id}/sources — [x] Sources list page implemented (backend list endpoint live; shows kind, created_at, tables_count). Pagination TBD.
- GET /api/v1/projects/{project_id}/sources/{source_id} — [x] Schema view implemented (falls back to /tables when needed).
- GET /api/v1/projects/{project_id}/sources/{source_id}/dag — [x] DAG visualization implemented (ReactFlow with auto layout).
- GET /api/v1/projects/{project_id}/sources/{source_id}/tables — [x] Used as fallback for schema.

### Requests (Synthetic Generation)
- POST /api/v1/projects/{project_id}/requests — [x] createRequest used in wizard run step.
- GET /api/v1/projects/{project_id}/requests — [x] Requests list/history page implemented with status badges, search, pagination.
- GET /api/v1/projects/{project_id}/requests/{request_id} — [x] request detail page present.
- POST /api/v1/projects/{project_id}/requests/{request_id}:estimate — [x] estimateRequest used.
- POST /api/v1/requests/{request_id}:start — [x] startRequest invoked.

### Artifacts
- GET /api/v1/requests/{request_id}/artifacts — [x] listArtifacts used.
- GET /api/v1/requests/{request_id}/artifacts/{artifact_id} — [x] Artifact download via "Get Signed URL" action on request detail page.
- GET /api/v1/requests/{request_id}/artifacts/{artifact_id}:sign (compat via colon) — [x] Integrated; opens signed URL in a new tab with fallback to storage_uri.

### Flat Preview & Jobs
- POST /api/v1/flat/preview — [x] UI preview pane wired (`FlatPreviewPage` with JSON editor and rows table).

### Validate Rules
- POST /api/v1/validate — [x] Rule builder UI and report rendering implemented (sample vs final toggle via "Sample Only").

### Provider Inference
- POST /api/v1/projects/{project_id}/infer/providers — [x] Used (`providers.ts` inferProviders).
- POST /api/v1/infer/providers — [x] Non-scoped alias wired (used as fallback when projectId is absent).

### LLM Settings (Project)
- GET /api/v1/projects/{project_id}/llm-settings — [x]
- PUT /api/v1/projects/{project_id}/llm-settings — [x]

### LLM Admin
- GET /api/v1/admin/llm/providers — [x]
- POST /api/v1/admin/llm/providers — [x]
- PATCH /api/v1/admin/llm/providers/{provider_id} — [x]
- POST /api/v1/admin/llm/providers/{provider_id}/credentials — [x]
- GET /api/v1/admin/llm/providers/{provider_id}/models — [x]
- POST /api/v1/admin/llm/providers/{provider_id}/models — [x]
- POST /api/v1/admin/llm/providers/{provider_id}:probe — [x]
- POST /api/v1/admin/llm/providers/{provider_id}:discover-models — [x]
- Default model marking UX — [x] Implemented: "Discover Models" drawer lists models with a "Make Default" action; default badge shown and lists refresh after discover/mark.

### Auth & Users
// OIDC implemented (SSO button on login and callback page storing dev token); password-based flows also implemented
- GET /api/v1/auth/login (OIDC start) — [x] Used by SSO button on `login_page`.
- GET /api/v1/auth/callback — [x] OIDC callback page stores dev token; redirects with success toast.
- POST /api/v1/auth/register — [x] Registration page implemented (navigates to verify screen).
- POST /api/v1/auth/verify-email — [x] Verification page with OTP + resend + toasts.
- POST /api/v1/auth/login — [x] Login (success toast, email prefill support, role capture).
- POST /api/v1/auth/resend-email-otp — [x] Resend integrated on verify page.
- POST /api/v1/auth/forgot-password — [x] Forgot password request page.
- POST /api/v1/auth/reset-password — [x] Reset password page with OTP + new password.
- POST /api/v1/auth/change-password — [x] Change password page (protected).
- GET /api/v1/users/me — [x] Profile page fetches user (role, org, email).
- PATCH /api/v1/users/me/avatar — [x] Avatar upload implemented.

### Admin Users
- GET /api/v1/admin/users — [x] Admin user approval dashboard implemented.
- POST /api/v1/admin/users/{user_id}/approve — [x] Approve action wired.
- POST /api/v1/admin/users/{user_id}/reject — [x] Reject action wired.

### Webhooks
- POST /api/v1/webhooks/run-status — [x] Configuration & register/update button on project detail; stored in `webhook_run_status_url`.

## Prioritized TODOs
Ordered by impact & dependency.
1. Project Management UI
   - [x] Create project form (name, owner, optional run-status webhook URL) w/ optimistic cache update.
   - [x] Detail & edit (rename, run-status webhook field, delete confirm + toasts, optimistic update, owner change confirmation, webhook register button).
2. API Keys Management
   - [x] List keys (masked) with scopes.
   - [x] Create key modal (name + scopes multi-select) displaying plaintext once.
   - [x] Revoke key action (confirmation dialog).
3. Auth Flows Expansion
   - [x] Registration page (email, org, password; success leads to verify screen).
   - [x] Email verification screen (OTP input + resend). 
   - [x] Forgot/reset password sequence (request → OTP → new password).
   - [x] Change password panel (current pwd or OTP path).
   - [x] Profile page using /users/me with avatar upload.
4. Admin User Approval
   - [x] Admin dashboard showing pending users with approve/reject actions.
5. Sources Enhancements
   - [x] DAG visualization using /dag endpoint (ReactFlow integration).
   - [x] Source list/history per project (shows uploaded files, timestamps, tables_count). Pagination & filtering TBD.
6.  Requests& Artifacts
   - [x] Requests list/history page (status badges, last run times).
   - [x] Artifact detail/download (signed URL fetch; add "Get Signed URL" button).
   - [x] Signed URL integration for CSV/Parquet/XLSX/JSONL.
7. Validation Rules UI
   - [x] Rule builder form for uniqueness, implication, distribution, temporal.
   - [x] Preview validation report rendering (sample vs final).
8. Flat Preview
   - [x] UI pane for POST /flat/preview (schema JSON editor + first 100 rows table).
9. Provider Suggestions UX
   - [x] Improve provider suggestions display (confidence, manual override diff highlighting).
   - [x] Per-row "Apply suggestion" action with confidence badge.
   - [x] Inline "Why this suggestion?" popover next to suggested provider.
   - [x] Compact summary banner after suggest run (X provider changes, Y PII updates).
   - [x] Per-row "Overwrites manual" hint when suggestion replaces existing provider/config.
   - [ ] Persist provider configs fully (backend PUT providers endpoint forthcoming) — adjust once API stable.
10. LLM Model Default UX
   - [x] Mark default model via Discover and inline models list; default badge and Default Model column.
   - Enhancements backlog:
      1. [x] Default toggle inline (radio-style)
    2. [x] Confirm default changes (optional dialog)
      3. [x] Success/error toasts on mark default
     4. [x] Show default in providers list (Default Model column)
      5. [x] Refresh models in-place (per-provider)
     6. [x] “No models” CTA (with Discover action and credentials hint)
     7. [x] Filters and sort in models table (chat/json/context)
   8. [x] Model metadata popover (context, json, provider-specific)
   9. [x] Inline edit of display name
       10. [x] Newly discovered/updated badge after discover
     11. [ ] Default-by-task type (chat/embeddings/tools) if supported
       12. [x] Project LLM Settings: “Use provider default” shortcut
     13. [x] RBAC cues (hide/disable actions for non-OWNER with tooltip)
       14. [x] Rate-limit/network error UX with backoff
     15. [x] Optimistic default switch with revert on failure
     16. [x] Persist Show Models expansion state per provider
       17. [x] Keyboard and a11y improvements (aria-live, focus)
        - [x] Added aria-live status updates for default change and loading
       18. [~] Audit and metrics surface (recent default changes) — lightweight "Last change" text added
   19. [x] Backend PATCH endpoint to set default explicitly
   20. [x] Default uniqueness enforcement (DB/server guard)
   21. [x] Denormalized default on provider (default_model_id)
      22. [x] Test coverage additions (inline + drawer parity)
   23. [x] Skeleton/loading polish for models and default cell (aria-busy + placeholder during loading/marking)
     24. [x] Discover progress feedback (long operations)
       25. [x] Documentation: Default model workflow
11. OIDC (Optional Phase)
   - [x] OIDC login start redirect & callback handler storing token.
12. Webhook Configuration
   - [x] Run-status webhook URL field + Register Webhook button invoking POST /webhooks/run-status.

## Cross-Cutting Improvements
- [x] Central error boundary + global toast system.
- [x] Loading skeletons (Profile & Verify Email, requests list, and providers discovery done; default cell polish tracked under LLM item 23).
- [x] Rate-limit feedback banner for infer providers (handle 429 gracefully).
- [x] Access control UI (hide OWNER-only LLM Providers link; extend later for ADMIN).

## Acceptance Criteria Examples
- Project Create: Submitting valid name & owner updates list within 1s; duplicate name shows backend 400 message inline.
- API Key Create: Newly created key shows plaintext only once; subsequent view hides plaintext; scopes rendered as badges.
- Registration Flow: User registers, receives verification prompt; OTP error states (invalid, expired) displayed; success transitions to login.
- DAG View: Renders all tables/nodes with FK edges; missing tables or API errors produce inline retry option.
- Requests History: Shows latest 20 requests with status filter and auto-refresh every 10s while any are running.

## Tracking & Ownership
Assign owners once team roles are confirmed:
| Area | Tentative Owner |
|------|-----------------|
| Auth flows | Frontend Lead |
| API Keys | Security/Platform |
| Projects UI | Core UX |
| Requests/Artifacts | Data Gen Team |
| Sources DAG | Data Model Engineer |
| Validation Rules | Quality/Testing |
| LLM Admin Enhancements | AI Integrations |
| Admin User Approval | Ops/Admin |

## Deferred / Optional
- [x] Non-scoped infer alias usage (/infer/providers) — wired as fallback when projectId missing.
- [x] Advanced artifacts filtering (format/date range) — client-side filters on Request Detail page.
- [ ] Real-time job progress via WebSocket instead of polling.

## Done / Implemented Snapshot
- Health check display
- Basic login (password) & route guard
- Wizard flow (entities -> providers -> rules -> outputs -> run) partial
- LLM providers & settings management (CRUD, credentials, models, probe, discover)
- Provider inference integration
- Request creation, start, estimate, detail view
- Artifacts list (basic)
- Full password-based auth suite (register, verify email + resend, forgot, reset, change password)
- Profile page with avatar upload
- Role capture & owner-only navbar link
- Global toast notifications & success/error/info messaging
- Central ErrorBoundary fallback
- Email prefill on login via query parameter
-- Skeleton loaders (initial pages)
-- Optimistic project create/update
-- Run-status webhook configuration & registration

---
Generated automatically. Update this file as features land; keep sections synchronized with backend changes.
