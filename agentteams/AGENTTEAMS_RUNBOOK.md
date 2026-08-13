# CogniGuide AgentTeams Runbook

This runbook validates a **real AgentTeams Team**, not a local hand-written
workflow. Keep credentials in the AgentTeams installer or a local secret store;
never put an API key in this repository, screenshots, prompts, or run artifacts.

## 0. Preconditions

- Docker Desktop (or a compatible Docker daemon) is running.
- Python 3 is available for the local tool gateway.
- AgentTeams and Element/Matrix are installed according to the competition's
  official installation instructions.
- A DeepSeek OpenAI-compatible provider is configured in AgentTeams. For this
  competition demo use the documented Chat Completions profile:

```text
Provider: DeepSeek / OpenAI-compatible API
Base URL: https://api.deepseek.com
Wire API: chat-completions
Model: deepseek-v4-flash
API key: read only from local protected configuration
```

Do not proceed as if AgentTeams is running until this succeeds:

```powershell
docker run --rm hello-world
```

## 1. Start and verify the gateway

Open a dedicated PowerShell window:

```powershell
Set-Location .\agentteams
.\run_gateway.bat
```

In another window, verify the two read-only endpoints:

```powershell
Invoke-RestMethod http://127.0.0.1:18089/health
Invoke-RestMethod http://127.0.0.1:18089/scenarios
Invoke-RestMethod -Method Post -ContentType 'application/json' `
  -Uri http://127.0.0.1:18089/tools/python_foundations_overconfidence/learning_data.get_task_metadata `
  -Body '{"schema_version":"cogniguide.tool-request/v1","task_id":"CG-1001","trace_id":"gateway-smoke-001","actor":"interaction-evidence-analyst"}'
```

Expected health response:

```json
{"ok": true, "service": "cogniguide-agentteams-tool-gateway"}
```

Run gateway contract tests before provisioning the Team:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m unittest discover -s agentteams/tests -v
```

## 2. Give Worker containers a reachable gateway address

`127.0.0.1:18089` inside a Worker container is the Worker itself, not the Windows
host. Set `MOCK_TOOL_BASE_URL` to an address reachable from the AgentTeams
containers. Start with `http://host.docker.internal:18089` on Docker Desktop, or
discover and verify a bridge/host address:

```powershell
docker ps --format '{{.Names}}'
docker exec -it <manager-container> curl http://host.docker.internal:18089/health
```

If that fails, use a reachable host/bridge address and repeat the `curl` test
from a Manager or Worker container. Do not paste an untested address into the
Manager message.

## 3. Configure the model in AgentTeams

Copy [`agentteams.env.example`](agentteams.env.example) to a local ignored file
only as a non-secret checklist. Configure the API key via the AgentTeams UI,
installer, or secret store, then perform the provider's built-in model test with
`deepseek-v4-flash`. Use `deepseek-v4-pro` only when its stronger reasoning is
needed and the latency/cost tradeoff is acceptable. A successful direct API probe
is not a substitute for a Worker
health check.

For a repeatable preflight that never stores or prints the key, export the key
only in the current PowerShell session and run the committed DeepSeek Chat
Completions contract probe:

```powershell
$env:DEEPSEEK_BASE_URL = "https://api.deepseek.com"
$env:DEEPSEEK_MODEL = "deepseek-v4-flash"
$env:DEEPSEEK_API_KEY = "<local secret only>"
python tools\llm_contract_smoke.py
```

Expected output is a small JSON object with `"ok": true`, the requested model,
`"wire_api": "chat-completions"`, and `"status": "completed"`. The adapter
also retains an optional OpenAI Responses compatibility branch, but it is not the
DeepSeek default. Clear the session variable or close the PowerShell window
afterward.

Run the stronger live Worker preflight as well. It makes two actual
`deepseek-v4-flash` Chat Completions calls with the Evidence Analyst contract,
validates the authorized aggregation and the fail-closed consent branch, and
never fabricates the model response:

```powershell
python tools\live_worker_contract.py
```

This verifies an individual Worker contract against the real provider. It still
is not evidence of a live AgentTeams Team Room; that requires the Docker and
AgentTeams steps below.

## 4. Provision the native Team

1. Open the AgentTeams `manager` room.
2. Open [`create_agents_messages.md`](create_agents_messages.md).
3. Replace every `<MOCK_TOOL_BASE_URL>` with the container-tested URL.
4. Send the complete message once. The Manager must create and health-check the
   four business Workers serially, then create `cogniguide-demo` and a new,
   independent `cogniguide-demo-leader`.
5. Record the Worker names, Team Room name, and successful health checks.

## 5. Run both acceptance scenarios

Open the resulting Team Room and send the two messages in
[`run_demo_task_message.md`](run_demo_task_message.md), mentioning the actual
TeamLeader name.

| Scenario | Required observation |
| --- | --- |
| `python_foundations_overconfidence` | all four Workers participate; evidence includes `evt-functions-*`; prerequisite validation passes; terminal status is cautious (`HUMAN_REVIEW_REQUIRED` or equivalent) |
| `consent_required` | metadata is read, terminal status is `BLOCKED`, and gateway trace contains no `learning_data.get_assessment_events` call |

Retrieve gateway evidence after each task:

```powershell
Invoke-RestMethod http://127.0.0.1:18089/tools/python_foundations_overconfidence/trace
Invoke-RestMethod http://127.0.0.1:18089/tools/consent_required/trace
Invoke-RestMethod http://127.0.0.1:18089/tools/python_foundations_overconfidence/audit
```

## 6. Preserve review evidence

For the competition demo, retain:

1. Docker and Worker health-check results;
2. the Manager provisioning transcript;
3. Team Room collaboration showing the independent TeamLeader and four roles;
4. gateway traces and audit summaries; and
5. the four versioned JSON artifacts plus final report.

Never retain raw learner text, unredacted personal data, API keys, or model
reasoning traces in the evidence bundle.

## Troubleshooting

- **Docker pipe/daemon unavailable:** start Docker Desktop first. Do not claim a
  live AgentTeams run while the daemon is unavailable.
- **Worker cannot reach the gateway:** use `docker exec ... curl` to prove the
  URL from the container, then update the Manager message.
- **Provider test fails:** check base URL, wire API, local secret configuration,
  and the model name in AgentTeams; do not add credentials to `.env.example`.
- **Consent scenario reads events:** stop the demo. The evidence analyst contract
  or tool configuration is wrong; reset the gateway with
  `POST /tools/consent_required/reset` and reprovision/fix before retesting.
