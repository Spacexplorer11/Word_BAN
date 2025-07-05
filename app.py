import dbm
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from utility import is_user_channel_manager

load_dotenv()

# Initializes your app with your bot token and socket mode handler
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
)


@app.command("/ban-word")
def ban_word(ack, command, respond, client, body):
    """
    Bans a word, but only if the user is a channel manager.
    Permissions are cached for 5 minutes.
    """
    ack()
    user_id = body["user_id"]
    channel_id = body["channel_id"]

    is_manager, error_occurred = is_user_channel_manager(client, user_id, channel_id)

    if error_occurred:
        respond("Sorry, the service is currently busy due to high traffic. Please try again in a moment.")
        return

    if not is_manager:
        respond(
            "Sorry, you are not authorized to use this command. If your permissions recently changed, please try again in 5 minutes")
        return

    with dbm.open("banned_words.db", "c") as db:
        word = command["text"].strip()
        if not word:
            respond("Please provide a word to ban.")
            return
        if word in db:
            respond(f"The word '{word}' is already banned.")
        else:
            db[word] = "banned"
            respond(f"The word '{word}' has been banned.")


@app.message()
def handle_message_events(logger, message, say):
    """
    Handles incoming messages and checks for banned words.
    """
    with dbm.open("banned_words.db", "c") as db:
        banned_words = list(db.keys())
        for word in banned_words:
            if word.decode('utf-8') in message.get('text', ''):
                say(text=f"Warning: The word '{word.decode('utf-8')}' is banned in this channel.",
                    thread_ts=message['ts'])
                logger.info(
                    f"The word '{word.decode('utf-8')}' was used and is banned in channel {message['channel']} by user {message['user']}.")
                break


@app.command("/unban-word")
def unban_word(ack, command, respond, client, body):
    """
    Unbans a word, but only if the user is a channel manager.
    Permissions are cached for 5 minutes.
    """
    ack()
    user_id = body["user_id"]
    channel_id = body["channel_id"]

    is_manager, error_occurred = is_user_channel_manager(client, user_id, channel_id)

    if error_occurred:
        respond("Sorry, the service is currently busy due to high traffic. Please try again in a moment.")
        return

    if not is_manager:
        respond(
            "Sorry, you are not authorized to use this command. If your permissions recently changed, please try again in 5 minutes")
        return

    with dbm.open("banned_words.db", "c") as db:
        word = command["text"].strip()
        if not word:
            respond("Please provide a word to unban.")
            return
        if word not in db:
            respond(f"The word '{word}' is not banned.")
            return
        if word in db:
            db.pop(word)
            respond(f"The word '{word}' was unbanned.")


# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
