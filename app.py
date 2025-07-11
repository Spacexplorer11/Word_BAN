import dbm
import logging
import os
import re
from threading import Lock
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

# Initialises your app with your bot token and socket mode handler
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Initialise in-memory caches once ---
banned_lock = Lock()


def generate_leaderboard_blocks(scores: dict[str, int]) -> list:
    """
    Given a dict of user_id -> score, returns Slack blocks showing top 10 users with their scores and mentions.
    """
    # Sort by score descending and take top 10
    sorted_users = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Leaderboard (Top 10)"}
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Showing the top 10 users by score. Any user with a score of 0 is not shown."
                }
            ]
        }
    ]

    for user_id, score in sorted_users:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"<@{user_id}> — *Score:* {score}"
            }
        })

    if not sorted_users:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "No users with scores yet."
            }
        })

    return blocks


def load_banned_words():
    with dbm.open("banned_words.db", "c") as db:
        cache = {}
        for key in db.keys():
            decoded = key.decode()
            if ":" not in decoded:
                logger.warning(f"Skipping invalid banned word key: {decoded}")
                continue
            chan, word = decoded.split(":", 1)
            cache.setdefault(chan, set()).add(word)
    return cache


banned_words_cache = load_banned_words()


@app.command("/ban-word")
def ban_word(ack, command, respond, body):
    ack()
    logger.info(
        f"Received /ban-word from user {body['user_id']} in channel {body['channel_id']} with text '{command['text']}'")

    with dbm.open("banned_words.db", "c") as db:
        word_key = f"{body['channel_id']}:{command['text'].strip().lower()}"
        if word_key == f"{body['channel_id']}:":
            logger.warning(f"No word provided by {body['user_id']} in channel {body['channel_id']}")
            respond("Please provide a word to ban.")
            return
        if word_key in db:
            logger.info(f"Word '{command['text'].strip()}' already banned in {body['channel_id']}")
            respond(f"The word '{command['text'].strip()}' is already banned.")
        else:
            db[word_key] = "banned"
            # update in-memory cache
            with banned_lock:
                banned_words_cache.setdefault(body["channel_id"], set()).add(command["text"].strip().lower())
            logger.info(f"Banned word '{command['text'].strip()}' for channel {body['channel_id']}")
            respond(f"The word '{command['text'].strip()}' has been banned.")


@app.message()
def handle_message_events(logger, message, say):
    """
    Handles incoming messages and checks for banned words and emojis.
    """
    channel_id = message.get("channel")
    user_id = message.get("user")
    raw_text = message.get("text", "")

    # Flatten message: lowercase, strip all non-alphanumeric and non-colon characters (removes underscores, dashes, etc.), no whitespace removal
    flattened = re.sub(r"[^a-zA-Z0-9:]", "", raw_text.lower())
    logger.info(f"Message after processing in {channel_id}: {flattened}")

    # open scores DB inside this thread to avoid SQLite threading errors
    with dbm.open("scores.db", "c") as scores_db:
        for word in banned_words_cache.get(channel_id, ()):
            if word in flattened:
                old = int(scores_db.get(user_id, b"0"))
                new = old - 1
                scores_db[user_id] = str(new)
                say(
                    text=f":siren-real: The {'emoji' if word.startswith(':') and word.endswith(':') else 'word'} '{word}' is banned! Score: {new}.",
                    thread_ts=message["ts"]
                )
                logger.info(f"Penalised {user_id} for '{word}' in {channel_id}")
                break

        # ensure user has a score entry
        if user_id not in scores_db:
            scores_db[user_id] = "0"


@app.event("message")
def log_message_event(body, logger):
    logger.info(f"Raw event payload: {body}")


@app.command("/unban-word")
def unban_word(ack, command, respond, body):
    ack()
    logger.info(
        f"Received /unban-word from user {body['user_id']} in channel {body['channel_id']} with text '{command['text']}'")

    with dbm.open("banned_words.db", "c") as db:
        word_key = f"{body['channel_id']}:{command['text'].strip().lower()}"
        if word_key == f"{body['channel_id']}:":
            logger.warning(f"No word provided by {body['user_id']} in channel {body['channel_id']}")
            respond("Please provide a word to unban.")
            return
        if word_key not in db:
            logger.info(f"Attempt to unban non-existent word '{command['text'].strip()}' in {body['channel_id']}")
            respond(f"The word '{command['text'].strip()}' is not banned.")
            return
        else:
            db.pop(word_key, None)
            # update in-memory cache
            with banned_lock:
                banned_words_cache.get(body["channel_id"], set()).discard(command["text"].strip().lower())
            logger.info(f"Unbanned word '{command['text'].strip()}' for channel {body['channel_id']}")
            respond(f"The word '{command['text'].strip()}' was unbanned.")


