# E-Survey

[Live application](https://esurvey-feedback-platform.vercel.app) · [GitHub repository](https://github.com/TharunMedam/Esurvey)

A working customer-feedback platform built with Python, Flask, SQLAlchemy, MySQL-compatible storage, Pandas, and a responsive JavaScript interface.

## Use the platform

1. Explore the clearly labeled **sample workspace** on the home page.
2. Select **Create workspace** to register your own business account.
3. Open **Surveys**, customize your survey, and copy its customer link.
4. Share that link with customers. They can submit a rating, category, written feedback, and optional name without an account.
5. Read and filter submissions in **Review inbox**. Mark responses as reviewing or resolved.
6. Use **Reports & insights** for rating distributions, category comparisons, and low-rating priorities. Export CSV or print/save a PDF using your browser.
7. Add measurable improvements to **Improvement plan** and move them through To do, In progress, and Completed.
8. Click the business selector to manage multiple separate businesses under one owner account. Other enterprises can register their own independent accounts.

## Stack and structure

- `app.py`: Flask/Vercel entrypoint.
- `esurvey/__init__.py`: application factory, database sessions, security headers, CSRF handling.
- `esurvey/models.py`: relational schema with foreign keys, uniqueness constraints, and query indexes.
- `esurvey/routes.py`: authenticated REST API, public survey endpoints, validation, database-backed request limits.
- `esurvey/reporting.py`: Pandas aggregation, trend preparation, and formula-safe CSV generation.
- `esurvey/demo.py`: synthetic example data; never mixed into live workspaces.
- `public/`: responsive dashboard and public customer survey UI; no frontend build step.
- `tests/`: workflow, authorization, validation, and reporting tests.
- `docs/API.md`: API contract and examples.
- `docs/schema.sql`: MySQL schema reference generated from the ORM models.

## Local development

Use Python 3.12 or newer:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. Without `DATABASE_URL`, local development uses a persistent `local.db` SQLite file. Production on Vercel never silently falls back to SQLite or ephemeral storage.

For MySQL, copy `.env.example` to `.env` and set `DATABASE_URL` and a long random `SECRET_KEY`. URL-encode special characters in database credentials. Enable TLS with `DATABASE_SSL=true`. Initialize the schema explicitly:

```sh
flask --app app init-db
```

`create_all` creates missing tables; it does not migrate existing columns. Add a versioned migration before deploying future schema changes.

## Vercel deployment

The project uses Vercel's native Flask support. Keep the database external to Vercel Functions.

```sh
vercel login
vercel link
vercel env add DATABASE_URL production
vercel env add SECRET_KEY production
vercel env add DATABASE_SSL production
vercel --prod
```

Store database credentials and the session signing secret as sensitive server-only variables. Keep `.env`, `.env.local`, `.vercel`, and database files out of Git. Do not share production secrets with preview deployments; use a separate preview database if you need authenticated previews.

## Verification

```sh
python -m unittest discover -s tests -v
node --check public/app.js
```

The backend suite checks account/session handling, CSRF protection, cross-business isolation, validation, duplicate submission handling, paused surveys, CRUD operations, reporting filters, and formula-safe CSV exports.

## Interpretation of reports

- **Overall rating:** mean of all selected 1–5 ratings.
- **Positive feedback:** percentage of selected ratings equal to 4 or 5.
- **Needs attention:** selected ratings of 1 or 2 that are not resolved.
- **Category score:** mean overall rating for submissions assigned to that category. It is not a multi-question score.
- **Trend:** daily average rating on dates with responses; dates without feedback are omitted.
- **Improvement priorities:** deterministic ranking by number of 1–2-star ratings, not AI sentiment analysis or causal conclusions.
- All exported results respect the active date/search/category/rating/status filters.

## Operating limits

This is a deployable initial product, not a certified enterprise service. One owner manages each business; staff invitations, email verification, self-service password recovery, audit logs, SSO, and automated backups are not implemented. Public surveys use random links, a honeypot, idempotency keys, and request limits; these reduce accidental duplicates and basic spam but do not prove a respondent is a real customer. Anonymous users can submit multiple legitimate visits. Use additional verification if you require one response per transaction.

Reporting currently aggregates the selected business/date window in application memory. For very large datasets, add server-side pagination and precomputed aggregates. Before collecting sensitive customer data at scale, establish your own retention, account recovery, backup, and support procedures. Avoid soliciting medical, payment, or other sensitive information in free-text feedback.

The deployed setup uses a MySQL-compatible TiDB Cloud Starter instance claimed into the owner's account. The earlier temporary-database expiration no longer applies. Manage database usage, access, and backups in TiDB Cloud. No paid database subscription was purchased by this setup.

## Git workflow

Use feature branches and review changes before merging. Run the verification commands above before deployment. The repository is connected to TharunMedam/Esurvey on GitHub. The earlier Node.js demo is preserved in Git history; the current application uses Flask and persistent MySQL-compatible storage. Configure the Vercel Git integration separately if automatic deployments are desired.
