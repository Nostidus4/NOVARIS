# Q-SHIELD Authentication — Implementation Plan

**Status:** Implemented and verified on 2026-09-23
**Scope:** Responsive login/register UI + Supabase email/password authentication through FastAPI
**Reference:** `frontend/public/Authentication.png` (1672×941)

## 1. Goals

1. Recreate the supplied desktop login design as a real, responsive page at `/login`.
2. Use `Authentication.png` only as the visual background; all text, controls, validation,
   focus states, loading states, and errors remain real HTML.
3. Authenticate email/password against the existing Supabase project through the FastAPI
   backend. Q-SHIELD must never store or log a plaintext password.
4. Keep the existing console functional and preserve the current GitHub Pages/static-export
   deployment path.
5. Add automated tests around the backend authentication contract and run frontend lint/build.
6. Support account registration, including Supabase projects that require email confirmation.

## 2. Current-state constraints

- Frontend: Next.js App Router, React 19, TypeScript, Tailwind v4, Lucide icons.
- Backend: FastAPI with a hexagonal layout and an existing server-only Supabase configuration.
- The console pages are server components and are also statically exportable for GitHub Pages.
- The supplied background is a wide desktop asset; mobile cannot preserve every crop, so the
  form must remain readable while the focal quantum sphere is repositioned.
- Existing console read APIs are intentionally left compatible. Authentication will gate entry
  in the web application and establish a backend-verifiable session contract; making every
  existing static read endpoint private would require converting the whole console data layer to
  authenticated client fetching and is not part of this UI feature.

## 3. User flow

1. Visiting `/` opens the public landing page.
2. The user selects “Đăng nhập” or “Truy cập hệ thống” to open `/login`.
3. The user enters an email and password.
4. Client validation rejects malformed email or empty/short password without a network request.
5. `POST /auth/login` sends credentials to Supabase Auth.
6. On success, the frontend stores the access token:
   - `localStorage` when “Ghi nhớ đăng nhập” is checked;
   - `sessionStorage` otherwise.
7. The frontend stores only session metadata needed by the UI. It never stores the password.
8. The login page confirms the token through `GET /auth/me`, then routes to `/overview`.
9. Console routes are wrapped by a client-side auth gate. Missing, expired, or rejected sessions
   are cleared and redirected to `/login?next=<route>`.
10. Logout calls `POST /auth/logout`, clears both browser storage locations, and returns to login.

## 4. Backend design

### 4.1 Contracts

- `LoginRequest`: normalized email and bounded password.
- `AuthUserDTO`: stable user id, email, and optional display name.
- `LoginResponse`: access token, refresh token, token type, expiry, and user.
- `SessionResponse`: current authenticated user.

Pydantic performs boundary validation. Password fields use secret types so their representation
does not expose the value.

### 4.2 Auth provider boundary

- Add an `AuthProvider` protocol under `domain/auth`.
- Add Supabase implementation under `infrastructure/auth`.
- Add login/get-current-user/logout use cases under `application/auth`.
- Construct the provider in `deps.py` using the publishable key, not the secret/service key.
- Create a fresh Supabase auth client for authentication operations so user session state is not
  shared across concurrent requests.

### 4.3 HTTP endpoints

- `POST /auth/login`
  - `200`: valid session payload.
  - `401`: generic “email or password is incorrect”; do not reveal which field matched.
  - `422`: malformed request.
- `POST /auth/register`
  - creates the Supabase Auth user with a normalized display name;
  - returns a session immediately when email confirmation is disabled;
  - otherwise returns `email_confirmation_required=true` for the confirmation screen.
- `GET /auth/me`
  - reads `Authorization: Bearer <token>`;
  - validates the token with Supabase and returns normalized user data;
  - `401` for missing, invalid, or expired tokens.
- `POST /auth/logout`
  - attempts provider-side sign-out for the bearer session;
  - remains idempotent from the UI perspective.

