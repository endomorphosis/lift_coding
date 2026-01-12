# MVP Checklists

## MVP1: Read-only PR inbox
- [ ] Wearable audio capture -> mobile
- [ ] STT (backend or on-device) -> text
- [ ] Intent: inbox.list
- [ ] GitHub auth (GitHub App or OAuth)
- [ ] Fetch PR list + checks
- [ ] TTS response playback
- [ ] Basic action log

## MVP2: PR summary
- [ ] Intent: pr.summarize
- [ ] Summarize description + diff stats + checks + last review
- [ ] “Repeat” + “next” navigation
- [ ] Profile: Workout (shorter summaries)

## MVP3: One safe write action
- [ ] Intent: pr.request_review OR checks.rerun
- [ ] Confirmation required
- [ ] Policy gate (repo allowlist)
- [ ] Audit entry + spoken confirmation

## MVP4: Agent delegation
- [ ] Intent: agent.delegate
- [ ] Task lifecycle tracking
- [ ] Notify on PR creation / completion
