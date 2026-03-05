# 🤖 Zuri — Your AI Best Friend & Assistant

Zuri is a full-featured, private-first AI chatbot application with a beautiful, minimalist UI. It allows you to toggle seamlessly between **Google Gemini (Cloud)** for fast, powerful intelligence and **Ollama (Local)** for completely private, offline AI generation. 

Built with **FastAPI** (Backend) and vanilla **HTML/CSS/JS** (Frontend), Zuri acts not just as a chatbot, but as a dynamic companion capable of adopting different personas, studying with you, summarizing videos, and operating directly from your web browser or as an installed desktop/mobile app (PWA).

---

## ✨ Features

- **🌐 Cloud vs. Local Toggle:** Instantly switch between `gemini-2.5-flash-lite` (via API key) and local Ollama (`llama3.1`, `llava`) for 100% offline, private chats.
- **🎭 Multi-Persona System:** Zuri can instantly change her personality. Choose between: *Best Friend*, *Coding Tutor*, *Therapist*, *Study Buddy*, or *Creative Writer*.
- **🌓 Dark Mode & Custom Themes:** A sleek, fully featured Dark Mode toggle that saves your preference locally.
- **📱 PWA (Progressive Web App) Ready:** Install Zuri directly to your phone's home screen or your Mac/PC as a native-feeling application with offline caching capabilities.
- **🎓 Interactive Study Mode:** Ask Zuri for a topic, and she will generate interactive, flippable Flashcard Quizzes for you to study on the fly.
- **🎤 Continuous Voice Typing:** Speak naturally! The microphone utilizes continuous Speech Recognition to type out what you say in real-time.
- **🔊 Text-to-Speech (TTS):** Zuri can read her responses out loud to you using natural browser voices.
- **📸 Vision & Screen Capture:** 
  - Upload images directly.
  - Automatically capture your screen/window to ask Zuri what you're looking at.
  - (When using Local mode with images, the `llava` vision model is automatically used).
- **📎 Document Context:** Upload `.txt` or `.pdf` files. Zuri instantly extracts the text and uses it as context to answer your questions.
- **📺 YouTube Summarization:** Paste a YouTube link, and Zuri will automatically fetch the transcript and provide a clean, bulleted summary.
- **💾 Persistent Memory:** Zuri remembers previous topics in your chat gracefully using SQLite and auto-summarization to prevent context bloating.

---

## 🛠️ Tech Stack

- **Backend:** Python 3, FastAPI, SQLite (for memory & auth), PyMuPDF (PDF parsing), `google-generativeai`, `ollama` Python client.
- **Frontend:** Vanilla HTML, CSS (`index.html`, minimal CSS variables), Vanilla JavaScript, Marked.js (Markdown), Highlight.js (Code highlighting).

---

## 🚀 Getting Started

### Prerequisites

1. **Python 3.9+** installed on your machine.
2. An active **Google Gemini API Key**. Get one at [Google AI Studio](https://aistudio.google.com/).
3. *(Optional but Recommended)* **Ollama** installed on your machine for offline models. Download from [ollama.com](https://ollama.com/).

### Installation

1. **Clone or Download the repository.**

2. **Set up your environment variables.**
   Inside the `backend/` folder, create a `.env` file and add your Gemini API Key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

3. **Install Python dependencies.**
   Navigate to the `backend/` directory in your terminal and run:
   ```bash
   pip install fastapi uvicorn google-generativeai python-dotenv pymupdf bcrypt ollama youtube-transcript-api python-multipart
   ```

4. **Pull Local Models (Optional, for Offline Mode).**
   If you want to use the local Llama toggle and Vision features, open a fresh terminal and run:
   ```bash
   ollama pull llama3.1
   ollama pull llava
   ```

### Running the App

1. Navigate to the `backend/` folder in your terminal.
2. Start the FastAPI server using Uvicorn:
   ```bash
   uvicorn main:app --reload
   ```
3. Open your web browser and go to:
   ```
   http://localhost:8000
   ```
   *(The frontend HTML/PWA assets are automatically served from the root URL).*

---

## 🧠 Using the App

- **Login / Register:** The very first time you open the app, it will ask you to register a username and password (saved locally in `chat_memory.db`).
- **Changing Personas:** Use the dropdown on the left sidebar to dictate how Zuri should respond to you.
- **PWA Installation:** Look for the "Install" icon in your browser's URL bar (usually on the right side in Chrome/Edge, or "Add to Dock" in Safari) to install Zuri as an independent app window!

Enjoy chatting with Zuri! 🤖✨
