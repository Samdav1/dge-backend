from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Check if a new access token was generated during dependency resolution
        new_access_token = getattr(request.state, "new_access_token", None)
        if new_access_token:
            # Expose the new access token in a custom header
            response.headers["X-New-Access-Token"] = new_access_token
            # Also ensure the header is exposed to the frontend in CORS requests
            if "Access-Control-Expose-Headers" in response.headers:
                response.headers["Access-Control-Expose-Headers"] += ", X-New-Access-Token"
            else:
                response.headers["Access-Control-Expose-Headers"] = "X-New-Access-Token"
                
        return response
