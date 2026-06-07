# 🤖 Jarvis AI Assistant

A full-stack, voice-enabled AI personal assistant built with Django. Talk naturally in English, Kannada, or mixed Kannada-English — Jarvis listens, thinks, and speaks back.

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.0-green?logo=django&logoColor=white)
![AI](https://img.shields.io/badge/AI-Gemini%20%7C%20Groq%20%7C%20OpenAI-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Features

| Feature | Description |
|---|---|
| 💬 **AI Chat** | Multi-turn conversations with persistent history. Powered by Gemini, Groq, or OpenAI. |
| 🧠 **Memory System** | Jarvis remembers your name, preferences, goals, and context across sessions. |
| 🎤 **Voice Assistant** | Animated orb interface — speak naturally and Jarvis responds with voice. |
| 🗂️ **Knowledge Vault** | Upload PDF, DOCX, PPTX, TXT — ask questions about your documents. |
| 📝 **Resume Analysis** | Upload your resume and get detailed feedback, skill extraction, and interview questions. |
| 🌐 **Multi-Language** | English, Kannada, and mixed Kannada-English ("Kanglish") support. |
| 🔐 **Authentication** | User registration, login, logout with session management. |
| 📊 **Dashboard** | Overview of your chat sessions, memories, documents, and AI usage. |
| ⚙️ **Voice Settings** | Configure voice gender, speed, pitch, language, and auto-speak. |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.13, Django 6.0 |
| **AI Providers** | Google Gemini 2.5 Flash (free), Groq LLaMA 3.3 70B (free), OpenAI GPT-4o-mini |
| **Speech** | Web Speech API (browser-native STT + TTS) |
| **Document Processing** | pypdf, python-docx, python-pptx |
| **Frontend** | Bootstrap 5, Bootstrap Icons, vanilla JS |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Static Files** | WhiteNoise |
| **Deployment** | Gunicorn, Render / Railway |

---

## 📸 Screenshots

> _Add your screenshots here after running the app._

| Dashboard | Voice Assistant | Chat |
|---|---|---|
| ![Dashboard](screenshots/dashboard.png) | ![Voice](screenshots/voice.png) | ![Chat](screenshots/chat.png) |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- pip

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/jarvis-ai-assistant.git
cd jarvis-ai-assistant
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
SECRET_KEY=your-random-secret-key
DEBUG=True
GEMINI_API_KEY=your-gemini-key    # Free at aistudio.google.com
GROQ_API_KEY=your-groq-key        # Free at console.groq.com
```

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Start the server

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000** in your browser.

---

## 🎤 Voice Assistant Usage

1. Navigate to **Voice** in the navbar
2. Click the **green orb** or press **Ctrl+M** to start listening
3. Speak your request — Jarvis transcribes, processes, and speaks the response
4. Use **Quick Action** chips for common tasks: Write Email, Interview Prep, Daily Plan
5. Select a document from the dropdown to ask questions about it

### Voice Commands

| Say this | What happens |
|---|---|
| "Open dashboard" | Navigates to Dashboard |
| "Open memory" | Navigates to Memory |
| "Stop speaking" | Cancels current TTS |
| "New chat" | Creates a new chat session |

---

## 📁 Project Structure

```
jarvis-ai-assistant/
├── assistant/                # Main Django app
│   ├── models.py            # User, Chat, Memory, Document, Voice models
│   ├── views.py             # All view functions
│   ├── urls.py              # URL routing
│   ├── ai_service.py        # Multi-provider AI integration
│   ├── memory_service.py    # Memory extraction + injection
│   ├── document_service.py  # PDF/DOCX/PPTX text extraction
│   ├── forms.py             # Django forms
│   └── admin.py             # Admin panel configuration
├── jarvis_ai/               # Django project settings
│   ├── settings.py          # Production-ready settings
│   ├── urls.py              # Root URL config
│   └── wsgi.py              # WSGI entry point
├── templates/               # HTML templates
│   ├── base.html            # Base layout
│   └── assistant/           # App templates
├── static/                  # CSS + JS
│   ├── css/
│   └── js/
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
├── Procfile                 # Deployment process file
├── runtime.txt              # Python version
└── README.md                # This file
```

---

## ☁️ Deployment

### Deploy to Render

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Configure:
   - **Build Command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - **Start Command:** `gunicorn jarvis_ai.wsgi`
5. Add environment variables in Render dashboard:
   - `SECRET_KEY` (generate a random one)
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = `your-app.onrender.com`
   - `CSRF_TRUSTED_ORIGINS` = `https://your-app.onrender.com`
   - `GEMINI_API_KEY` / `GROQ_API_KEY`

### Deploy to Railway

1. Push your code to GitHub
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
3. Railway auto-detects Django. Add environment variables:
   - Same as Render above
4. Railway auto-runs `Procfile`

---

## 🗺️ Future Roadmap

- [ ] 🔗 **Google Calendar integration** — schedule events via voice
- [ ] 📧 **Email integration** — send emails through Jarvis
- [ ] 📱 **PWA support** — installable on mobile
- [ ] 🧪 **Unit tests** — full test coverage
- [ ] 🐘 **PostgreSQL** — production database
- [ ] 🔄 **WebSocket chat** — real-time streaming responses
- [ ] 🌍 **Hindi + Tamil** — additional language support
- [ ] 📈 **Analytics dashboard** — usage statistics and insights

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 👨‍💻 Author

**Sudhee** — Built with ❤️ as a personal AI assistant project.

---

> _"Hegiddiya Jarvis?" — "Channagiddini! Nimage hege help maadali?"_ 🎤
