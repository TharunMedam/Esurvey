# REST API contract

All paths begin with `/api`. JSON requests must use `Content-Type: application/json`. Errors use `{"error":"Human-readable explanation"}`. IDs are integers; dates are UTC ISO strings. Authentication uses an HttpOnly, SameSite=Lax session cookie (Secure in Vercel production), expiring after 12 hours.

## Session and authentication

Call `GET /session` first. Its response contains `csrf`, `user` (or null), and `available`. Send that CSRF token as `X-CSRF-Token` on every POST, PATCH, or DELETE except public survey responses. The session cookie must accompany requests. Registration and login rotate the token; use the returned replacement.

| Method | Path | Contract |
|---|---|---|
| GET | `/session` | Session identity, CSRF token, database configuration status |
| POST | `/auth/register` | `name` (2–100), `business` (2–120), `industry` (1–60, optional), `email`, `password` (12–128). Returns 201 with user and CSRF token; creates first business and default survey. |
| POST | `/auth/login` | `email`, `password`. Returns user and new CSRF token. |
| POST | `/auth/logout` | Clears session. |

Registration accepts 10 attempts per network identifier per 10-minute bucket; login accepts 20. No email is sent by these endpoints.

## Businesses and private records

All endpoints below require a signed-in owner. Cross-business resource access returns 404. The user ID is derived from the session, never from request parameters.

| Method | Path | Contract |
|---|---|---|
| GET | `/businesses` | Lists the signed-in owner's businesses. |
| POST | `/businesses` | `name` (2–120), `industry` (1–60). Creates an empty business. |
| PATCH | `/businesses/{bid}` | `name`, `industry`. Updates public business profile. |
| GET | `/businesses/{bid}/dashboard` | Returns `business`, `surveys`, `reviews`, `actions`, `summary`. |
| GET | `/businesses/{bid}/export` | UTF-8 CSV attachment with BOM, formula-safe text cells, and matching filters. |
| POST | `/businesses/{bid}/surveys` | `title` (2–150), `description` (0–1000), `categories` (array of 1–8 nonempty strings, each up to 80 characters). Returns 201. |
| PATCH | `/businesses/{bid}/surveys/{id}` | Optional `title`, `description`, `categories`, `status` (`active`, `paused`). |
| DELETE | `/businesses/{bid}/surveys/{id}` | Deletes only surveys without responses; otherwise 409. |
| PATCH | `/businesses/{bid}/reviews/{id}` | `status`: `new`, `reviewing`, or `resolved`. Raw feedback cannot be edited by a business owner. |
| POST | `/businesses/{bid}/actions` | `title` (3–180), `category` (1–80), `priority`: `high`, `medium`, `low`. |
| PATCH | `/businesses/{bid}/actions/{id}` | Optional `title`, `status`: `planned`, `in_progress`, `done`. |
| DELETE | `/businesses/{bid}/actions/{id}` | Deletes an action. |

Dashboard and export filters:

| Parameter | Values |
|---|---|
| `days` | `7`, `30` (default), `90`, `365`, `all` |
| `q` | Case-insensitive search in comment, name, and category; first 150 characters |
| `category` | Exact category name |
| `rating` | `1`–`5`, `negative` (1–2), `positive` (4–5) |
| `status` | `new`, `reviewing`, `resolved` |

## Public survey flow

`GET /public/surveys/{slug}` returns title, description, categories, status, business name, and `demo`. Unknown slugs return 404; paused surveys return 410.

`POST /public/surveys/{slug}/responses` accepts:

```json
{
  "rating": 2,
  "category": "Service",
  "comment": "The food was good, but our order took 40 minutes.",
  "name": "",
  "consent": true,
  "submission_key": "94b13a18-ec85-41c3-91a5-d5ec4196cd6a",
  "website": ""
}
```

- `rating` must be an integer between 1 and 5 (booleans and numeric strings are rejected).
- `category` must match a configured survey category.
- `comment` must contain 5–3000 non-whitespace characters.
- `name` is optional and limited to 100 characters; blank becomes `Anonymous`.
- `consent` must be the JSON boolean `true`.
- `submission_key` must be a 16–64-character client-generated unique key. Retrying with the same survey/key returns the existing response rather than inserting another.
- `website` is a honeypot and must be blank.
- Successful first submission returns 201 with `{"ok":true,"id":123}`. A retry returns 200 with the original ID.
- Public responses are limited to 15 per survey/network identifier per 10-minute bucket. Network identifiers are hashed; expired limiter records are removed during subsequent limited requests.
- Sample surveys return 400 on submission. The browser previews success locally and clearly states that no response was saved.

## Public demonstration and health

`GET /demo` and `GET /demo/export` expose only synthetic sample data, with the same filters. `GET /health` returns process health and whether database credentials are configured; it does not validate database connectivity.

## Errors

400 validation error; 401 sign-in required; 403 invalid/missing CSRF token; 404 missing or unauthorized record; 409 duplicate account or protected deletion; 410 paused survey; 413 request body exceeds 32 KiB; 429 rate limit; 503 missing or temporarily unavailable database. Database exceptions never return credentials or raw SQL to clients.
