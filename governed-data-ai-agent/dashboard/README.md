# Interview Dashboard

A live browser UI for the existing **Governed Data & AI Operations Agent**. The dashboard calls the same Python governance workflow used by the CLI; the browser does not make the ALLOW/BLOCK decision.

## Run

```bash
pip install -r requirements-dashboard.txt
uvicorn dashboard.server:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

## Suggested interview demo

1. Click **Load sample** and run with **Approved governed source** + **Lineage registered** enabled.
2. Show the `ALLOW` decision, policy controls, metadata classifications, quality findings, anomaly findings, and SHA-256 input/output traceability.
3. Turn **Approved governed source** off and run again.
4. Show that the same asset becomes `BLOCK`, proving governance is an enforceable policy gate rather than an advisory chatbot response.

The dashboard deliberately uses the existing deterministic policy engine for the final decision and the existing Microsoft Purview publication boundary for auditable governance output.
