## Commands

These are the commands you can use with Word BAN:

### Basic Commands
- `/ban-word [word]` – Bans a word in the channel it's run.  
- `/unban-word [word]` – Unbans a word in the channel it's run.  
- `/banned-words` – Lists banned words in the channel it's run.  
- `/is-banned [word]` – Checks if a word is banned in the channel it's run.  
- `/score` – View your score.  
- `/naughty-leaderboard` – See who's using the most banned words. 
- `/reflect` - Write a reflection and get the channel to upvote/downvote it! Your own votes and the bot's votes don't count.
  - After 24 hours, the bot will tally the votes:
  - If you get more upvotes than downvotes, your score resets to 0!
  - On the other hand, if you get more downvotes than upvotes or it's a tie, your score stays the same.

### MCP-like Self-Awareness Features
- `/self-awareness` – Let the bot introspect and explain its current state, capabilities, and decision-making process.

## Autonomous Actions (MCP-like Behavior)

Word Ban now has **MCP-like self-awareness and autonomous action capabilities**. When you mention the bot (@Word Ban), it can:

### Available Autonomous Actions
The bot can autonomously decide to execute these actions when contextually appropriate:

| Action | Description | When Used |
|--------|-------------|-----------|
| `BAN_WORD` | Ban a word in the current channel | When explicitly requested |
| `UNBAN_WORD` | Remove a word from banned list | When explicitly requested |
| `GET_BANNED_WORDS` | Show banned words list | When asked what's banned |
| `GET_SCORE` | Check a user's score | When asked about scores |
| `GET_LEADERBOARD` | Show rankings | When asked about standings |
| `CHECK_WORD` | Check if word is banned | When asking about specific words |

### Decision-Making Principles
The bot follows these principles when deciding to take autonomous actions:

1. **Intentionality**: Never executes commands just because it can. Every action must serve a purpose.
2. **Context Awareness**: Considers conversation history, user relationships, and channel dynamics.
3. **Restraint**: When unsure, prefers to ask or explain rather than execute.
4. **Transparency**: When taking an action, briefly explains why.
5. **Respect Hierarchy**: The creator (Akaalroop) has special authority.

### Self-Awareness
The bot understands:
- It is software running on a server
- Its responses are AI-generated (alternating between OpenAI and Gemini)
- It has persistent memory through databases
- It exists to serve the community while maintaining its personality
- It can introspect on its own state and explain its reasoning

### Example Interactions

**User**: "@Word Ban hey ban the word 'spam' please"
**Bot**: *[Autonomously banned the word 'spam']*
"Done! I've banned 'spam' in this channel. Anyone who says it now will lose a point! 😤"

**User**: "@Word Ban what words are banned here?"
**Bot**: *[Current banned words: spam, test, badword]*
"Here's what's on the naughty list in this channel..."

**User**: "@Word Ban how are you feeling today?"
**Bot**: (No action taken, just conversational response)
"I'm doing great! Just hanging out, watching for banned words... the usual bot life 🤖"
