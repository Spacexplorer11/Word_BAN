import dbm
import json
import logging
import os
import re
import time
from threading import RLock

from dotenv import load_dotenv
from openai import OpenAI
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError

load_dotenv()

# --- Reflection and Score Caches (thread-safe) ---
reflection_channel_id = ""
reflections_cache = []
scores_cache = {}
scores_lock = RLock()
reflections_lock = RLock()


# Load all unprocessed reflections into memory
def load_pending_reflections():
    loaded = []
    with dbm.open("reflections.db", "c") as db:
        for key in db.keys():
            record = json.loads(db[key].decode())
            if not record.get("processed", False):
                loaded.append(record)
    return loaded


def load_scores():
    loaded = {}
    with dbm.open("scores.db", "c") as db:
        for k, v in db.items():
            loaded[k.decode()] = int(v)
    return loaded


reflections_cache = load_pending_reflections()
scores_cache = load_scores()

# Initialises your app with your bot token and socket mode handler
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Akaalroop Intelligence trust trust

AI_TOKEN = os.environ.get("AI_TOKEN")
AI_MODEL = "google/gemini-2.5-flash"
AI_URL = "https://ai.hackclub.com/proxy/v1"

client = OpenAI(
    api_key=AI_TOKEN,
    base_url=AI_URL
)


def ai_request(prompt):
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "assistant",
             "content": f"You are a bot called Word Ban. You are open source and your code is at https://github.com/Spacexplorer11/Word_BAN/ You are used to ban words in a Slack channel. You have a teenage boy personality. The user has given a prompt to you. Please respond appropriately as your response will be sent directly, word for word, to the user. Please keep responses short and conscise. Please use slack mrkdwn. User Prompt (+ a bit extra user metadata): {prompt}"}
        ]
    )
    return response.choices[0].message.content


# --- Initialise in-memory caches once ---
# Thread-safe lock for banned words cache
banned_lock = RLock()


def mark_reflection_processed(key: str):
    with dbm.open("reflections.db", "c") as db:
        if key.encode() in db:
            record = json.loads(db[key].decode())
            record["processed"] = True
            db[key] = json.dumps(record)


def generate_leaderboard_blocks(scores: dict) -> list:
    """
    Given a dict of user_id -> score, returns Slack blocks showing top 10 users with their scores and mentions.
    """
    # Sort by score descending and take top 10
    sorted_users = sorted(scores.items(), key=lambda x: -x[1], reverse=True)[:10]

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


# Thread-safe banned words cache
banned_words_cache = load_banned_words()


