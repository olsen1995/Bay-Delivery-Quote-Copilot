# Bay Delivery Quote Copilot — Project Rules

## Core Architecture Rules

1. SQLite is the source of truth.
2. Google Calendar is a scheduling mirror only.
3. Database writes must occur before external API calls.
4. Calendar sync failures must not corrupt or roll back valid DB state.
5. Route handlers must stay thin.
6. Business logic belongs in `app/services/`.
7. SQL belongs in `app/storage/`.
8. External API wrappers belong in `app/integrations/`.

## Security Rules

1. Admin authentication required for all admin scheduling endpoints.
2. Customer quote access must use secure tokens.
3. Booking submission must require `booking_token`.
4. Customer name and phone must not be editable after quote creation.
5. Prevent quote enumeration.
6. Prevent XSS in admin UI.
7. Prevent SQL injection by using parameterized queries and field allowlists.
8. Limit PII in Google Calendar payloads.
9. Never send phone numbers or full notes to Google Calendar.

## Scheduling Rules

1. Scheduling updates DB first.
2. Calendar sync happens second.
3. Calendar failure updates sync state and error fields only.
4. Cancel flow must preserve scheduling history.

## Typing Rules

1. Prefer typed helper functions over repeated Optional checks.
2. Use `TypedDict`, Pydantic models, or clear typed return values where helpful.
3. Avoid untyped dict mutation when a typed structure is available.

## AI Estimation Rules

1. AI may suggest structured inputs only.
2. AI must never determine final price.
3. Final pricing must always be calculated by the pricing engine.
4. Image analysis must be isolated in `app/services/ai_estimation_service.py`.

## Code Quality Rules

1. Keep modules small and focused.
2. Avoid growing `main.py` with business logic.
3. Preserve existing API behavior unless explicitly requested otherwise.
4. Prefer explicit code over clever abstractions.
5. Keep tests passing at all times.
