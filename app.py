import dbm
import logging
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

# Initializes your app with your bot token and socket mode handler
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.command("/ban-word")
def ban_word(ack, command, respond, client, body):
    """
    Bans a word, but only if the user is a channel manager.
    Permissions are cached for 5 minutes.
    """
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
            logger.info(f"Banned word '{command['text'].strip()}' for channel {body['channel_id']}")
            respond(f"The word '{command['text'].strip()}' has been banned.")


@app.message()
def handle_message_events(logger, message, say):
    """
    Handles incoming messages and checks for banned words.
    """
    channel_id = message.get('channel')
    logger.info(f"Processing message from user {message.get('user')} in {channel_id}: '{message.get('text', '')}'")
    try:
        with dbm.open("banned_words.db", "r") as db:
            banned_words = tuple(db.keys())
            for word in banned_words:
                # Check if the word is banned in the current channel
                if f"{channel_id}:".encode('utf-8') in word:
                    # Remove the channel ID from the word
                    word = word.split(f"{channel_id}:".encode('utf-8'))[1]
                    if word.decode('utf-8').lower() in message.get('text', '').lower():
                        say(text=f"Warning: The word '{word.decode('utf-8')}' is banned in this channel.",
                            thread_ts=message['ts'])
                        logger.info(
                            f"The word '{word.decode('utf-8')}' was used and is banned in channel {message['channel']} by user {message['user']}.")
                        break
    except FileNotFoundError as e:
        logger.warning(f"Banned words DB missing when handling message: {e}")


@app.command("/unban-word")
def unban_word(ack, command, respond, client, body):
    """
    Unbans a word, but only if the user is a channel manager.
    Permissions are cached for 5 minutes.
    """
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
            db.pop(word_key)
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
    word = f"{channel_id}:{command.get("text", "").strip().lower()}"
    logger.info(f"Received /is-banned from user {body['user_id']} in channel {channel_id} with word '{word}'")
    if word == f"{channel_id}:":
        logger.warning(f"No word provided by {body['user_id']} in channel {channel_id}")
        respond("Please provide a word to check.")
        return
    with dbm.open("banned_words.db", "r") as db:
        if word in db:
            logger.info(f"The word '{command['text'].strip()}' is banned in channel {channel_id}")
            respond(f"The word '{command['text'].strip()}' is banned in this channel.")
        else:
            logger.info(f"The word '{command['text'].strip()}' is not banned in channel {channel_id}")
            respond(f"The word '{command['text'].strip()}' is not banned in this channel.")


# Start your app
if __name__ == "__main__":
    logger.info("Starting Slack bot listener")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
