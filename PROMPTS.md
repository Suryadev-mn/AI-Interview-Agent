# AI usage log

This project was developed with OpenAI Codex as an AI-assisted coding partner.

## Key prompts and outcomes

### Product brief

> Build an AI Interview Agent for a 31-day enterprise AI engineering cohort. It must conduct a realistic multi-turn technical interview tailored to each candidate's completed missions, adapt questions based on responses, ask follow-ups, maintain session context, and provide actionable structured feedback.

Outcome: Designed a session-based interview engine that selects curriculum missions using completion and attempts as learning signals.

### Adaptive assessment behavior

> The interview questions should not be fixed; change them based on the user response.

Outcome: Implemented response analysis against topic signals. Strong replies receive a trade-off probe; weaker replies receive a request-flow and failure-mitigation clarification. The system completes after at least eight scored turns spanning multiple curriculum days.

### Voice experience

> Make the interview agent ask questions directly through audio conversation.

Outcome: Added browser-native Speech Synthesis for spoken questions and Web Speech Recognition for microphone transcription, with a hands-free toggle and text fallback.

### Submission readiness

> Help me match all submission criteria: public repository, deployed URL, and AI usage log.

Outcome: Added this AI usage log, deployment configuration, portable data-path configuration, and repository hygiene guidance.

## Human review and decisions

The developer reviewed the generated implementation, chose the product scope, and is responsible for creating the public GitHub repository and deployment account. No candidate data is sent to third-party AI model APIs by this implementation; assessment currently uses transparent local heuristics.
