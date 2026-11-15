---
license: apache-2.0
library_name: vllm
base_model:
- mistralai/Leanstral-2603
---

# Leanstral 1.5 119B A6B

![leanstral_benchmark_comparison](https://cdn-uploads.huggingface.co/production/uploads/66775fab8c58c5a12ae629ac/u5R3aWfUizTaxGemat-lU.png)

Leanstral 1.5 is an open-source code agent model designed for [Lean 4](https://github.com/leanprover/lean4), a proof assistant capable of expressing complex mathematical objects such as [perfectoid spaces](https://xenaproject.wordpress.com/2020/12/05/liquid-tensor-experiment/) and software specifications like [properties of Rust fragments](https://github.com/AeneasVerif/aeneas).

Built as part of the [Mistral Small 4 family](https://huggingface.co/collections/mistralai/mistral-small-4), it combines multimodal capabilities and an efficient architecture, making it both performant and cost-effective compared to existing closed-source alternatives.

> [!Note]
> This is an updated model of our previously released [Leanstral model](https://huggingface.co/mistralai/Leanstral-2603).

## Key Features

Leanstral incorporates the following architectural choices:

- **MoE**: 128 experts, 4 active per token
- **Model Size**: 119B parameters with 6.5B activated per token
- **Context Length**: 256k tokens
- **Multimodal Input**: Accepts text and image input, producing text output

## Recommended Settings

- **Temperature**: 1.0
- **Reasoning Effort**:
  - `'none'` → Do not use reasoning
  - `'high'` → Use reasoning (recommended for complex prompts).
- **Context Length**: ≤ 200k tokens recommended

## Usage

**Installing Mistral Vibe and Leanstral**

- If you have already installed Leanstral it should automatically use the new model. ****
- Verify your Mistral account settings at https://chat.mistral.ai/
    - Sign up or Sign in
    - You can stay on the **free** plan (there is no need to sign up to Mistral Pro to use Leanstral).
    - Opt into “Enable Labs models” in https://admin.mistral.ai/plateforme/privacy
    - Make an API key in https://admin.mistral.ai/organization/api-keys
- Follow the instructions to install the mistral vibe CLI at https://docs.mistral.ai/getting-started/quickstarts/vibe-code/install-cli
- Setup should happen automatically, requesting your API key. But if not, use `vibe --setup` from the terminal.
- To setup Leanstral in Mistral `vibe` enter:
    - `/leanstall` (lean + [in]stall)
    - `exit` (to leave `vibe`)

**Using Leanstral**

- Type `vibe --agent lean` in the terminal (**ensure Leanstral displays at the top**).
    - We recommend running `vibe` inside vs code terminal so you can see both vibe and your code.
    - We recommend running `vibe` inside your Lean project directory.
    - To auto-approve model changes (be careful!), use `vibe --agent lean --yolo`.
- Ask Leanstral to do any coding task for you, such as prove a given theorem or fix some code in your project.
- Leanstral is capable of doing very long range tasks which requires hours of work.  Don’t hesitate to let it work away at a problem.

**Using Leanstral with the lean-lsp-mcp**

We recommend trying Leanstral with the lean-lsp-mcp, a standard tool for AI agents to interact with Lean. The lean-lsp-mcp README has instructions for setting up the MCP with Mistral Vibe.

### Local server

If instead of pinging the Mistral API, you want to use your local vLLM server, you can do the following:
- 1. Spin up a vllm server as explained in [`Usage - vllm`](#vllm)
- 2. Create a new agent file called `lean.toml` in `~/.vibe/agents`:

```sh
mkdir ~/.vibe/agents/ && touch ~/.vibe/agents/lean.toml
```

And then copy-paste the following config into `~/.vibe/agents/lean.toml`

```toml
display_name = "Lean (local vLLM)"
description = "Lean 4 mode using local vLLM"
safety = "neutral"

system_prompt_id = "lean"
active_model = "leanstral"

[[providers]]
name = "vllm"
api_base = "http://<your-host-url>:8000/v1"
api_key_env_var = ""
backend = "generic"
reasoning_field_name = "reasoning_content"

[[models]]
name = "mistralai/Leanstral-1.5-119B-A6B"
provider = "vllm"
alias = "leanstral"
thinking = "high"
temperature = 1.0
auto_compact_threshold = 168000

[tools.bash]
default_timeout = 1200
```

**Note**: Make sure to overwrite `<your-host-url>` with your server's url.

Then restart `vibe` and "tab-shift" to "lean" mode.

Give it a try on some "lean" code such as, *e.g.*: [PrimeNumberTheoremAnd](https://github.com/AlexKontorovich/PrimeNumberTheoremAnd)

### Local Deployment

The model can also be deployed with vLLM, we advise everyone to use the Mistral AI API if the model is subpar with local serving:
- [`vllm (recommended)`](https://github.com/vllm-project/vllm): See [here](#vllm).

#### vLLM

Let's use this model with the [vLLM library](https://github.com/vllm-project/vllm) to implement production-ready inference pipelines.

1. **Installation**

Make sure to install **vllm >= 0.24.0**:

```
uv pip install -U vllm --torch-backend=auto
```

Doing so should automatically install [`mistral_common >= 1.11.5`](https://github.com/mistralai/mistral-common/releases/tag/v1.11.5).

To check:
```
python -c "import mistral_common; print(mistral_common.__version__)"
```

You can also make use of a ready-to-go [docker image](https://github.com/vllm-project/vllm/blob/main/docker/Dockerfile) or on the [docker hub](https://hub.docker.com/layers/vllm/vllm-openai/latest).

2. **Launch server**

We recommend that you use Leanstral in a server/client setting. 

```
vllm serve mistralai/Leanstral-1.5-119B-A6B \
  --max-model-len 200000 \
  --tensor-parallel-size 4 \
  --attention-backend FLASH_ATTN_MLA \
  --tool-call-parser mistral \
  --enable-auto-tool-choice \
  --reasoning-parser mistral
```


3. **Client**

```py
from openai import OpenAI
from huggingface_hub import hf_hub_download

# Modify OpenAI's API key and API base to use vLLM's API server.
openai_api_key = "EMPTY"
openai_api_base = "<your-host-url>"

client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)

TEMP = 1.0
MAX_TOK = 32000
REASONING = "high" # switch to 'none' for faster answers

models = client.models.list()
model = models.data[0].id


prompt = """Define the transition rules as an inductive proposition.

This choice provides better support for proving properties about valid transitions and is generally more natural for modeling state machines in Lean, where you want to express logical rules rather than just computing a yes/no vale for each possible transition."""
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": prompt,
            },
        ],
    },
]



response = client.chat.completions.create(
    model=model,
    messages=messages,
    temperature=TEMP,
    max_tokens=MAX_TOK,
    reasoning_effort=REASONING,
)

print("Content")
print(response.choices[0].message.content)

print("Reasoning")
print(response.choices[0].message.reasoning)
```

_Example Content_:
<details>
<summary>Expand</summary
To define transaction rules as an inductive proposition in Lean, you can create an inductive type that captures the valid transitions between states. This approach is particularly useful for modeling state machines and proving properties about transitions, such as invariants.

Here is an example of how to define an inductive proposition for valid transitions in a simple counter machine:

```lean
-- Example: Counter that can only increment by 1 (no decrement, no shortcuts)
inductive ValidTransition : Nat → Nat → Prop
  | step1 : ∀ s, ValidTransition s (s + 1)   -- Core transition: s → s+1
  | step2 : ∀ s, ValidTransition s (2 * s)    -- Bonus: s → 2s (optional)
  | zero_step : ValidTransition 0 0          -- Additional special case

lemma reach_any_positive : ∀ n > 0, ValidTransition 0 n := by
  induction n with
  | zero => contradiction
  | succ n ih =>
    cases' Nat.eq_zero_or_pos n with h h
    · simp [h]
    · have : ValidTransition 0 (n + 1) := by
        cases' h with _ ih    -- Wait, this is messy...
```

In this example, `ValidTransition` is defined as an inductive proposition with constructors `step1`, `step2`, and `zero_step`. The `step1` constructor allows for any state to transition to the next state by incrementing by 1, while `step2` allows for doubling the state. The `zero_step` constructor is a special case for the initial state 0.

The lemma `reach_any_positive` aims to prove that any positive natural number is reachable from the initial state 0 through valid transitions. The proof uses induction on `n`, but due to simplification issues, the current approach may not be the most effective.

A more concise and effective way to define and prove properties about transitions is to use a simpler model, such as the following:

```lean
-- Simpler model for counter transitions (suffices for proofs)
inductive CounterTrans : Nat → Nat → Prop
  | valid : ∀ n, CounterTrans n (n + 1)

lemma reach_positive : ∀ n > 0, CounterTrans 0 n
  -- Proof is now trivial (by induction)
```

In this simpler model, `CounterTrans` is defined with a single constructor `valid`, which allows for any state to transition to the next state by incrementing by 1. The lemma `reach_positive` is straightforward to prove by induction, leveraging the simplicity of the transition rules.

This approach ensures that the proof remains concise and effective, avoiding unnecessary complexity in the transition rules. By using inductive propositions, we can effectively reason about state transitions and prove properties about the system.
</details>

**_Tool-Calling_**

You can add `tools` to the chat completion as follows:

```py
prompt = """I have the following Lean 4 code snippet and want to check if it compiles and runs without errors. Can you run it for me and let me know the result?

```lean\ninductive State where\n  | idle\n  | busy\n  | error\n\ndef transition : State → State → Bool\n  | .idle, .busy => true\n  | .busy, .idle => true\n  | .busy, .error => true\n  | _, _ => false\n\n#eval transition .idle .busy\n```"""

tools = [{
    "type": "function",
    "function": {
        "name": "lean_run_code",
        "description": "Run or compile an independent Lean code snippet or file and return the result or error message.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Lean code snippet to run or compile. Either this or file_path must be provided."
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to the Lean file to run or compile. Either this or code must be provided."
                }
            },
        }
        }
}]

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": prompt,
            },
        ],
    },
]

response = client.chat.completions.create(
    model=model,
    messages=messages,
    temperature=TEMP,
    max_tokens=MAX_TOK,
    reasoning_effort=REASONING,
    tools=tools,
)

print("Tool Calls")
print(response.choices[0].message.tool_calls)

print("Reasoning")
print(response.choices[0].message.reasoning)
```

_Example Tool Calls_:
<details>
<summary>Expand</summary

`Function(arguments='{"code": "inductive State where\\n  | idle\\n  | busy\\n  | error\\n\\ndef transition : State → State → Bool\\n  | .idle, .busy => true\\n  | .busy, .idle => true\\n  | .busy, .error => true\\n  | _, _ => false\\n\\n#eval transition .idle .busy"}', name='lean_run_code')`

</details>

## License

This model is licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0.txt).

*You must not use this model in a manner that infringes, misappropriates, or otherwise violates any third party’s rights, including intellectual property rights.*