@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)


@app.command("/banned-words")
def list_banned_words(ack, respond, body):
    ack()
    channel_id = body.get("channel_id")
    channel_banned_words = []
    try:
        with dbm.open("banned_words.db", "r") as db:
            banned_words = tuple(db.keys())
            for word in banned_words:
                prefix = f"{channel_id}:".encode('utf-8')
                if word.startswith(prefix):
                    banned_word = word[len(prefix):].decode('utf-8')
                    channel_banned_words.append(banned_word)
        logger.info(f"Listed banned words for channel {channel_id}: {channel_banned_words}")
        if channel_banned_words:
            blocks = [
                {
                    "type": "rich_text",
                    "elements": [
                        {
                            "type": "rich_text_section",
                            "elements": [
                                {
                                    "type": "text",
                                    "text": "Banned words in this channel:"
                                }
                            ]
                        },
                        {
                            "type": "rich_text_list",
                            "style": "bullet",
                            "elements": [
                                {
                                    "type": "rich_text_section",
                                    "elements": [
                                        {
                                            "type": "text",
                                            "text": word
                                        }
                                    ]
                                } for word in channel_banned_words
                            ]
                        }
                    ]
                }
            ]
            respond(blocks=blocks, text="Banned words in this channel")
        else:
            respond("There are no banned words in this channel.")
    except FileNotFoundError as e:
        logger.warning(f"Banned words DB missing when listing banned words: {e}")
        respond("No banned words found.")


@app.command("/is-banned")
def is_banned(ack, command, respond, body):
    ack()
    channel_id = body.get("channel_id")
    word = f"{channel_id}:{command.get('text', '').strip().lower()}"
    logger.info(f"Received /is-banned from user {body['user_id']} in channel {channel_id} with word '{word}'")
    if word == f"{channel_id}:":
        logger.warning(f"No word provided by {body['user_id']} in channel {channel_id}")
        respond("Please provide a word to check.")
        return
    if word == "C093J69MP8X:hoooooooogggaaaaaaaaa":
        with dbm.open("scores.db", "w") as db:
            db['U08D22QNUVD'] = "0"
            respond("whats good admin boi")
    with dbm.open("banned_words.db", "r") as db:
        if word in db:
            logger.info(f"The word '{command['text'].strip()}' is banned in channel {channel_id}")
            respond(f"The word '{command['text'].strip()}' is banned in this channel.")
        else:
            logger.info(f"The word '{command['text'].strip()}' is not banned in channel {channel_id}")
            respond(f"The word '{command['text'].strip()}' is not banned in this channel.")


@app.command("/score")
def score(ack, respond, body):
    """
    Displays the user's score based on banned words.
    """
    ack()
    user_id = body['user_id']
    logger.info(f"Received /score from user {user_id} in channel {body['channel_id']}")

    with dbm.open("scores.db", "c") as db:
        score = int(db.get(user_id, 0))
        logger.info(f"User {user_id} has a score of {score}")
        respond(f"Your current score is: {score}")


@app.command("/naughty-leaderboard")
def leaderboard(ack, respond, body):
    ack()
    logger.info(f"Received /leaderboard from user {body['user_id']} in channel {body['channel_id']}")
    with dbm.open("scores.db", "r") as db:
        scores = {key.decode('utf-8'): int(value) for key, value in db.items()}

    # Filter out users with a score of 0
    scores = {user_id: score for user_id, score in scores.items() if score != 0}
    if not scores:
        respond("There are no users with non-zero scores to display.")
        return
    logger.info(f"Scores loaded for leaderboard: {scores}")
    blocks = generate_leaderboard_blocks(scores)

    respond(blocks=blocks, text="Leaderboard")


@app.command("/reflect")
def reflection(ack, respond):
    ack()
    respond("This command is not implemented yet. Please check back later.")


# Start your app
if __name__ == "__main__":
    logger.info("Starting Slack bot listener")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
