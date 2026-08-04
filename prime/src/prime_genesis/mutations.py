from __future__ import annotations

import hashlib
from dataclasses import replace

from prime_genesis.models import AgentVersion


def _version_id(parent: str, mutation_type: str, payload: str) -> str:
    digest = hashlib.sha256(f"{parent}|{mutation_type}|{payload}".encode()).hexdigest()[:12]
    return f"prime-g{digest}"


def _candidate(
    champion: AgentVersion,
    *,
    mutation_type: str,
    reason: str,
    prompt: str | None = None,
    workflow_steps: tuple[str, ...] | None = None,
    model_route: str | None = None,
    retrieval_policy: str | None = None,
    response_contract: str | None = None,
) -> AgentVersion:
    payload = "|".join(
        [
            prompt or champion.prompt,
            ",".join(workflow_steps or champion.workflow_steps),
            model_route or champion.model_route,
            retrieval_policy or champion.retrieval_policy,
            response_contract or champion.response_contract,
        ]
    )
    return replace(
        champion,
        version_id=_version_id(champion.version_id, mutation_type, payload),
        parent_version_id=champion.version_id,
        mutation_type=mutation_type,
        mutation_reason=reason,
        generation=champion.generation + 1,
        prompt=prompt or champion.prompt,
        workflow_steps=workflow_steps or champion.workflow_steps,
        model_route=model_route or champion.model_route,
        retrieval_policy=retrieval_policy or champion.retrieval_policy,
        response_contract=response_contract or champion.response_contract,
    )


def propose_mutations(champion: AgentVersion) -> list[AgentVersion]:
    """Generate bounded configuration candidates without rewriting production code."""

    candidates: list[AgentVersion] = []
    if champion.response_contract == "plain":
        candidates.append(
            _candidate(
                champion,
                mutation_type="structured-response-contract",
                reason="Improve parsing consistency and evidence traceability.",
                prompt=champion.prompt.rstrip()
                + "\nReturn a structured answer with finding and evidence fields.",
                response_contract="structured",
            )
        )
    elif champion.response_contract == "structured":
        candidates.append(
            _candidate(
                champion,
                mutation_type="evidence-linked-response-contract",
                reason="Add calibrated confidence and exact evidence linkage.",
                prompt=champion.prompt.rstrip()
                + "\nReturn finding, calibrated confidence, and exact supporting evidence.",
                response_contract="evidence-linked",
            )
        )

    if "critic" not in champion.workflow_steps:
        candidates.append(
            _candidate(
                champion,
                mutation_type="critic-workflow-stage",
                reason="Add an explicit adversarial verification pass before the final answer.",
                workflow_steps=("analyze", "retrieve", "critic", "verify", "answer"),
            )
        )

    if champion.retrieval_policy != "evidence-first":
        candidates.append(
            _candidate(
                champion,
                mutation_type="evidence-first-retrieval",
                reason="Require evidence selection before conclusion generation.",
                retrieval_policy="evidence-first",
            )
        )

    if champion.model_route != "reasoning":
        candidates.append(
            _candidate(
                champion,
                mutation_type="reasoning-route",
                reason="Route complex cases through the reasoning model tier.",
                model_route="reasoning",
            )
        )

    if not candidates:
        candidates.append(
            _candidate(
                champion,
                mutation_type=f"generation-{champion.generation + 1}-verification-tuning",
                reason="Test a stricter verification policy after the main policy lattice is mature.",
                prompt=champion.prompt.rstrip()
                + "\nBefore answering, reject any claim that cannot be tied to supplied evidence.",
            )
        )
    return candidates
