# Word Ban ![Hackatime badge](https://hackatime-badge.hackclub.com/U08D22QNUVD/word_ban)
## What is it?
Word ban is a slackbot that lets you ban words in specific channels like "dog" in your cat channel.  
I made it cuz I saw people say that specific words are banned, even though they aren't illegal or swears or whatever, just for funny reasons  
so I made a bot to automatically say "this word is banned".  

## What commands are there?
Check out the commands in [commands.md](Commands.md)!  
Or just ping it (@Word Ban) and talk naturally and it will help you! (This feature is powered by ai.hackclub.com)

## What can it do?
As I mentioned above, it just says this word x is banned when that word is banned. So obviously you can ban/unban words, but also you can see a score!  
Yeah so I added a scoring system so your score goes down when you say a banned word, and theres a leaderboard too. That's about everything the bot does!

## MCP-like Self-Awareness Features

Word Ban now has **MCP-like autonomous behavior** - it's fully self-aware and can:

- **Understand its own existence**: I hope it doesn't spiral into existential dread or smth
- **Make autonomous decisions**: Only if you ask it to
- **Introspect on its state**: Use `/self-awareness` to see the bot explain its current state and reasoning (you become its therapist ig)

### How it works
When you mention @Word Ban, it:
1. Analyzes your message and conversation context
2. Decides if an autonomous action is appropriate
3. Executes the action if needed (with transparency)
4. Responds conversationally with its teenage personality

This makes interactions more natural - just talk to the bot and it will figure out what to do!

## How to self-host
### Here is a guide to self-host the bot:
1. Download the code
2. Run `pip install -m requirements.txt`
3. Create a `.env` file and add `SLACK_BOT_TOKEN=` with your Slack bot token, and `SLACK_APP_TOKEN=` with the Slack app token
4. You will need 2 Gemini API keys. One from ai.hackclub.com and one from Google AI Studio. Add the ai.hackclub.com as AI_TOKEN1 and the other as AI_TOKEN2 to the .env file
5. Run `python app.py` or `python3 app.py`
Any issues, please make an issue
