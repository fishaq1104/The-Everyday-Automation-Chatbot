# Everyday Automation Chatbot (Discord + Python)

This is a starter implementation of an "Everyday Automation" chatbot focused on one daily pain point:

- Getting useful updates (news + weather)
- Tracking reading habit progress
- Receiving a daily reminder in Discord

It is built to score well against your rubric with:

- Free public API integration (Hacker News + Open-Meteo)
- Clean slash command flow and help menu
- Graceful error handling for invalid inputs and API failures
- Practical habit-tracking with local persistence (SQLite)

## Features

- `/help` - command overview with examples
- `/ping` - bot health check
- `/news [limit]` - top tech news headlines from Hacker News
- `/weather <city>` - weather by city from Open-Meteo
- `/morning_brief <city>` - combined weather + top news summary
- `/read_add <pages> <book>` - save reading progress
- `/read_stats` - total pages, entries, daily pages, and streak
- `/remind_set <HH:MM> [timezone] [message]` - daily reminder in local timezone
- `/remind_off` - disable daily reminder

## Project Structure

```text
.
├── app
│   ├── __init__.py
│   ├── apis.py          # Public API integration + retries/timeouts
│   ├── bot.py           # Discord slash commands + reminder loop
│   ├── config.py        # Env config loader
│   └── database.py      # SQLite storage for reading logs/reminders
├── .env.example
├── .gitignore
├── main.py
├── requirements.txt
└── README.md
```

## What We Used

- Language: Python
- Bot Framework: discord.py
- HTTP Client: aiohttp
- Config Loader: python-dotenv
- Local Database: SQLite (built in)
- Public APIs:
  - Hacker News Firebase API (tech news)
  - Open-Meteo API (weather)

## How To Connect The Bot To Discord

### 1) Create the Discord app and bot user

1. Open Discord Developer Portal.
2. Click New Application.
3. Enter a name (for example: CRAB_Bot).
4. Open Bot from the left menu.
5. Click Add Bot.

### 2) Get the token

1. Stay on the Bot page.
2. In Token section, click Reset Token (or Copy Token).
3. Copy the token.
4. Paste it into the local .env file (never share this token).

### 3) Generate invite URL and add bot to server

1. Open OAuth2 -> URL Generator.
2. In Scopes, select:
	- bot
	- applications.commands
3. In Bot Permissions, select at least:
	- View Channels
	- Send Messages
	- Embed Links
	- Use Slash Commands
4. Copy the generated URL.
5. Open it in browser, select your server, click Authorize.

## Local Setup And Run

### 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure environment variables

```bash
cp .env.example .env
```

Edit .env and set your token:

```env
DISCORD_TOKEN=your_actual_token_here
DATABASE_PATH=data/bot.db
```

### 3) Run the bot

```bash
python main.py
```

Once connected, run `/help` in your Discord server.

## Command Demo Checklist

Use this list during your demo and add one screenshot for each command.

1. /help
2. /news limit:5
3. /weather city:Lagos
4. /read_add pages:20 book:Atomic Habits
5. /read_stats
6. /remind_set time_local:20:00 timezone_name:Africa/Lagos message:Log your reading now
7. /remind_off
8. /morning_brief city:Lagos

## Screenshot Placeholders (Add Your Images)

You can replace each line below with an actual image after testing.

```md
### /help
![help command output](docs/screenshots/help.png)

### /news
![news command output](docs/screenshots/news.png)

### /weather
![weather command output](docs/screenshots/weather.png)

### /read_add
![read_add command output](docs/screenshots/read_add.png)

### /read_stats
![read_stats command output](docs/screenshots/read_stats.png)

### /remind_set
![remind_set command output](docs/screenshots/remind_set.png)

### /remind_off
![remind_off command output](docs/screenshots/remind_off.png)

### /morning_brief
![morning_brief command output](docs/screenshots/morning_brief.png)
```

## Reliability and Error Handling Included

- API requests include timeout + retry behavior
- User-facing error messages for API failures or bad command input
- Slash command types enforce validation (for example, page ranges)
- Catch-all exception handling in each command to prevent crashes
- Reminder scheduler avoids duplicate sends within the same day

## Example Command Flow

1. `/help`
2. `/news limit:5`
3. `/weather city:Lagos`
4. `/read_add pages:20 book:Atomic Habits`
5. `/read_stats`
6. `/remind_set time_local:20:00 timezone_name:Africa/Lagos message:Log your reading now`
7. `/remind_off`
8. `/morning_brief city:Lagos`

## Notes

- Reminders support IANA timezones (for example: `Africa/Lagos`, `Europe/London`, `UTC`).
- Data is stored locally in SQLite at `DATABASE_PATH`.
- News source: Hacker News Firebase API.
- Weather source: Open-Meteo APIs.

This is the Proof it works :
<img width="1310" height="565" alt="image" src="https://github.com/user-attachments/assets/105e551a-a7ce-411f-84c3-f57af8efb3fc" />
<img width="1310" height="565" alt="Screenshot 2026-04-24 125758" src="https://github.com/user-attachments/assets/0deab58c-9bfb-4b39-a934-ebc855299f6f" />
<img width="668" height="577" alt="Screenshot 2026-04-24 125050" src="https://github.com/user-attachments/assets/64ae630e-19ad-4753-a7dc-a0fd155338cc" />
<img width="1007" height="575" alt="Screenshot 2026-04-24 125034" src="https://github.com/user-attachments/assets/ba86ecd4-4813-474f-99ff-bc3a3657f882" />
<img width="744" height="482" alt="Screenshot 2026-04-24 114249" src="https://github.com/user-attachments/assets/e9977153-33c5-4a99-9ce6-730dfee22587" />
<img width="1331" height="581" alt="Screenshot 2026-04-24 124536" src="https://github.com/user-attachments/assets/f244551b-151d-4dc2-aeec-199f68e8cef3" />
<img width="965" height="494" alt="Screenshot 2026-04-24 114052" src="https://github.com/user-attachments/assets/e1461fba-7501-4040-978f-495c96151389" />
<img width="716" height="319" alt="Screenshot 2026-04-24 113754" src="https://github.com/user-attachments/assets/47480925-4dff-4776-9dee-2ce6a5f6b15d" />



