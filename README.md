# Word Ban ![Hackatime badge](https://hackatime-badge.hackclub.com/U08D22QNUVD/word_ban)
## What is it?
Word ban is a slackbot that lets you ban words in specific channels like "dog" in your cat channel.  
I made it cuz I saw people say that specific words are banned, even though they aren't illegal or swears or whatever, just for funny reasons  
so I made a bot to automatically say "this word is banned".  

## What commands are there?
Check out the commands in [commands.md](Commands.md)!  

## What can it do?
As I mentioned above, it just says this word x is banned when that word is banned. So obviously you can ban/unban words, but also you can see a score!  
Yeah so I added a scoring system so your score goes down when you say a banned word, and theres a leaderboard too. That's about everything the bot does!

## How to self-host
### Here is a guide to self-host the bot:
1. Download the code
2. Run `pip install -m requirements.txt`
3. Create a `.env` file and add `SLACK_BOT_TOKEN=` with your slack bot token, and `SLACK_APP_TOKEN=` with the slack app token
4. Run `python app.py` or `python3 app.py`
Any issues, please make an issue
