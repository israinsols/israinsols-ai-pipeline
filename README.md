# 🚀 Israinsols AI-Powered Lead Pipeline

An enterprise-grade, fully automated lead generation and management ecosystem designed for freelancers and agencies. This project leverages **G0I's high-performance AI models** (MiniMax M2.5, DeepSeek V3, GPT-4o) to automate client outreach and negotiation.

---

## ✨ Key Features

### 🤖 AI-Powered Automation
- **One-Click AI Proposals:** Generates hyper-personalized, high-converting proposals using the beast **MiniMax M2.5** or **GPT-4o** models.
- **AI Negotiation Coach:** Forwards client messages to get strategic advice and "perfect replies" to close deals.
- **Smart Formatting:** Automatic HTML formatting for professional Telegram and Discord alerts.

### 🕵️‍♂️ Advanced Lead Scraping
- **Multi-Source Scraper:** Automated scraping from **Freelancer.com** and other platforms.
- **Persistent Database:** Leads are stored in SQLite/PostgreSQL with deduplication and status tracking.
- **Celery Scheduling:** Background scraping tasks run 24/7 without freezing the main application.

### 📱 Premium Telegram Bot
- **Interactive UI:** Buttons for "Apply Now", "Contacted", "AI Proposal", and "Add Note".
- **Real-time Alerts:** Instant notifications for high-value leads.
- **Pipeline Statistics:** Real-time dashboard for lead volume and status breakdown.

---

## 🤝 AI Coaching & Bot Commands

The Telegram bot is the command center for your pipeline. Here are the available commands:

| Command | Description |
|---------|-------------|
| `/start` | 🏠 Opens the main menu and dashboard. |
| `/recent` | 📋 Shows the latest leads found by the scraper. |
| `/unnotified` | 🔔 List leads that haven't been alerted yet. |
| `/stats` | 📊 Displays real-time pipeline statistics (Total leads, Contacted, etc.). |
| `/scrape` | 🤖 Manually triggers the scraper to find new leads. |
| `/search` | 🔍 Search leads by keywords (e.g., `/search react`). |
| `/proposal` | 📝 **AI Feature**: Generates a high-converting pitch for any job text. |
| `/coach` | 🤝 **AI Feature**: Get negotiation strategy for client messages. |
| `/help` | 📖 Shows the user guide and support info. |

---

## 🛠 Tech Stack

- **Backend:** Python, Django (REST Framework)
- **AI Engine:** G0I.shop (OpenAI Compatible API)
- **Task Queue:** Celery, Redis
- **Database:** SQLite (Development) / PostgreSQL (Production)
- **Communication:** Telegram Bot API (via aiogram), Discord Webhooks
- **Proxy Support:** Cloudflare Workers (for bypassing ISP blocks)

---

## 🛠 Project Structure
```text
israinsols_pipeline/
├── leads/              # Core logic: Bot, Scraper, Tasks
│   ├── bot/            # Telegram handlers & keyboards
│   ├── scraper/        # Scraper logic for Freelancer.com
│   └── tasks.py        # Celery background tasks
├── config/             # Django settings & Celery config
├── manage.py           # Django management script
└── .env                # Secrets & Configurations (Hidden)
```

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/israinsols/israinsols-ai-pipeline.git
cd israinsols-pipeline
```

### 2. Set Up Environment
Create a `.env` file from the provided template:
```env
TELEGRAM_BOT_TOKEN=your_token
G0I_API_KEY=your_g0i_key
G0I_MODEL=gpt-4o-a
REDIS_URL=redis://localhost:6379/0
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Engine
```bash
# Start Django
python manage.py migrate
python manage.py runserver

# Start Bot
python manage.py run_bot

# Start Celery (for automation)
python start_celery.py
```

---

