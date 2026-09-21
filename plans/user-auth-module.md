# User & Auth Module Implementation Plan

## Current State

**What works:**
- Backend: `/api/auth/register`, `/api/auth/login`, `/api/auth/logout` endpoints
- Frontend: LoginForm and RegisterForm components
- Password hashing with Argon2id
- Session cookies (httpOnly, secure flags)
- MongoDB users collection

**What's broken/incomplete:**
1. Origin header mismatch blocks all auth requests from frontend
2. No email validation (format only, not existence check)
3. No password strength requirements
4. No "forgot password" flow
5. No email verification
6. Session expiry not enforced on client side
7. No rate limiting on registration (only on login)
8. No user profile/preferences storage
9. No logout confirmation
10. No session management (view active sessions, logout all)

---

## Implementation Plan (5 phases)

### Phase 1: Fix Critical Auth Bugs (TODAY)

**User stories:**
- User can register with email/password and stay logged in
- User can log in with email/password
- User can log out

**What to fix:**
1. ✅ ALLOWED_ORIGINS origin mismatch (DONE)
2. Verify session cookie is set and sent on all requests
3. Test registration → auto-login flow end-to-end
4. Test logout clears cookie
5. Add error message clarity (email taken, bad password, etc)

**Acceptance criteria:**
- [ ] Register at `/register`, redirects to `/kits` logged in
- [ ] Can create a Kit immediately after registering
- [ ] Logout clears session, redirects to `/login`
- [ ] Refresh page after logout stays logged out
- [ ] Login with wrong password shows error
- [ ] Login with non-existent email shows error

**Tests to add:**
```python
# Backend tests
- test_register_creates_user()
- test_register_sets_session_cookie()
- test_register_duplicate_email_fails()
- test_login_valid_credentials()
- test_login_invalid_password()
- test_logout_clears_session()
- test_session_persists_across_requests()
```

**Files to check/fix:**
- `apps/api/app/api/routers/auth.py:49-87` (register/login endpoints)
- `apps/api/app/persistence/store.py` (session store)
- `apps/web/lib/api-client.ts` (fetch config for cookies)
- `apps/web/components/auth-form.tsx` (error handling)

---

### Phase 2: Password & Input Validation (1 day)

**User stories:**
- User sees clear error if password is too weak
- User sees clear error if email is invalid
- User cannot register with blank password or email

**What to add:**
1. Frontend validation: email format, password 8+ chars
2. Backend validation: same, plus email normalization (lowercase)
3. Password strength hints (optional: suggest "correct horse battery staple")
4. Sanitize inputs (trim whitespace)

**Acceptance criteria:**
- [ ] Register with email "abc" shows "Enter a valid email"
- [ ] Register with password "123" shows "Password must be at least 8 characters"
- [ ] Register with empty fields shows validation errors
- [ ] Whitespace is trimmed from email before checking

**Files to update:**
- `apps/web/components/auth-form.tsx` (zod schema already has this, just verify)
- `apps/api/app/api/routers/auth.py:54-55` (backend validation)

---

### Phase 3: Rate Limiting & Abuse Prevention (1 day)

**User stories:**
- Attacker cannot spam registrations from one IP
- User cannot accidentally lock themselves out with many wrong passwords

**What to add:**
1. Registration rate limit: max 5 registrations per IP per hour
2. Login throttle: max 10 attempts per (IP + email) per 10 minutes
3. Bounded throttle store (prevent memory exhaustion)
4. Clear error messages: "Too many attempts, try again in X minutes"

**Acceptance criteria:**
- [ ] 6th registration from same IP in 1 hour fails with "rate limited" message
- [ ] 11th login attempt for same account in 10 minutes returns rate limit error
- [ ] Throttle store has max size limit (e.g., 100k entries)
- [ ] Throttle entries auto-expire after TTL

**Files to update:**
- `apps/api/app/api/routers/auth.py` (add registration throttle)
- `apps/api/app/persistence/store.py` (throttles store)

---

### Phase 4: User Profile & Preferences (2 days)

**User stories:**
- User can view their profile (email, created date)
- User can change their password
- User can update their name/preferences (optional: name, avatar, theme preference)
- User sees when they last logged in

**What to add:**
1. Extend User schema: name, avatar, theme, last_login, created_at
2. `PATCH /api/me` endpoint (update profile)
3. `POST /api/auth/change-password` endpoint
4. `GET /api/me` shows current user info
5. Frontend: simple profile page at `/profile`

