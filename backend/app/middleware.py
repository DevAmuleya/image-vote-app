import os
import time
import collections
import threading
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging

logger = logging.getLogger("uvicorn.access")
logger.disabled = True

# True when running inside an AWS Lambda function
_IS_LAMBDA = "AWS_LAMBDA_FUNCTION_NAME" in os.environ

_LOCAL_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
]

# ─── In-memory sliding-window rate limiter ────────────────────────────────────
# Tracks request timestamps per (IP, route_group) over a 60-second window.
# No external dependencies — works in single-process servers and Lambda.
# Not suitable for multi-process/distributed deployments (use Redis there).

_rate_lock = threading.Lock()
_rate_log: dict[str, collections.deque] = collections.defaultdict(
    lambda: collections.deque()
)

# Route groups → (max_requests, window_seconds)
_RATE_LIMITS = {
    "vote":    (10, 60),   # POST /api/posts/{id}/vote — strict: 10 per minute
    "default": (60, 60),   # everything else: 60 per minute
}


def _check_rate_limit(ip: str, route_group: str) -> bool:
    """Return True if the request is allowed, False if it should be rejected."""
    max_req, window = _RATE_LIMITS.get(route_group, _RATE_LIMITS["default"])
    key = f"{ip}:{route_group}"
    now = time.monotonic()
    cutoff = now - window

    with _rate_lock:
        dq = _rate_log[key]
        # Remove timestamps outside the sliding window
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= max_req:
            return False
        dq.append(now)
        return True


def register_middleware(app: FastAPI):

    # CORS_ORIGINS env var: comma-separated list set by Terraform (CloudFront URL).
    # Falls back to localhost origins for local development.
    cors_env = os.getenv("CORS_ORIGINS", "")
    allow_origins = [o.strip() for o in cors_env.split(",") if o.strip()] or _LOCAL_ORIGINS

    # ✅ CORS MUST COME FIRST
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # TrustedHostMiddleware is skipped in Lambda — API Gateway enforces host
    # validation at its own layer so adding it here would reject valid requests.
    if not _IS_LAMBDA:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0"],
        )

    # ✅ Rate limiting + logging middleware (after CORS)
    @app.middleware("http")
    async def rate_limit_and_log(request: Request, call_next):
        start_time = time.time()

        # Determine client IP — trust X-Forwarded-For from API Gateway / load balancer
        forwarded_for = request.headers.get("x-forwarded-for")
        ip = forwarded_for.split(",")[0].strip() if forwarded_for else (
            request.client.host if request.client else "unknown"
        )

        # Classify route for rate limiting
        path = request.url.path
        if request.method == "POST" and "/vote" in path:
            route_group = "vote"
        else:
            route_group = "default"

        if not _check_rate_limit(ip, route_group):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)

        processing_time = time.time() - start_time
        print(
            f"{ip} - {request.method} {path} - "
            f"{response.status_code} - {processing_time:.4f}s"
        )
        return response

