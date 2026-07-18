#!/usr/bin/env bash
# ci/test_streaming.sh — assert /v1/chat/completions streams SSE chunks.
#
# Exercises the streaming code path through LiteLLM:
#   1. response is SSE format (data: {...}\n\n lines)
#   2. final line is 'data: [DONE]'
#   3. ≥2 chunks present (actual chunking, not single-shot)
#   4. reassembled delta.content equals the mock's deterministic reply ('ok')
set -euo pipefail

ENDPOINT="${ENDPOINT:-http://127.0.0.1:4000}"
MASTER_KEY="${LITELLM_MASTER_KEY:-sk-ci-test-key-not-real}"

raw=$(curl -sS -N -X POST "$ENDPOINT/v1/chat/completions" \
  -H "Authorization: Bearer $MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.2","stream":true,"messages":[{"role":"user","content":"reply with one word: ok"}]}')

# 1. SSE shape
if ! echo "$raw" | grep -q '^data: '; then
  echo "FAIL: response is not SSE format (no 'data: ' lines)"
  echo "$raw"
  exit 1
fi

# 2. [DONE] terminator
if ! echo "$raw" | grep -q '^data: \[DONE\]'; then
  echo "FAIL: stream missing '[DONE]' terminator"
  echo "$raw"
  exit 1
fi

# 3. ≥2 content chunks
chunk_count=$(echo "$raw" | grep '^data: ' | grep -v 'DONE' | wc -l)
if [[ "$chunk_count" -lt 2 ]]; then
  echo "FAIL: expected ≥2 stream chunks, got $chunk_count"
  exit 1
fi

# 4. reassembled content (strip the 'data: ' SSE prefix before jq)
content=$(echo "$raw" | sed -n 's/^data: //p' | grep -v '^\[DONE\]' \
  | jq -r '.choices[0].delta.content // empty' | tr -d '\n')
if [[ "$content" != "ok" ]]; then
  echo "FAIL: reassembled content '$content' != 'ok'"
  exit 1
fi

echo "PASS: streamed $chunk_count chunks, reassembled content='ok', [DONE] terminator present"
