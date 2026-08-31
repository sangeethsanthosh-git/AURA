# AURA Backend API

The REST API wraps the existing AURA backend without replacing the Electron JSON-lines bridge.

## Run

```powershell
python -m backend.api.server
```

Default base URL: `http://127.0.0.1:8765/api/v1`

## Environment

Configure these values in `.env` for production-like runs:

- `DATABASE_URL=sqlite:///data/aura.sqlite3`
- `JWT_SECRET`
- `JWT_REFRESH_SECRET`
- `CORS_ORIGIN`
- `AURA_API_HOST`
- `AURA_API_PORT`
- `AURA_RATE_LIMIT_PER_MINUTE`

Use long, unique secrets for `JWT_SECRET` and `JWT_REFRESH_SECRET`.

## Response Shape

Success:

```json
{ "success": true, "data": {}, "message": "Operation completed successfully" }
```

Error:

```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "message": "Invalid request", "details": [] } }
```

## Endpoints

- `GET /api/v1/health`
- `GET /api/v1/openapi.json`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/me`
- `POST /api/v1/aura/message`
- `GET /api/v1/memories`
- `POST /api/v1/memories/forget`
- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/activity`
- `POST /api/v1/weather/current`
- `POST /api/v1/web/search`

All endpoints except health, OpenAPI, and auth entry points require `Authorization: Bearer <access_token>`.
