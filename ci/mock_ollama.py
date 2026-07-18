#!/usr/bin/env python3
"""Mock Ollama for CI config tests.

Speaks just enough of Ollama's native API (/api/chat, /api/tags, /api/show)
for LiteLLM's `ollama/*` provider to route a chat completion through it.
Returns canned deterministic output — no model, no GPU.

Run locally:   python3 ci/mock_ollama.py
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

KNOWN_MODELS = ("llama3.2", "nomic-embed-text")


class MockOllama(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode())
        except (ValueError, UnicodeDecodeError):
            return {}

    def do_GET(self):  # noqa: N802 — http.server convention
        if self.path.startswith("/api/tags"):
            self._send(200, {"models": [{"name": m, "digest": "sha256:mock"} for m in KNOWN_MODELS]})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802 — http.server convention
        body = self._read_body()
        model = body.get("model", "llama3.2")
        if self.path.startswith("/api/show"):
            self._send(200, {"modelfile": f"FROM {model}", "details": {"family": "mock"}})
            return
        if self.path.startswith("/api/embeddings"):
            # ponytail: fixed 8-dim vector — enough for LiteLLM to pass it through
            self._send(200, {"embedding": [0.0] * 8})
            return
        if self.path.startswith("/api/generate"):
            # LiteLLM 1.92 routes chat through this legacy single-turn endpoint;
            # request: {"prompt": "..."}; response: {"response": "text"}
            prompt = body.get("prompt", "")
            reply = "ok" if "ok" in prompt.lower() else f"echo:{prompt[:32]}"
            self._send(200, {
                "model": model,
                "created_at": "2026-01-01T00:00:00Z",
                "response": reply,
                "done": True,
                "done_reason": "stop",
            })
            return
        if self.path.startswith("/api/chat"):
            user_msg = ""
            for m in body.get("messages", []):
                if m.get("role") == "user":
                    user_msg += m.get("content", "")
            reply = "ok" if "ok" in user_msg.lower() else f"echo:{user_msg[:32]}"
            self._send(200, {
                "model": model,
                "created_at": "2026-01-01T00:00:00Z",
                "message": {"role": "assistant", "content": reply},
                "done": True,
                "done_reason": "stop",
            })
            return
        self._send(404, {"error": "not found"})

    def log_message(self, *args):  # quiet in CI logs
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 11434), MockOllama).serve_forever()
