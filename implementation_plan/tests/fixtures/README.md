# Fixtures

This folder is intentionally empty in the starter pack—add fixtures as you build.

Recommended layout:

tests/fixtures/
  transcripts/
    clean/
      inbox.txt
      summarize_pr_412.txt
    noisy/
      inbox_gym_noise_variant_1.txt
  github/
    webhooks/
      pull_request.opened.json
      check_suite.completed.json
    api/
      list_pull_requests.json
      get_pull_request.json

Golden outputs:
- Store expected `spoken_text` in `.golden.json` files so summarization changes are intentional.
