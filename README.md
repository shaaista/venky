# AutoPilot AI Assistant

AutoPilot AI Assistant is now a browser-based workspace instead of a Telegram bot.
It gives you a simple chat UI plus structured tool panels for:

- Gmail inbox summaries
- Email drafting and sending
- Google Calendar reminders
- Document and attachment summaries
- Deep research using Tavily plus an LLM

## Browser UI Features

- Chat-style web interface
- Quick action buttons for inbox, research, reminders, and file summaries
- Separate forms for email, reminder, research, and file upload
- Session-based chat history in the browser
- Copy and download buttons for responses
- Helpful and Needs work feedback buttons that update the local learning policy
- Suggested prompts to bootstrap common tasks
- Responsive layout for desktop and mobile
- Light and dark theme toggle
- Browser voice input and response read-aloud when the browser supports the Web Speech API

## How It Works

1. Open the browser UI.
2. Type a free-form request or use one of the tool forms.
3. The backend routes the request to the correct service.
4. Results come back as formatted cards in the chat stream.
5. User feedback updates a lightweight bandit policy and logs Agent Lightning compatible events.

## Environment Setup

Create a `.env` file in the project root:

```env
LLM_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_MODEL=mistralai/mistral-small-3.1-24b-instruct:free
LLM_FALLBACK_MODELS=meta-llama/llama-3.3-70b-instruct:free,openai/gpt-oss-20b:free

TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REFRESH_TOKEN=your-refresh-token

CALENDAR_CLIENT_ID=your-calendar-client-id.apps.googleusercontent.com
CALENDAR_CLIENT_SECRET=your-calendar-client-secret
CALENDAR_REFRESH_TOKEN=your-calendar-refresh-token
```

## Run The App

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the server:

```bash
python main.py
```

Open the UI:

```text
http://127.0.0.1:5000
```

## Smoke Test

Run the local smoke suite:

```bash
python smoke_test.py
```

The script reports:

- `pass` for working features
- `blocked` when external credentials are invalid or missing
- `fail` for actual app defects that need code changes

## Supported Chat Requests

- `Summarize my latest emails`
- `Research AI workflow automation`
- `Remind me tomorrow at 8pm to call the client`
- `Send an email to name@example.com about tomorrow's meeting`

For file summaries, use the upload form in the UI.

## Project Structure

```text
AutoPilot-AI-Assistant-/
|-- agents/
|-- services/
|   |-- assistant_service.py
|-- static/
|   |-- app.js
|   |-- style.css
|-- templates/
|   |-- index.html
|-- utils/
|-- main.py
|-- requirements.txt
|-- README.md
```

## Notes

- This is still a single-user app that uses one Gmail account and one Calendar account from the `.env` file.
- Gmail and Calendar features require valid Google refresh tokens. If you see `invalid_grant`, regenerate them with `python generate_token.py` and `python generate_calendar_token.py`.
- The live app uses a local feedback-driven bandit policy. Agent Lightning package import is not stable on native Windows, so the app exports compatibility logs under `data/` instead of launching the full training stack in-process.
- Multi-user auth, adaptive routing, feedback loops, and learning metrics are still future work.
