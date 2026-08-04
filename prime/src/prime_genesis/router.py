from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteRequest:
    domain: str
    text: str
    sensitivity: str = "standard"
    max_cost_usd: float | None = None
    latency_target_ms: int | None = None


@dataclass(frozen=True)
class RouteDecision:
    tier: str
    reason: str
    required_capabilities: tuple[str, ...]


class ModelRouter:
    COMPLEX_TERMS = {"simulate", "counterfactual", "architecture", "conflict", "root cause", "compliance", "forecast", "tradeoff"}

    def route(self, request: RouteRequest) -> RouteDecision:
        sensitivity = request.sensitivity.lower()
        lowered = request.text.lower()
        if sensitivity in {"restricted", "private", "regulated"}:
            return RouteDecision("local-private", "Sensitive workload requires a customer-controlled model boundary.", ("private-inference", "audit"))
        if request.max_cost_usd is not None and request.max_cost_usd <= 0.001:
            return RouteDecision("fast", "A strict cost ceiling requires the fast model tier.", ("text",))
        if len(request.text) > 1_500 or any(term in lowered for term in self.COMPLEX_TERMS):
            return RouteDecision("reasoning", "The request contains multi-step or counterfactual reasoning signals.", ("reasoning", "structured-output"))
        if request.latency_target_ms is not None and request.latency_target_ms <= 500:
            return RouteDecision("fast", "The latency target requires the fast model tier.", ("text",))
        return RouteDecision("balanced", "The workload fits the balanced quality, latency, and cost tier.", ("text", "structured-output"))
