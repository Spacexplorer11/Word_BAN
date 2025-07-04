import logging
import os
import time

import requests
from dotenv import load_dotenv
from slack_sdk.errors import SlackApiError

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- In-memory cache for user permissions ---
# { "user_id-channel_id": {"is_manager": bool, "timestamp": float} }
permission_cache = {}
CACHE_TTL_SECONDS = 300  # 5 minutes

# --- Webhook for Rate Limit Notifications ---
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


def send_rate_limit_notification(user_id, channel_id, error):
    """Sends a notification to the configured Discord webhook about a rate-limiting event."""
    if not DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL is not set. Cannot send rate limit notification.")
        return

    retry_after = error.response.headers.get("Retry-After", "N/A")
    message = {
        "content": "<@1168126408808202273>",
        "embeds": [
            {
                "title": "🚨 Slack API Rate Limit Exceeded",
                "description": "The application hit a rate limit while trying to check user permissions.",
                "color": 15158332,  # Red
                "fields": [
                    {"name": "User ID", "value": user_id, "inline": True},
                    {"name": "Channel ID", "value": channel_id, "inline": True},
                    {"name": "Retry-After", "value": f"{retry_after} seconds", "inline": True},
                    {"name": "Timestamp", "value": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                     "inline": False},
                ],
                "footer": {"text": "This may indicate high traffic or abuse."}
            }
        ]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=message)
    except requests.RequestException as e:
        logger.error(f"Failed to send Discord webhook notification: {e}")


def is_user_channel_manager(client, user_id, channel_id):
    """
    Checks if a user is a manager of a channel, with caching.
    A user is considered a manager if they are a workspace admin/owner
    or the creator of the channel.
    Returns a tuple: (is_manager: bool, error_occurred: bool)
    """
    cache_key = f"{user_id}-{channel_id}"
    current_time = time.time()

    if cache_key in permission_cache:
        cached_data = permission_cache[cache_key]
        if current_time - cached_data["timestamp"] < CACHE_TTL_SECONDS:
            logger.info(f"Cache hit for user {user_id} in channel {channel_id}")
            return cached_data["is_manager"], False

    logger.info(f"Cache miss for user {user_id} in channel {channel_id}. Fetching from API.")
    try:
        user_info = client.users_info(user=user_id)
        user_profile = user_info.get("user", {})
        is_admin_or_owner = user_profile.get("is_admin", False) or user_profile.get("is_owner", False)

        conversation_info = client.conversations_info(channel=channel_id)
        channel_info = conversation_info.get("channel", {})
        is_channel_creator = channel_info.get("creator") == user_id

        is_manager = is_admin_or_owner or is_channel_creator
        permission_cache[cache_key] = {"is_manager": is_manager, "timestamp": current_time}
        return is_manager, False

    except SlackApiError as e:
        logger.error(f"Error checking user permissions: {e}")
        # Check if the error is a rate-limiting error (HTTP 429)
        if e.response.status_code == 429:
            send_rate_limit_notification(user_id, channel_id, e)
        return False, True  # Return False (not manager) and True (error occurred)