@app.event("app_mention")
def handle_mention_event(body, say, logger):
    user_id = body["event"]["user"]
    text = body["event"].get("text", "")
    channel_id = body["event"]["channel"]
    logger.info(f"User {user_id} mentioned the bot in {channel_id}: {text}")

    text_without_mention = re.sub(r"<@[^>]+>", "", text).strip()

    command = ai_request(f"""Identify if the following prompt is a command the bot can execute or a general message."
                         Rules: 
                         Respond with MESSAGE if it's a general message.
                         Respond with SCORE if they are asking for their score.
                         Respond with LEADERBOARD if they are asking for the leaderboard.
                         Respond with BAN_WORD if they are asking to ban a word.
                         Respond with UNBAN_WORD if they are asking to unban a word.
                         Respond with BANNED_WORDS if they are asking for the list of banned words.
                         Respond with REFLECT if they are asking to submit a reflection.
                         Respond with HELP if they are asking for what you can do or what commands you can execute.
                         Only respond with one of the above keywords and absolutely NOTHING else.
                         Prompt: {text_without_mention}""")

    if command == "MESSAGE":
        pass
    elif command == "SCORE":
        score(ack=lambda: None, respond=lambda msg: say(msg), body={"user_id": user_id, "channel_id": channel_id})
        return
    elif command == "LEADERBOARD":
        say("Please use the `/naughty-leaderboard` command to view the leaderboard.")
        return
    elif command == "BAN_WORD":
        say("To ban a word, please use the `/ban-word` command followed by the word you want to ban.")
        return
    elif command == "UNBAN_WORD":
        say("To unban a word, please use the `/unban-word` command followed by the word you want to unban.")
        return
    elif command == "BANNED_WORDS":
        list_banned_words(ack=lambda: None, respond=lambda **kwargs: say(**kwargs), body={"channel_id": channel_id})
        return
    elif command == "REFLECT":
        say("To submit a reflection, please run the `/reflect` command")
        return
    elif command == "HELP":
        say("Please check my commands at commands.md here: https://github.com/Spacexplorer11/Word_BAN/blob/main/Commands.md")
        return

    if user_id == "U08D22QNUVD":
        say(ai_request(
            f"User {user_id} said {text_without_mention}. Refer to them as <@{user_id}> in your final output. This is the creator of you (word ban) please talk to him respectfully and nicely. Please respond as if you are owned by him and serve him."))
        return
    elif user_id == "U097SUCKJ90":
        say(ai_request(
            f"User {user_id} said {text_without_mention}. Refer to them as <@{user_id}> in your final output. This is the best friend of the creator of you (word ban) please talk to him with extreme sass and cheekiness. Please respond as if you are dislike him in a bantery way."))
        return
    elif user_id == "U09192704Q7":
        say(ai_request(
            f"User {user_id} said {text_without_mention}. Refer to them as <@{user_id}> in your final output. This is a friend of the creator of you (word ban) please talk to him with a touch of sass."))
        return

    say(ai_request(
        f"User {user_id} said {text_without_mention}. Respond appropriately to the prompt. Refer to them as <@{user_id}> in your final output."))


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
def handle_message_events(logger, message, say, client):
    """
    Handles incoming messages and checks for banned words and emojis.
    Optimized: uses in-memory caches for scores and reflections, and thread-safe update.
    """
    channel_id = message.get("channel")
    user_id = message.get("user")
    raw_text = message.get("text", "")

    # Flatten message: lowercase, strip all non-alphanumeric and non-colon characters (removes underscores, dashes, etc.), no whitespace removal
    flattened = re.sub(r"[^a-zA-Z0-9:]", "", raw_text.lower())
    logger.info(f"Message after processing in {channel_id}: {flattened}")

    penalised = False
    with banned_lock:
        banned_set = banned_words_cache.get(channel_id, set())
        for word in banned_set:
            if word in flattened:
                with scores_lock:
                    old = scores_cache.get(user_id, 0)
                    new = old - 1
                    scores_cache[user_id] = new
                    try:
                        with dbm.open("scores.db", "c") as scores_db:
                            scores_db[user_id] = str(new)
                    except Exception as e:
                        logger.error(f"Failed to write score for {user_id}: {e}")
                say(
                    text=f":siren-real: The {'emoji' if word.startswith(':') and word.endswith(':') else 'word'} '{word}' is banned! Score: {new}.",
                    thread_ts=message.get("ts")
                )
                logger.info(f"Penalised {user_id} for '{word}' in {channel_id}")
                penalised = True
                break
    # Ensure user has a score entry in cache
    with scores_lock:
        if user_id not in scores_cache:
            scores_cache[user_id] = 0
            try:
                with dbm.open("scores.db", "c") as scores_db:
                    scores_db[user_id] = "0"
            except Exception as e:
                logger.error(f"Failed to initialize score for {user_id}: {e}")
    # Reflection processing is now handled in a background scheduler.


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

    # Use in-memory cache for scores
    with scores_lock:
        score = scores_cache.get(user_id, 0)
    logger.info(f"User {user_id} has a score of {score}")
    respond(f"Your current score is: {score}")


@app.command("/naughty-leaderboard")
def leaderboard(ack, respond, body):
    ack()
    logger.info(f"Received /leaderboard from user {body['user_id']} in channel {body['channel_id']}")
    # Use in-memory cache for scores
    with scores_lock:
        scores = {user_id: score for user_id, score in scores_cache.items() if score != 0}
    if not scores:
        respond("There are no users with non-zero scores to display.")
        return
    logger.info(f"Scores loaded for leaderboard: {scores}")
    blocks = generate_leaderboard_blocks(scores)
    respond(blocks=blocks, text="Leaderboard")