**Acceptance criteria:**
- [ ] `GET /api/me` returns {id, email, name, created_at, last_login}
- [ ] `PATCH /api/me` updates name and theme
- [ ] `POST /api/auth/change-password` validates old password before changing
- [ ] Profile page shows user info and allows edits
- [ ] last_login updates on each login

**Files to create/update:**
- `apps/api/app/persistence/schemas.py` (extend User model)
- `apps/api/app/api/routers/auth.py` (add change-password endpoint)
- `apps/api/app/api/routers/users.py` (new, for profile updates)
- `apps/web/app/profile/page.tsx` (new profile page)

---

### Phase 5: Session Management & Security (2 days)

**User stories:**
- User can see all active sessions and log out from any device
- User can set session timeout
- User is warned if session is about to expire
- Old sessions are cleaned up automatically

**What to add:**
1. Session document: includes user_agent, ip_address, created_at, last_active
2. `GET /api/sessions` → list all active sessions
3. `DELETE /api/sessions/{id}` → logout from specific device
4. `POST /api/auth/logout-all` → logout everywhere
5. Auto-cleanup: remove sessions older than TTL
6. Client-side: show expiry warning 5 minutes before timeout

**Acceptance criteria:**
- [ ] Sessions list shows device info (user agent, IP, last active)
- [ ] Can logout from a specific session without affecting others
- [ ] "Logout all" clears every session for that user
- [ ] Session expires after TTL automatically
- [ ] 5-minute warning appears before expiry
- [ ] Expired sessions are cleaned from database

**Files to create/update:**
- `apps/api/app/persistence/schemas.py` (extend Session model)
- `apps/api/app/api/routers/auth.py` (add sessions endpoints)
- `apps/web/app/sessions/page.tsx` (new sessions management page)
- `apps/web/lib/auth.tsx` (add expiry warning logic)

---

## Testing Strategy

### Unit Tests (backend)
```python
# Password hashing
- test_hash_password_is_deterministic()
- test_verify_correct_password()
- test_verify_wrong_password_fails()

# User creation
- test_create_user_with_valid_email_password()
- test_create_user_duplicate_email_fails()
- test_create_user_normalizes_email_lowercase()

# Sessions
- test_session_created_on_login()
- test_session_expires_after_ttl()
- test_session_persists_across_requests()
- test_logout_deletes_session()
```

### Integration Tests (frontend + backend)
```typescript
// Registration flow
- test_register_then_api_call_includes_session_cookie()
- test_register_then_redirect_to_kits()
- test_register_duplicate_email_shows_error()

// Login flow
- test_login_with_correct_credentials()
- test_login_with_wrong_password()
- test_login_persists_session_across_page_reload()

// Logout flow
- test_logout_clears_session_and_redirects()
- test_logout_api_call_deletes_session()
```

### End-to-End Tests (Playwright)
```typescript
// User journey
- test_new_user_can_register_and_create_kit()
- test_user_can_login_to_existing_account()
- test_user_can_logout_and_login_again()
- test_session_timeout_redirects_to_login()
```

---

## Dependencies & Risks

**Dependencies:**
- Argon2id library (already installed: `argon2-cffi`)
- MongoDB for users/sessions (already set up)
- Pydantic for schema validation (already installed)

**Risks:**
- Session cookie stealing via XSS (mitigation: httpOnly, secure, SameSite=Lax flags)
- Brute force attacks (mitigation: rate limiting + Argon2 slow hashing)
- Email enumeration (mitigation: generic error messages for "not found" vs "bad password")
- Password reset link abuse (mitigation: short TTL, one-time tokens, rate limiting) — Phase 6

---

## Success Criteria

When complete, you should be able to:
1. ✅ Register with any email/password
2. ✅ Auto-login after registration
3. ✅ Log in with email/password
4. ✅ Stay logged in across page reloads
5. ✅ Log out and be redirected to login
6. ✅ See "session expired" message if TTL exceeded
7. ✅ Change password without re-registering
8. ✅ View active sessions across devices
9. ✅ Logout from a specific device

---

## Priority

**Must have (Phase 1-2):** Registration, login, logout, validation
**Should have (Phase 3-4):** Rate limiting, profile, password change
**Nice to have (Phase 5+):** Multi-session, advanced security
