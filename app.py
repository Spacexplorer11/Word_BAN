import dbm
import logging
import os
import string

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
def ban_word(ack, command, respond, body):
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
    user_id = message['user']
    logger.info(f"Processing message from user {message.get('user')} in {channel_id}: '{message.get('text', '')}'")
    try:
        with dbm.open("scores.db", "c") as scores_db:
            with dbm.open("banned_words.db", "r") as db:
                banned_words = tuple(db.keys())
                for word in banned_words:
                    # Check if the word is banned in the current channel
                    if f"{channel_id}:".encode('utf-8') in word:
                        # Remove the channel ID from the word
                        word = word.split(f"{channel_id}:".encode('utf-8'))[1]
                        text_cleaned = message.get('text', '').translate(
                            str.maketrans('', '', string.punctuation)).lower()
                        if word.decode('utf-8') in text_cleaned:
                            say(text=f":siren-real: :siren-real: The word '{word.decode('utf-8')}' is banned in this channel! You have been penalised. \n Your score has been reduced by 1. It is now {int(scores_db.get(user_id, 0)) - 1}.",
                                thread_ts=message['ts'])
                            logger.info(
                                f"The word '{word.decode('utf-8')}' was used and is banned in channel {message['channel']} by user {message['user']}.")
                            if user_id in scores_db:
                                scores_db[user_id] = str(int(scores_db[user_id]) - 1)
                            else:
                                scores_db[user_id] = "-1"
                            break
            if user_id not in scores_db:
                scores_db[user_id] = "0"
    except FileNotFoundError as e:
        logger.warning(f"Banned words DB missing when handling message: {e}")


@app.command("/unban-word")
def unban_word(ack, command, respond, body):
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


@app.command("/leaderboard")
def leaderboard(ack, respond, body):
    ack()
    respond("This command is not implemented yet. Please check back later.")


@app.command("/reflect")
def reflection(ack, respond, body):
    ack()
    respond("This command is not implemented yet. Please check back later.")


# Start your app
if __name__ == "__main__":
    logger.info("Starting Slack bot listener")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
