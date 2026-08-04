from __future__ import annotations

import hashlib

from prime_genesis.models import AgentVersion


MUTATIONS = (
    (
        "structured-output",
        "Return a structured answer with finding and evidence.",
        "Improve consistency and downstream parsing.",
    ),
    (
        "evidence-linked-output",
        "Return an evidence-linked answer with finding, confidence, and exact evidence.",
        "Increase traceability and calibrated decision support.",
    ),
    (
        "concise-verification",
        "Return only verified findings and omit unsupported assumptions.",
        "Reduce hallucination and unnecessary output.",
    ),
)


def _version_id(parent: str, mutation_type: str, prompt: str) -> str:
    digest = hashlib.sha256(f"{parent}|{mutation_type}|{prompt}".encode()).hexdigest()[:10]
    return f"prime-{digest}"


def propose_mutations(champion: AgentVersion) -> list[AgentVersion]:
    candidates: list[AgentVersion] = []
    for mutation_type, instruction, reason in MUTATIONS:
        prompt = f"{champion.prompt.rstrip()}\n{instruction}"
        candidates.append(
            AgentVersion(
                version_id=_version_id(champion.version_id, mutation_type, prompt),
                prompt=prompt,
                parent_version_id=champion.version_id,
                mutation_type=mutation_type,
                mutation_reason=reason,
            )
        )
    return candidates
