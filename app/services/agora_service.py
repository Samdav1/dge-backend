"""
Agora RTC Token Service

Generates short-lived RTC tokens for clients to join Agora voice/video channels.
The token is generated on the server using the App Certificate (never exposed to clients).

Usage:
    token = generate_agora_token(app_id, app_cert, channel_name, uid, expire_seconds=3600)
"""
import time
import logging

from agora_token_builder import RtcTokenBuilder

logger = logging.getLogger(__name__)

# Agora role constants
ROLE_PUBLISHER = 1    # Can publish audio/video and subscribe to others
ROLE_SUBSCRIBER = 2   # Read-only: can only subscribe to others


def generate_agora_token(
    app_id: str,
    app_certificate: str,
    channel_name: str,
    uid: int,
    role: int = ROLE_PUBLISHER,
    expire_seconds: int = 3600,
) -> str:
    """
    Generate a short-lived Agora RTC token.

    Args:
        app_id:           Agora project App ID.
        app_certificate:  Agora project App Certificate (keep secret, server-side only).
        channel_name:     The channel the user wants to join.
        uid:              Numeric user ID (use 0 to let Agora assign one automatically).
        role:             ROLE_PUBLISHER (1) or ROLE_SUBSCRIBER (2).
        expire_seconds:   Token validity window in seconds (default: 1 hour).

    Returns:
        A time-limited Agora RTC token string.
    """
    expire_ts = int(time.time()) + expire_seconds
    token = RtcTokenBuilder.buildTokenWithUid(
        app_id,
        app_certificate,
        channel_name,
        uid,
        role,
        expire_ts,
    )
    logger.debug(
        "Generated Agora token for channel=%s uid=%s expires_in=%ss",
        channel_name,
        uid,
        expire_seconds,
    )
    return token
