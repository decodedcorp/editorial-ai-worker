# User Setup: Supabase Service Layer (02-01)

## Required Service: Supabase

The Supabase service layer needs access to your Supabase project for data reads and (in Plan 02-02) for the Postgres checkpointer.

## Environment Variables

Add the following to your `.env` or `.env.local` file:

### 1. SUPABASE_URL

- **Source:** Supabase Dashboard -> Settings -> API -> Project URL
- **Format:** `https://<project-ref>.supabase.co`
- **Example:** `SUPABASE_URL=https://abcdefghijklmnop.supabase.co`

### 2. SUPABASE_SERVICE_ROLE_KEY

- **Source:** Supabase Dashboard -> Settings -> API -> service_role key (secret)
- **Format:** A long JWT string starting with `eyJ...`
- **Example:** `SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...`
- **Warning:** This key bypasses Row Level Security (RLS). Keep it secret and never expose it in client-side code.

### 3. DATABASE_URL

- **Source:** Supabase Dashboard -> Settings -> Database -> Connection string -> Session mode (port 5432)
- **Format:** `postgres://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres`
- **Example:** `DATABASE_URL=postgres://postgres.abcdefghijklmnop:your-password@aws-0-us-east-1.pooler.supabase.com:5432/postgres`
- **Note:** Use Session mode (port 5432), NOT Transaction mode (port 6543). The checkpointer needs session-level features.

## Verification

After setting the environment variables, verify the connection works:

```bash
# Check config loads the values
uv run python -c "from editorial_ai.config import settings; print('URL:', settings.supabase_url[:30] + '...' if settings.supabase_url else 'NOT SET')"

# Run integration tests against live Supabase (read-only)
uv run pytest -m integration -v
```

## Important Notes

- All three env vars are optional at startup (the app won't crash without them)
- They are required only when actually connecting to Supabase (service functions, checkpointer)
- The Pydantic models may need schema adjustments after verifying against your actual Supabase tables
- Integration tests are read-only and will NOT modify any data
