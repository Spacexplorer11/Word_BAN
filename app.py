import dbm
import os
import logging

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from utility import is_user_channel_manager

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
    logger.info(f"Received /ban-word from user {body['user_id']} in channel {body['channel_id']} with text '{command['text']}'")
    is_manager, error_occurred = is_user_channel_manager(client, body["user_id"], body["channel_id"])

    if error_occurred:
        logger.error(f"Permissions check failed for user {body['user_id']} in channel {body['channel_id']}")
        respond("Sorry, the service is currently busy due to high traffic. Please try again in a moment.")
        return

    logger.info(f"User {body['user_id']} manager status in channel {body['channel_id']}: {is_manager}")
    if not is_manager:
        logger.warning(f"Unauthorized /ban-word attempt by {body['user_id']} in {body['channel_id']}")
        respond("Sorry, you are not authorized to use this command. If your permissions recently changed, please try again in 5 minutes")
        return

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
    logger.info(f"Processing message from user {message.get('user')} in {channel_id}: '{message.get('text','')}'")
    try:
        with dbm.open("banned_words.db", "r") as db:
            banned_words = list(db.keys())
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
    logger.info(f"Received /unban-word from user {body['user_id']} in channel {body['channel_id']} with text '{command['text']}'")
    is_manager, error_occurred = is_user_channel_manager(client, body["user_id"], body["channel_id"])

    if error_occurred:
        logger.error(f"Permissions check failed for user {body['user_id']} in channel {body['channel_id']}")
        respond("Sorry, the service is currently busy due to high traffic. Please try again in a moment.")
        return

    logger.info(f"User {body['user_id']} manager status in channel {body['channel_id']}: {is_manager}")
    if not is_manager:
        logger.warning(f"Unauthorized /unban-word attempt by {body['user_id']} in {body['channel_id']}")
        respond("Sorry, you are not authorised to use this command. If your permissions recently changed, please try again in 5 minutes")
        return

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
        db.pop(word_key)
        logger.info(f"Unbanned word '{command['text'].strip()}' for channel {body['channel_id']}")
        respond(f"The word '{command['text'].strip()}' was unbanned.")


# Start your app
if __name__ == "__main__":
    logger.info("Starting Slack bot listener")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