@app.command("/reflect")
def reflection(ack, respond, body):
    ack()
    global reflection_channel_id
    reflection_channel_id = body.get("channel_id")
    logger.info(f"Received /reflect command from user {body['user_id']} in channel {body['channel_id']}")
    # Use in-memory cache for pending reflections
    with reflections_lock:
        for reflection in reflections_cache:
            if not reflection.get("processed", False) and reflection.get("user") == body["user_id"]:
                respond(
                    "You already have a pending reflection. Please wait for it to be processed before submitting another.")
                return

    app.client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "reflect_modal",
            "title": {
                "type": "plain_text",
                "text": "Reflection"
            },
            "submit": {
                "type": "plain_text",
                "text": "Submit"
            },
            "close": {
                "type": "plain_text",
                "text": "Cancel"
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "reflection_input_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "reflection_input"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Please type your reflection below:"
                    }
                }
            ]
        }
    )


@app.view("reflect_modal")
def handle_reflect_submission(ack, body, view, client, logger):
    ack()
    user = body["user"]["id"]
    reflection = view["state"]["values"]["reflection_input_block"]["reflection_input"]["value"]

    try:
        client.chat_postEphemeral(
            channel=reflection_channel_id,
            user=user,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Reflection Preview:*\n>{reflection}"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": ":warning: This reflection will be saved in our database if you confirm. It will also be stored alongside other metadata such as your user ID which is directly linked with your reflection. Please ensure you are comfortable with this before confirming."
                        }
                    ]
                },
                {
                    "type": "actions",
                    "block_id": "reflection_confirm_block",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Confirm"
                            },
                            "style": "primary",
                            "value": reflection,
                            "action_id": "reflect_confirm"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Cancel"
                            },
                            "style": "danger",
                            "action_id": "reflect_cancel"
                        }
                    ]
                }
            ],
            text="Reflection preview"
        )
    except SlackApiError as e:
        logger.error(f"Failed to send confirmation: {e}")


# Handler for confirmation button
@app.action("reflect_confirm")
def confirm_reflection(ack, body, client, logger, say):
    ack()
    user = body["user"]["id"]
    reflection_text = body["actions"][0]["value"]

    # Check in-memory cache for user pending reflection
    with reflections_lock:
        for reflection in reflections_cache:
            if not reflection.get("processed", False) and reflection.get("user") == user:
                say("You already have a pending reflection. Please wait for it to be processed before submitting another.")
                return

    timestamp = int(time.time())
    key = f"{user}:{timestamp}"
    try:
        response = client.chat_postMessage(
            channel=reflection_channel_id,
            text=f"*New Reflection by <@{user}>:*\n>{reflection_text}"
        )
        ts = response["ts"]
    except Exception as e:
        logger.error(f"Failed to post reflection: {e}")
        return

    record = {
        "user": user,
        "reflection": reflection_text,
        "created_at": timestamp,
        "channel": reflection_channel_id,
        "ts": ts,
        "processed": False,
    }
    # Save to DB and in-memory cache (thread-safe)
    try:
        with dbm.open("reflections.db", "c") as db:
            db[key] = json.dumps(record)
    except Exception as e:
        logger.error(f"Failed to store reflection in DB: {e}")
    with reflections_lock:
        reflections_cache.append(record)
    try:
        client.reactions_add(channel=reflection_channel_id, timestamp=ts, name="upvote")
        client.reactions_add(channel=reflection_channel_id, timestamp=ts, name="downvote")
        client.chat_postMessage(
            channel=reflection_channel_id,
            text="Everyone please upvote or downvote this reflection!"
        )
    except Exception as e:
        logger.error(f"Failed to add reactions or prompt message: {e}")


