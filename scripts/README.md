# Creating Draft PRs for Remaining Implementation Gaps

This directory contains automation scripts to create draft PRs for the 3 remaining backend implementation gaps identified in the gap analysis.

## PRs to Create

1. **PR-026: Automatic push notification delivery**
   - Branch: `draft/pr-026-notification-push-delivery`
   - Tracking: `tracking/PR-026-notification-push-delivery.md`

2. **PR-027: Profile-based summary verbosity tuning**
   - Branch: `draft/pr-027-profile-verbosity-tuning`
   - Tracking: `tracking/PR-027-profile-verbosity-tuning.md`

3. **PR-028: External agent runner setup guide**
   - Branch: `draft/pr-028-external-agent-runner-setup`
   - Tracking: `tracking/PR-028-external-agent-runner-setup.md`

## Prerequisites

- Git repository cloned locally
- `gh` CLI installed and authenticated
  - Install: https://cli.github.com/manual/installation
  - Login: `gh auth login`

## Quick Start

### Option 1: Bash Script (Recommended)

```bash
cd /path/to/lift_coding
./scripts/create-draft-prs.sh
```

### Option 2: Python Script

```bash
cd /path/to/lift_coding
python3 scripts/create_draft_prs.py
```

### Option 3: Manual Creation

If you prefer to create PRs manually:

```bash
# For each PR (026, 027, 028):
PR_NUM="026-notification-push-delivery"
TITLE="PR-026: Automatic push notification delivery"
TRACKING="tracking/PR-026-notification-push-delivery.md"

# Create branch
git checkout -b "draft/pr-${PR_NUM}" main

# Create initial plan
mkdir -p work
cat > "work/pr-${PR_NUM}-plan.md" <<EOF
# ${TITLE}

Ready for GitHub Copilot agent implementation.
See ${TRACKING} for full details.
EOF

# Commit and push
git add "work/pr-${PR_NUM}-plan.md"
git commit -m "PR-${PR_NUM}: Initial plan"
git push -u origin "draft/pr-${PR_NUM}"

# Create draft PR
gh pr create \
  --repo endomorphosis/lift_coding \
  --base main \
  --head "draft/pr-${PR_NUM}" \
  --title "${TITLE}" \
  --body-file "${TRACKING}" \
  --draft \
  --label copilot-agent

# Return to main
git checkout main
```

Repeat for PR-027 and PR-028.

## What the Scripts Do

1. **Check prerequisites**: Verify gh CLI is installed and authenticated
2. **Create branches**: One branch per PR from main
3. **Add initial plan**: Create a work/pr-XXX-plan.md file referencing the tracking doc
4. **Commit and push**: Push each branch to origin
5. **Create draft PRs**: Create draft PRs with:
   - Title from PR number
   - Body from tracking document
   - Label: `copilot-agent`
   - Base: `main`
   - Status: Draft

## After PRs are Created

1. Review the created PRs on GitHub
2. Assign them to GitHub Copilot agents (use `@copilot` mentions)
3. Copilot agents will implement according to the tracking documents

## Troubleshooting

### "gh: command not found"
Install GitHub CLI: https://cli.github.com/manual/installation

### "Not authenticated with GitHub"
Run: `gh auth login` and follow the prompts

### "remote: Permission denied"
Make sure you have write access to the repository, or fork it first

### Branch already exists
Delete the branch first:
```bash
git branch -D draft/pr-026-notification-push-delivery
git push origin --delete draft/pr-026-notification-push-delivery
```

## Files Created

Each PR will have:
- Branch: `draft/pr-XXX-...`
- Plan file: `work/pr-XXX-...-plan.md`
- Tracking doc: `tracking/PR-XXX-....md` (already exists)

## Expected Output

```
Creating draft PRs for remaining implementation gaps...
Repository: endomorphosis/lift_coding
Base branch: main

✓ gh CLI is installed
✓ gh CLI is authenticated

Creating PR-026: Automatic push notification delivery
  Branch: draft/pr-026-notification-push-delivery
  Tracking: tracking/PR-026-notification-push-delivery.md
  Pushing branch...
  Creating draft PR...
  ✓ Created: https://github.com/endomorphosis/lift_coding/pull/139

Creating PR-027: Profile-based summary verbosity tuning
  Branch: draft/pr-027-profile-verbosity-tuning
  Tracking: tracking/PR-027-profile-verbosity-tuning.md
  Pushing branch...
  Creating draft PR...
  ✓ Created: https://github.com/endomorphosis/lift_coding/pull/140

Creating PR-028: External agent runner setup guide
  Branch: draft/pr-028-external-agent-runner-setup
  Tracking: tracking/PR-028-external-agent-runner-setup.md
  Pushing branch...
  Creating draft PR...
  ✓ Created: https://github.com/endomorphosis/lift_coding/pull/141

✓ All draft PRs created successfully!

Next steps:
  1. Review the created PRs on GitHub
  2. Assign them to GitHub Copilot agents
  3. Copilot agents will implement according to tracking docs
```

## Alternative: GitHub UI

If you can't use the scripts, you can create PRs via the GitHub web interface:

1. Go to https://github.com/endomorphosis/lift_coding
2. Click "New pull request"
3. Click "compare across forks" or create branch first
4. Set base: `main`, compare: `draft/pr-XXX-...` (create branch first)
5. Add title and body from tracking document
6. Mark as draft
7. Add label `copilot-agent`
8. Create pull request

## Support

For issues with these scripts, see:
- `work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md` - Original detailed instructions
- `tracking/IMPLEMENTATION_PLAN_GAP_CHECKLIST.md` - Gap analysis
