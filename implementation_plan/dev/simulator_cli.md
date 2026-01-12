# Simulator CLI (text-first)

Use these commands to test the backend without the wearable or mobile app.

## Inbox
curl -s http://localhost:8080/v1/command \
  -H 'Content-Type: application/json' \
  -d '{
    "input": {"type":"text","text":"inbox"},
    "profile":"workout",
    "client_context":{"device":"simulator","locale":"en-US","timezone":"America/Los_Angeles","app_version":"0.1.0","noise_mode":true},
    "idempotency_key":"dev-1"
  }' | jq

## Summarize PR
curl -s http://localhost:8080/v1/command \
  -H 'Content-Type: application/json' \
  -d '{
    "input": {"type":"text","text":"summarize pr 412"},
    "profile":"default",
    "client_context":{"device":"simulator","locale":"en-US","timezone":"America/Los_Angeles","app_version":"0.1.0"},
    "idempotency_key":"dev-2"
  }' | jq

## Confirm pending action
curl -s http://localhost:8080/v1/commands/confirm \
  -H 'Content-Type: application/json' \
  -d '{"token":"<PENDING_ACTION_TOKEN>","idempotency_key":"dev-confirm-1"}' | jq
