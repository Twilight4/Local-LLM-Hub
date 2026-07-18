#!/usr/bin/env bash
# ci/test_chat.sh — assert LiteLLM's /v1/chat/completions returns valid OpenAI JSON.
#
# Sends a prompt, then checks:
#   1. response parses as JSON and has choices[0].message.content
#   2. the content is the deterministic reply the mock returns ("ok")
#
# Expects: the stack is up (real or CI override), jq installed, master key
# in $LITELLM_MASTER_KEY (defaults to the CI override value).
set -euo pipefail

ENDPOINT="${ENDPOINT:-http://127.0.0.1:4000}"
MASTER_KEY="${LITELLM_MASTER_KEY:-sk-ci-test-key-not-real}"

resp=$(curl -sS --fail-with-body -X POST "$ENDPOINT/v1/chat/completions" \
  -H "Authorization: Bearer $MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.2","messages":[{"role":"user","content":"reply with one word: ok"}]}')

# 1. shape: must be OpenAI-style JSON with the content field
if ! echo "$resp" | jq -e '.choices[0].message.content | type == "string"' > /dev/null; then
  echo "FAIL: response is not valid OpenAI chat JSON (missing choices[0].message.content)"
  echo "$resp"
  exit 1
fi

# 2. content: mock returns "ok" when the user message contains "ok"
content=$(echo "$resp" | jq -r '.choices[0].message.content')
if [[ "$content" != "ok" ]]; then
  echo "FAIL: expected content 'ok', got '$content'"
  exit 1
fi

echo "PASS: chat completion returned valid JSON with content='ok'"
