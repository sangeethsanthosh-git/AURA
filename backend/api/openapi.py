"""OpenAPI document for public REST endpoints."""

OPENAPI_DOCUMENT = {
    "openapi": "3.0.3",
    "info": {"title": "AURA Backend API", "version": "1.0.0"},
    "paths": {
        "/api/v1/health": {"get": {"summary": "Health check", "responses": {"200": {"description": "Healthy"}}}},
        "/api/v1/auth/register": {"post": {"summary": "Register a user", "responses": {"201": {"description": "Created"}}}},
        "/api/v1/auth/login": {"post": {"summary": "Login", "responses": {"200": {"description": "Authenticated"}}}},
        "/api/v1/auth/refresh": {"post": {"summary": "Refresh tokens", "responses": {"200": {"description": "Refreshed"}}}},
        "/api/v1/auth/logout": {"post": {"summary": "Logout", "responses": {"200": {"description": "Logged out"}}}},
        "/api/v1/me": {"get": {"summary": "Current user", "security": [{"bearerAuth": []}], "responses": {"200": {"description": "Profile"}}}},
        "/api/v1/aura/message": {"post": {"summary": "Send an AURA prompt", "security": [{"bearerAuth": []}], "responses": {"200": {"description": "AURA response"}}}},
        "/api/v1/memories": {"get": {"summary": "List current user's local memories", "security": [{"bearerAuth": []}], "responses": {"200": {"description": "Memories"}}}},
        "/api/v1/memories/forget": {"post": {"summary": "Forget matching memory content", "security": [{"bearerAuth": []}], "responses": {"200": {"description": "Forgotten"}}}},
        "/api/v1/dashboard/summary": {"get": {"summary": "Dashboard summary", "security": [{"bearerAuth": []}], "responses": {"200": {"description": "Summary"}}}},
        "/api/v1/dashboard/activity": {"get": {"summary": "Recent activity", "security": [{"bearerAuth": []}], "responses": {"200": {"description": "Activity"}}}},
    },
    "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}},
}

