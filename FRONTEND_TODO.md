# Frontend TODO (API Coverage Gap Analysis)

Generated: 2025-11-10

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
- GET /api/v1/projects/{project_id}/api-keys — [ ] Missing UI.
- POST /api/v1/projects/{project_id}/api-keys — [ ] Missing creation flow.
- DELETE /api/v1/projects/{project_id}/api-keys/{key_id} — [ ] Missing revoke button.

### Sources
Implemented subset (upload + schema/table fetch).
- POST /api/v1/projects/{project_id}/sources — [~] Upload implemented (DDL & JSON). Need dialect selection UI polish & error states.
- GET /api/v1/projects/{project_id}/sources/{source_id} — [x] Fallback to /tables implemented.
- GET /api/v1/projects/{project_id}/sources/{source_id}/dag — [ ] No DAG visualization yet (backend endpoint exists).
- GET /api/v1/projects/{project_id}/sources/{source_id}/tables — [x] Used as fallback.

### Requests (Synthetic Generation)
- POST /api/v1/projects/{project_id}/requests — [x] createRequest used in wizard run step.
- GET /api/v1/projects/{project_id}/requests — [ ] Missing list/history view.
- GET /api/v1/projects/{project_id}/requests/{request_id} — [x] request detail page present.
- POST /api/v1/projects/{project_id}/requests/{request_id}:estimate — [x] estimateRequest used.
- POST /api/v1/requests/{request_id}:start — [x] startRequest invoked.

### Artifacts
- GET /api/v1/requests/{request_id}/artifacts — [x] listArtifacts used.
- GET /api/v1/requests/{request_id}/artifacts/{artifact_id} — [ ] No individual artifact detail/download UI (only list & signed URL logic missing).
- GET /api/v1/requests/{request_id}/artifacts/{artifact_id}:sign (compat via colon) — [ ] Not integrated (no signed URL button).

### Flat Preview & Jobs
- POST /api/v1/flat/preview — [ ] Not wired to a UI preview pane.

### Validate Rules
- POST /api/v1/validate — [~] Service exists (`validation.ts`); UI lacks report rendering & rule builder.

### Provider Inference
- POST /api/v1/projects/{project_id}/infer/providers — [x] Used (`providers.ts` inferProviders).
- POST /api/v1/infer/providers — [ ] Non-scoped alias unused (optional).

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
- Default model marking UX — [ ] Follow-up (client helper exists but needs UI trigger).

### Auth & Users
// OIDC still pending; all password-based flows now implemented
- GET /api/v1/auth/login (OIDC start) — [ ] Not used; only password login implemented.
- GET /api/v1/auth/callback — [ ] No OIDC callback page.
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
   - [ ] List keys (masked) with scopes.
   - [ ] Create key modal (name + scopes multi-select) displaying plaintext once.
   - [ ] Revoke key action (confirmation dialog).
3. Auth Flows Expansion
   - [x] Registration page (email, org, password; success leads to verify screen).
   - [x] Email verification screen (OTP input + resend). 
   - [x] Forgot/reset password sequence (request → OTP → new password).
   - [x] Change password panel (current pwd or OTP path).
   - [x] Profile page using /users/me with avatar upload.
4. Admin User Approval
   - [x] Admin dashboard showing pending users with approve/reject actions.
5. Sources Enhancements
   - [ ] DAG visualization using /dag endpoint (ReactFlow integration).
   - [ ] Source list/history per project (show uploaded files, timestamps).
6. Requests & Artifacts
   - [ ] Requests list/history page (status badges, last run times).
   - [ ] Artifact detail/download (signed URL fetch; add "Get Signed URL" button).
   - [ ] Signed URL integration for CSV/Parquet/XLSX/JSONL.
7. Validation Rules UI
   - [ ] Rule builder form for uniqueness, implication, distribution, temporal.
   - [ ] Preview validation report rendering (sample vs final).
8. Flat Preview
   - [ ] UI pane for POST /flat/preview (schema JSON editor + first 100 rows table).
9. Provider Suggestions UX
   - [ ] Improve provider suggestions display (confidence, manual override diff highlighting).
   - [ ] Persist provider configs fully (backend PUT providers endpoint forthcoming) — adjust once API stable.
10. LLM Model Default UX
   - [ ] Add toggle/button to mark one model default; refresh list after discover.
11. OIDC (Optional Phase)
   - [ ] OIDC login start redirect & callback handler storing token.
12. Webhook Configuration
   - [x] Run-status webhook URL field + Register Webhook button invoking POST /webhooks/run-status.

## Cross-Cutting Improvements
- [x] Central error boundary + global toast system.
- [~] Loading skeletons (Profile & Verify Email done; requests list & providers discovery pending).
- [ ] Rate-limit feedback banner for infer providers (handle 429 gracefully).
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
- [ ] Non-scoped infer alias usage (/infer/providers) — only if public trial mode needed.
- [ ] Advanced artifacts filtering (format/date range).
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
