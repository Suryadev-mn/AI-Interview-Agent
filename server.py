"""Cohort Interview Agent — dependency-free server and adaptive interview API."""
from __future__ import annotations

import json
import os
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any

ROOT = Path(__file__).parent
DATA_DIR = Path(os.getenv("COHORT_DATA_DIR", ROOT / "data"))
SESSIONS: dict[str, dict[str, Any]] = {}
LOCK = Lock()

TOPIC_KNOWLEDGE = {
    "Embeddings": ["semantic", "vector", "similarity", "cosine", "distance", "chunk"],
    "Vector": ["index", "metadata", "filter", "nearest", "recall", "latency"],
    "Retrieval": ["retrieve", "rerank", "chunk", "hybrid", "precision", "recall", "citation"],
    "RAG": ["retrieve", "context", "ground", "citation", "hallucination", "chunk"],
    "Prompt": ["system", "few-shot", "constraint", "evaluation", "structured", "injection"],
    "Function": ["schema", "validate", "tool", "json", "pydantic", "retry"],
    "Memory": ["history", "summary", "token", "session", "context", "preference"],
    "Agent": ["tool", "router", "delegate", "state", "retry", "trace"],
    "MCP": ["server", "client", "tool", "protocol", "transport", "schema"],
    "Deployment": ["docker", "kubernetes", "health", "scale", "environment", "rollback"],
    "Monitoring": ["metric", "trace", "log", "latency", "error", "dashboard"],
    "Security": ["validate", "auth", "injection", "sanitize", "privacy", "guardrail"],
}


