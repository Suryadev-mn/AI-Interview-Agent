# ORBIT — AI Cohort Interview Agent

> Build the interviewer, not the interview.

🚀 **[Live Demo — Try ORBIT]([YOUR_LIVE_DEMO_URL](https://ai-interview-agent-j7ls.onrender.com))**

📂 **[GitHub Repository](YOUR_GITHUB_REPOSITORY_URL)**

Run with Python 3.11+:

```powershell
python server.py
```

Open `http://localhost:8000`. The app reads the supplied JSON files from `C:\Users\Surya\Downloads` by default. To point it elsewhere, set `COHORT_DATA_DIR`.

## Voice interview

After starting an interview, select **Enable hands-free**. Orbit reads each question aloud, listens through the browser microphone, transcribes the answer, and continues automatically. The microphone button provides a one-answer voice capture mode. Speech features use the browser Web Speech API, so Chrome or Edge is recommended; the regular text interview remains available everywhere.

## Required API

`POST /api/interview` supports the supplied contract. Start with `{ "sessionId": "...", "candidate": { ... } }`; send successive `{ "sessionId": "...", "message": "..." }` payloads. It keeps in-memory session context and finishes with structured feedback after at least eight adaptive questions.

The UI adds a convenience `GET /api/candidates` route.