@app.action("reflect_cancel")
def cancel_reflection(ack, body, client, logger):
    ack()
    user = body["user"]["id"]
    # Try to determine the channel to send ephemeral to
    channel = None
    # If ephemeral, channel is in body['container']['channel_id']
    if "container" in body and "channel_id" in body["container"]:
        channel = body["container"]["channel_id"]
    elif "channel" in body and "id" in body["channel"]:
        channel = body["channel"]["id"]
    # fallback: try reflection_channel_id
    if not channel:
        channel = reflection_channel_id
    try:
        client.chat_postEphemeral(
            channel=channel,
            user=user,
            text=":x: Reflection cancelled. Your reflection was not stored."
        )
    except Exception as e:
        logger.error(f"Failed to send ephemeral reflection cancel message: {e}")


if __name__ == "__main__":
    import threading


    def process_pending_reflections():
        """
        Periodically checks for pending reflections and processes them.
        """
        try:
            from slack_sdk import WebClient
            slack_token = os.environ.get("SLACK_BOT_TOKEN")
            if not slack_token:
                logger.error("SLACK_BOT_TOKEN not set in environment")
                return
            client = WebClient(token=slack_token)
        except Exception as e:
            logger.error(f"Could not create Slack WebClient: {e}")
            return

        while True:
            now = time.time()
            to_process = []
            with reflections_lock:
                for reflection in reflections_cache:
                    if not reflection.get("processed", False) and now > reflection["created_at"] + 86400:
                        to_process.append(reflection)
            for reflection in to_process:
                try:
                    reflection_id = reflection["ts"]
                    response = client.reactions_get(channel=reflection['channel'], timestamp=reflection_id)
                    reactions = response["message"].get("reactions", [])
                    upvotes = 0
                    downvotes = 0
                    for reaction in reactions:
                        # Only count votes from users other than the reflection's author
                        if reaction["name"] == "upvote":
                            upvotes = len([u for u in reaction["users"] if u != reflection["user"]])
                        elif reaction["name"] == "downvote":
                            downvotes = len([u for u in reaction["users"] if u != reflection["user"]])
                    response = client.conversations_open(users=reflection['user'])
                    dm_channel_id = response["channel"]["id"]
                    if upvotes > downvotes:
                        logger.info(
                            f"Majority agreed and upvoted the reflection by {reflection['user']} which was {reflection['reflection']}")
                        client.chat_postMessage(
                            channel=dm_channel_id,
                            text=f":whitecheckmark: Your reflection '{reflection['reflection']}' received more upvotes than downvotes! \n This means your score was reset to 0!"
                        )
                        with scores_lock:
                            scores_cache[reflection['user']] = 0
                            try:
                                with dbm.open("scores.db", "c") as scores_db:
                                    scores_db[reflection['user']] = "0"
                            except Exception as e:
                                logger.error(f"Failed to reset score for {reflection['user']}: {e}")
                    elif downvotes > upvotes:
                        logger.info(
                            f"Majority disagreed and downvoted the reflection by {reflection['user']} which was {reflection['reflection']}")
                        client.chat_postMessage(
                            channel=dm_channel_id,
                            text=f":x: Your reflection '{reflection['reflection']}' received more downvotes than upvotes! \n This means your score was not reset to 0 and instead remains the same. You may try again."
                        )
                    else:
                        logger.info(
                            f"The was a tie for the reflection by {reflection['user']} which was {reflection['reflection']}")
                        client.chat_postMessage(
                            channel=dm_channel_id,
                            text=f"Your reflection '{reflection['reflection']}' received the same amount of upvotes and downvotes! \n This means your score stays the same. You may try again."
                        )
                    mark_reflection_processed(f"{reflection['user']}:{reflection['created_at']}")
                    with reflections_lock:
                        reflection["processed"] = True
                    try:
                        with dbm.open("reflections.db", "c") as db:
                            key = f"{reflection['user']}:{reflection['created_at']}"
                            if key.encode() in db:
                                db[key] = json.dumps(reflection)
                    except Exception as e:
                        logger.error(f"Failed to mark reflection processed in DB: {e}")
                except Exception as e:
                    logger.error(f"Error processing reflection {reflection}: {e}")
            time.sleep(180)


    reflection_thread = threading.Thread(target=process_pending_reflections, daemon=True)
    reflection_thread.start()

    logger.info("Starting Slack bot listener")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