No access tokens, refresh tokens, authorization headers, or passwords may be logged.

### 4.4 Error mapping

- Provider invalid-credential/session errors map to HTTP 401.
- Provider availability/configuration failures map to HTTP 503.
- Client responses use stable Vietnamese messages without leaking Supabase internals.

## 5. Frontend design

### 5.1 Route and components

- `app/(auth)/login/page.tsx` and `app/(auth)/register/page.tsx`: public auth routes.
- `components/auth/LoginForm.tsx`: controlled form, validation, loading, password visibility,
  remember-me, submit error, and redirect handling.
- `components/auth/AuthGate.tsx`: session verification and protected-console transition.
- `components/auth/QuantumShieldIcon.tsx`: small code-native decorative shield/orbit mark.
- `lib/auth.ts`: typed API calls, safe storage helpers, expiry handling, logout.

### 5.2 Visual specification

- Full-viewport background using `Authentication.png` with dark overlays for contrast.
- Desktop split: brand/value proposition at left; glass login panel at right.
- Login panel: translucent navy surface, thin cool-gray border, blue glow, 28–32px radius.
- Inputs: 52–56px height, icon prefix, visible focus ring, password reveal button.
- Browser-autofilled inputs retain the same dark surface, text, and caret styling as typed values.
- Primary action: blue/cyan gradient with progress state.
- The page supports the working email/password flow only; no inactive social-login controls are
  shown.
- Mobile/tablet: hide the long left copy, center the panel, preserve logo/back navigation, and
  crop the background around its focal point.
- Respect `prefers-reduced-motion`; all controls have keyboard focus and accessible labels.

### 5.3 Session behavior

- Bearer token is sent only to `NEXT_PUBLIC_QSHIELD_API_URL`.
- `next` redirects accept local paths only, preventing open redirects.
- On 401, clear stale storage and return to login.
- Browser storage is used because GitHub Pages is a separate static origin and cannot own a
  backend HttpOnly cookie. This has an XSS tradeoff; no HTML injection or token logging is added.

## 6. Existing console integration

- Serve a public landing page at `/`; its login CTAs navigate to `/login`.
- Wrap the console layout with `AuthGate` without rewriting the existing presentation pages.
- Add a logout control to the top bar or sidebar while preserving theme/run controls.
- Keep asset paths compatible with the existing GitHub Pages base path helper.

## 7. Tests and verification

### Backend

- Login success returns normalized session/user.
- Invalid credentials return 401 and a generic message.
- Provider failure returns 503.
- `/auth/me` rejects a missing/malformed bearer header.
- `/auth/me` returns the provider user for a valid token.
- Logout is callable with a valid bearer token.

### Frontend

- ESLint passes.
- Next production build passes.
- Static Pages build passes so `/login/` is exportable.
- Manual responsive smoke checks at approximately 1440px, 1024px, 768px, and 390px.
- Keyboard smoke check: tab order, focus visibility, password toggle, checkbox, submit.

### Backend suite

- Run focused auth tests first, then the existing backend tests to detect router/config regressions.

## 8. Delivery order

1. Add backend auth domain/application/infrastructure contracts and endpoint tests.
2. Register the auth router and verify the focused backend tests.
3. Add frontend auth client/session helpers and login page.
4. Add the console auth gate, safe redirect, and logout action.
5. Tune responsive styling against the supplied reference.
6. Run lint, Next builds, backend tests, and inspect the final diff for secrets or unrelated edits.

## 9. Acceptance criteria

- A real user in Supabase Auth can sign in with email/password and reach `/overview`.
- Wrong credentials show a generic inline error and never expose provider details.
- Refresh preserves or drops the session according to the remember-me choice.
- Expired/invalid sessions return to login.
- The UI closely matches the supplied visual on desktop and remains usable on mobile.
- Existing console behavior, static export, and backend tests continue to pass.
- No secret keys, plaintext passwords, or session tokens are committed or printed.
