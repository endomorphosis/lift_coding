# Agent Runner Quick Start Guide

This guide will help you set up and test the agent runner in **under 10 minutes**.

## What is the Agent Runner?

The agent runner is a GitHub Actions workflow that:
1. Monitors issues labeled `copilot-agent` in your repository
2. Extracts task metadata and instructions from the issue
3. Creates a pull request with the processed results
4. Posts status updates back to the issue

## Prerequisites

- A GitHub repository (this can be your dispatch repository)
- Admin access to the repository (to add secrets)
- 5 minutes of your time

## Setup Steps

### Step 1: Create a GitHub Token (2 minutes)

1. Go to **https://github.com/settings/tokens/new**

2. Fill in the form:
   - **Note**: `Agent Runner Token`
   - **Expiration**: Choose 90 days or longer
   - **Scopes**: Check the box for `repo` (Full control of private repositories)
     - This will automatically check all sub-scopes

3. Click **Generate token**

4. **IMPORTANT**: Copy the token immediately (starts with `ghp_`)
   - You won't be able to see it again!
   - Save it somewhere secure temporarily

### Step 2: Add the Token as a Secret (1 minute)

1. Go to your repository on GitHub

2. Click **Settings** → **Secrets and variables** → **Actions**

3. Click **New repository secret**

4. Fill in:
   - **Name**: `AGENT_RUNNER_TOKEN`
   - **Secret**: Paste the token you copied in Step 1

5. Click **Add secret**

✅ That's it! The agent runner is now enabled and will automatically process issues.

### Step 3: Test It! (5 minutes)

Now let's verify the agent runner works correctly.

#### Create a Test Issue

1. Go to your repository on GitHub

2. Click **Issues** → **New issue**

3. Fill in the issue:

   **Title**: `Test agent runner - Hello World`

   **Body**:
   ```markdown
   <!-- agent_task_metadata {"task_id": "test-12345678"} -->

   ## Instruction

   Create a simple test trace file to verify the agent runner is working correctly.

   Target Repository: YOUR_OWNER/YOUR_REPO
   ```
   
   **Important**: Replace `YOUR_OWNER/YOUR_REPO` with your repository name (e.g., `endomorphosis/lift_coding`)

4. Click **Labels** and add the `copilot-agent` label
   - If the label doesn't exist, create it first:
     - Go to **Issues** → **Labels** → **New label**
     - Name: `copilot-agent`
     - Color: Any color you like (e.g., purple `#9333ea`)
     - Click **Create label**

5. Click **Submit new issue**

#### Watch the Magic Happen

1. **Go to the Actions tab** in your repository

2. You should see a new workflow run called "Agent Runner" that just started

3. Click on it to see the live logs

4. **Expected behavior** (takes 30-60 seconds):
   - ✅ Issue detected
   - ✅ Metadata extracted
   - ✅ Task processed
   - ✅ PR created
   - ✅ Comments posted to the issue

#### Verify the Results

1. **Check the Issue**:
   - Go back to the test issue
   - You should see 2 comments from the agent runner:
     - 🤖 "Agent runner started processing..."
     - ✅ "Agent runner completed processing and created a pull request..."

2. **Check the Pull Request**:
   - Go to **Pull requests** tab
   - You should see a new PR titled "Agent task: Test agent runner - Hello World"
   - Open it and verify:
     - ✅ PR body contains `<!-- agent_task_metadata {"task_id": "test-12345678"} -->`
     - ✅ PR body contains `Fixes #X` (where X is your issue number)
     - ✅ Files changed includes `agent-tasks/test-123.md`
     - ✅ The trace file contains your task metadata

3. **Clean Up** (optional):
   - Close or merge the test PR
   - Close the test issue
   - Delete the test branch if desired

🎉 **Congratulations!** Your agent runner is now operational!

## What Happens Next?

Now that the agent runner is set up:

1. **Any issue labeled `copilot-agent`** will be automatically processed
2. The runner will create a **trace file** with task metadata
3. A **pull request** will be opened with correlation metadata
4. The **HandsFree backend** (if configured) will mark the task as completed

