# Telegram Security Bot

A powerful Telegram bot that helps protect your groups from spam and prohibited links.

## Project Structure

```
telegram-security/
├── main.py              # Main bot code
├── requirements.txt     # Python dependencies
├── .env                # Environment variables (bot token)
├── security_status.json # Security settings for groups
└── README.md           # Project documentation
```

## Features

- Blocks spam messages (more than 10 messages per minute)
- Blocks prohibited links (Telegram, TikTok, Instagram, YouTube, Facebook, Discord, etc.)
- Automatic timeout for violators (15 minutes)
- Admin can unmute users
- Security settings persist across bot restarts
- Easy to use commands

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/telegram-security.git
cd telegram-security
```

2. Install required packages:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file and add your bot token:

```
BOT_TOKEN=your_bot_token_here
```

## Usage

1. Add the bot to your group
2. Make the bot an admin
3. Use the following commands:

- `/security on` - Enable security
- `/security off` - Disable security
- `/security` - Check security status

## Security Features

- **Spam Protection**: Users sending more than 10 messages per minute will be timed out
- **Link Protection**: Blocks various prohibited links including:
  - Telegram links
  - Social media links (TikTok, Instagram, YouTube, Facebook)
  - Discord links
  - Adult content links
- **Automatic Timeout**: 15-minute timeout for violators
- **Admin Controls**: Admins can unmute users using the unmute button

## Requirements

- python-telegram-bot==20.7
- python-dotenv==1.0.0

## Running the Bot

```bash
python main.py
```

## Security Settings

The bot saves security settings in a JSON file (`security_status.json`). This means:

- Security settings persist across bot restarts
- Each group maintains its own security status
- No need to re-enable security after bot restart

##