def load_json(name: str) -> Any:
    with (DATA_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


def curriculum_days() -> dict[int, dict[str, Any]]:
    data = load_json("curriculum.json")
    rows = data.get("curriculum", data.get("days", data))
    if isinstance(rows, dict):
        rows = next((v for v in rows.values() if isinstance(v, list)), [])
    return {int(row["day"]): row for row in rows if isinstance(row, dict) and "day" in row}


def topic_for(title: str) -> str:
    lower = title.lower()
    for term in TOPIC_KNOWLEDGE:
        if term.lower() in lower:
            return term
    if "docker" in lower or "kubernetes" in lower:
        return "Deployment"
    if "logging" in lower or "observability" in lower:
        return "Monitoring"
    if "security" in lower or "privacy" in lower:
        return "Security"
    return "RAG"


def quality(answer: str, topic: str) -> tuple[int, list[str]]:
    words = re.findall(r"[a-zA-Z][a-zA-Z-]+", answer.lower())
    hits = sorted(set(words) & set(TOPIC_KNOWLEDGE.get(topic, [])))
    score = min(4, len(hits)) + (1 if len(words) >= 35 else 0) + (1 if any(x in answer.lower() for x in ["because", "trade-off", "tradeoff", "for example"]) else 0)
    return min(score, 5), hits


def make_question(session: dict[str, Any], mission: dict[str, Any], followup: bool = False) -> str:
    day = mission["day"]; title = mission["title"]; topic = topic_for(title)
    objective = session["days"].get(day, {}).get("objectives", ["Explain the engineering decisions involved"])[0]
    prior = session["answers"][-1] if session["answers"] else None
    if followup and prior:
        if prior["score"] >= 3:
            return f"Good direction. Now make it concrete: for Day {day} — {title}, what trade-off would you measure before choosing your approach, and what would make you change course?"
        return f"Let’s unpack that. In your Day {day} work on {title}, walk me through the request flow end-to-end and name one failure mode plus its mitigation."
    prompts = {
        "Embeddings": "Explain how embeddings turn a user question into useful retrieval, and how you would decide chunk size.",
        "Vector": "How would you design a vector index and metadata filters for accurate, low-latency retrieval?",
        "Retrieval": "Describe a retrieval pipeline you would ship. How would you evaluate whether it returns the right evidence?",
        "RAG": "Design an end-to-end RAG request path. Where can it hallucinate, and how would you reduce that risk?",
        "Prompt": "How would you turn a prompt into a reliable interface rather than a one-off instruction?",
        "Function": "When an LLM calls a tool, how do you validate and safely execute the request?",
        "Memory": "How would you retain the right conversation context while controlling token growth and privacy risk?",
        "Agent": "When is an agentic workflow justified over a deterministic pipeline, and how do you make it observable?",
        "MCP": "Explain the roles of an MCP client, server, and tool. How would this make an integration safer to evolve?",
        "Deployment": "Take an AI API into production: outline the container, health, scaling, and rollback decisions you would make.",
        "Monitoring": "Which signals would you instrument to spot a degraded AI experience before users report it?",
        "Security": "What guardrails would you put around a production AI endpoint, especially for prompt injection and sensitive data?",
    }
    return f"Day {day} · {title}\n\n{prompts.get(topic, objective)}"


def start(candidate: dict[str, Any]) -> tuple[dict[str, Any], str]:
    days = curriculum_days()
    completed = [m for m in candidate.get("missions", []) if m.get("passed")]
    # High-attempt missions are valuable diagnostic signals; shuffle by risk then breadth.
    completed.sort(key=lambda m: (-(m.get("attempts", 1)), m["day"]))
    selected: list[dict[str, Any]] = []
    seen = set()
    for m in completed:
        category = topic_for(m["title"])
        if category not in seen or len(selected) < 4:
            selected.append(m); seen.add(category)
    selected = selected[:8] if len(selected) >= 8 else selected
    if len(selected) < 8:
        selected += [m for m in completed if m not in selected][:8-len(selected)]
    name = candidate.get("member", {}).get("name", "there")
    session = {"candidate": candidate, "days": days, "queue": selected, "index": 0, "answers": [], "asked": [], "followup_pending": False, "started_at": datetime.now(timezone.utc).isoformat()}
    return session, f"Welcome, {name}. I’ll tailor this interview to your cohort journey. Think aloud, explain trade-offs, and use examples from what you built.\n\n{make_question(session, selected[0])}"


def feedback(session: dict[str, Any]) -> dict[str, Any]:
    answers = session["answers"]
    strong = [a for a in answers if a["score"] >= 3]
    weak = [a for a in answers if a["score"] < 3]
    name = session["candidate"].get("member", {}).get("name", "The candidate")
    avg = round(sum(a["score"] for a in answers) / max(1, len(answers)), 1)
    strengths = [f"{a['topic']}: connected the explanation to {', '.join(a['signals'][:3]) or 'a concrete engineering rationale'}." for a in strong[:3]] or ["Stayed engaged across a multi-domain technical discussion."]
    gaps = [f"{a['topic']}: make the request flow, failure modes, and success metric more explicit." for a in weak[:3]] or ["Continue strengthening depth with production examples and measurable outcomes."]
    return {"summary": f"{name} completed {len(answers)} adaptive questions across {len(set(a['day'] for a in answers))} cohort days (evidence score: {avg}/5). The strongest next step is turning conceptual knowledge into concise production decision narratives.", "strengths": strengths, "gaps": gaps, "next": ["Practice a 90-second architecture walkthrough: input → retrieval/tools → model → guardrails → observability.", "For each project, prepare one metric, one trade-off, and one failure you mitigated.", "Rehearse follow-up answers using: decision, rationale, alternative, measurement."]}


def interview(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    sid = payload.get("sessionId")
    if not sid: return {"error": "sessionId is required"}, 400
    with LOCK:
        if payload.get("candidate"):
            session, reply = start(payload["candidate"]); SESSIONS[sid] = session
            return {"reply": reply, "done": False, "meta": {"questionsRequired": 8, "voiceReady": True}}, 200
        session = SESSIONS.get(sid)
        if not session: return {"error": "Unknown session. Start with candidate."}, 404
        message = str(payload.get("message", "")).strip()
        if not message: return {"error": "message is required"}, 400
        mission = session["queue"][session["index"]]
        topic = topic_for(mission["title"]); score, signals = quality(message, topic)
        session["answers"].append({"day": mission["day"], "topic": topic, "score": score, "signals": signals, "answer": message})
        session["asked"].append(mission["day"])
        # One targeted follow-up only, ensuring 8 scored questions across at least 4 days.
        if not session["followup_pending"] and len(session["answers"]) < 8 and (score <= 2 or score >= 4):
            session["followup_pending"] = True
            return {"reply": make_question(session, mission, True), "done": False, "meta": {"assessment": "probe" if score >= 4 else "clarify", "question": len(session["answers"]) + 1}}, 200
        session["followup_pending"] = False; session["index"] += 1
        if len(session["answers"]) >= 8 or session["index"] >= len(session["queue"]):
            return {"reply": "Interview completed. Your tailored feedback is ready.", "done": True, "feedback": feedback(session)}, 200
        nxt = session["queue"][session["index"]]
        return {"reply": make_question(session, nxt), "done": False, "meta": {"assessment": "advance", "question": len(session["answers"]) + 1, "coverageDays": len(set(session["asked"]))}}, 200


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(ROOT), **kwargs)
    def do_GET(self):
        if self.path == "/api/candidates":
            try:
                encoded = json.dumps(load_json("candidates.json")).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(encoded))); self.end_headers(); self.wfile.write(encoded)
            except OSError as e:
                self.send_error(500, f"Could not load candidate data: {e}")
            return
        return super().do_GET()
    def do_POST(self):
        if self.path != "/api/interview": self.send_error(404); return
        try:
            length = int(self.headers.get("Content-Length", 0)); payload = json.loads(self.rfile.read(length))
            body, status = interview(payload)
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            body, status = {"error": f"Invalid request: {e}"}, 400
        encoded = json.dumps(body).encode(); self.send_response(status)
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(encoded))); self.end_headers(); self.wfile.write(encoded)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000")); print(f"Interview Agent running at http://localhost:{port}")
    ThreadingHTTPServer(("", port), Handler).serve_forever()