## Customization

The current implementation creates a **placeholder trace file**. To make it do actual work:

1. Edit `.github/workflows/agent-runner.yml`
2. Find the "Process task" step
3. Replace the placeholder logic with:
   - LLM integration (OpenAI, Anthropic, etc.)
   - Code generation tools
   - Custom scripts
   - Whatever you need!

Example:
```yaml
- name: Process task
  working-directory: target-repo
  run: |
    # Install your tools
    pip install openai
    
    # Run your code
    python ../agent-runner/my_custom_agent.py \
      --instruction "$INSTRUCTION" \
      --task-id "$TASK_ID"
```

## Troubleshooting

### Workflow doesn't run

**Problem**: No workflow run appears in the Actions tab

**Solutions**:
- ✅ Verify the `copilot-agent` label is on the issue
- ✅ Check that the workflow file exists: `.github/workflows/agent-runner.yml`
- ✅ Ensure Actions are enabled: Settings → Actions → General → Allow all actions
- ✅ Verify the workflow is on the default branch (main/master)

### "AGENT_RUNNER_TOKEN secret is not configured" warning

**Problem**: Workflow runs but skips processing with a warning

**Solution**:
- ✅ Add the secret as described in Step 2
- ✅ Verify the secret name is exactly `AGENT_RUNNER_TOKEN` (case-sensitive)
- ✅ Make sure you added it to the correct repository

### "Missing task_id in agent_task_metadata" error

**Problem**: Workflow fails with this error message

**Solution**:
- ✅ Verify the issue body includes the metadata comment:
  ```markdown
  <!-- agent_task_metadata {"task_id": "your-task-id"} -->
  ```
- ✅ Ensure the JSON is valid (use quotes around keys and values)
- ✅ The task_id should be a unique identifier (8+ characters)

### PR creation fails

**Problem**: Workflow succeeds but no PR is created

**Solutions**:
- ✅ Verify the token has `repo` scope
- ✅ Check that the target repository exists and is accessible
- ✅ Ensure you're not on a protected branch that blocks pushes
- ✅ Look at the workflow logs for specific error messages

### Can't find workflow logs

**Problem**: Don't see the workflow run in Actions tab

**Solution**:
- ✅ Go to **Actions** tab at the top of your repository
- ✅ Look for "Agent Runner" in the workflow list
- ✅ Click on it to see all runs
- ✅ Click on a specific run to see detailed logs

## Security Notes

🔒 **Keep your token safe**:
- Never commit tokens to version control
- Don't share tokens in issues or pull requests
- Rotate tokens every 90 days
- Use a bot account for production (not your personal account)

🔒 **Review generated PRs**:
- Always review PRs before merging
- Use branch protection rules to require reviews
- Don't auto-merge PRs from the agent runner

## Advanced Usage

### Manual Triggering

You can also trigger the workflow manually:

1. Go to **Actions** → **Agent Runner**
2. Click **Run workflow**
3. Enter an issue number
4. Click **Run workflow**

This is useful for:
- Re-processing an issue
- Testing changes to the workflow
- Debugging issues

### Docker Runner Alternative

If you prefer running the agent as a Docker container instead of GitHub Actions:

1. See the complete guide: [docs/agent-runner-setup.md](./agent-runner-setup.md)
2. Use the Docker Compose configuration: `docker-compose.agent-runner.yml`
3. Follow the setup instructions for the containerized runner

The Docker runner is better for:
- On-premise deployments
- Custom LLM integrations
- Advanced error handling
- High-volume processing

## Need Help?

- 📖 **Full documentation**: [docs/agent-runner-setup.md](./agent-runner-setup.md)
- 🐛 **Report issues**: Create an issue in this repository
- 💬 **Questions**: Ask in discussions or issues

## Next Steps

1. ✅ Test the basic flow (you just did this!)
2. 🔧 Customize the task processing logic
3. 🧪 Test with real tasks from your workflow
4. 📊 Monitor and optimize performance
5. 🚀 Scale up as needed

Enjoy your automated agent runner! 🎉
