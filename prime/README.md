# PRIME v0.3 — Governed Evolution + Product Runtime

**PRIME — Progressive Recursive Intelligence & Mutation Engine** is a model-agnostic control plane that improves bounded AI policy through governed experiments and powers four tenant-scoped products:

- **Guardian X** — reliability, security, data, AI, and cost intelligence
- **Genome** — longitudinal finance and healthcare risk-support signatures
- **Company Brain** — organizational memory and conflict detection
- **Digital Twin** — assumption-explicit counterfactual scenarios

v0.3 combines cumulative daily evolution with tenant isolation, memory, model routing, bounded tools, runtime events, feedback, CLI commands, REST APIs, and a control dashboard. It is an executable platform foundation, not yet a frontier foundation model.

## Run locally

```bash
cd prime
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
python -m unittest discover -s tests -v
prime evolve
prime status
prime products
```

Run a product:

```bash
prime run-product guardian-x \
  --tenant acme --actor operator --roles reader \
  --text "Kafka consumer lag caused pipeline latency to breach the SLA." --json
```

Add Company Brain memory:

```bash
prime memory-add --tenant acme --actor editor --roles writer \
  --namespace architecture --content "The deployment runbook lists port 8080."
```

Optional integrations:

```bash
pip install -e '.[openai]'
export OPENAI_API_KEY='...'
prime evolve --provider openai --model gpt-5

pip install -e '.[api]'
prime serve --host 127.0.0.1 --port 8080
```

The product API expects `X-Prime-Tenant`, `X-Prime-Actor`, and `X-Prime-Roles` from a trusted identity-aware gateway. PRIME v0.3 does not authenticate those headers itself. API-triggered evolution remains disabled unless `PRIME_API_EVOLUTION_ENABLED=true` is set explicitly.

## Safety boundaries

- Customer content, runtime databases, private holdouts, and raw outputs are not committed to Git.
- Genome does not diagnose patients or confirm fraud.
- Guardian X does not execute automatic remediation.
- Company Brain does not silently resolve policy conflicts.
- Digital Twin does not claim guaranteed outcomes.
- Arbitrary source-code self-modification remains prohibited; code changes use reviewed pull requests.

See `docs/ARCHITECTURE.md`, `docs/EVOLUTION_POLICY.md`, and `docs/PRODUCT_RUNTIME.md`.
