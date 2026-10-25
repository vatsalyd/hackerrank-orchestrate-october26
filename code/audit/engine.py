from __future__ import annotations

from dataclasses import asdict

from .identity import IdentityResolver
from .models import Decision, UnresolvedCase
from .planner import build_decision
from .policy import Policy
from .timeline import EvidenceIndex, reconstruct
from .validation import validate_citations


class Auditor:
    def __init__(self, dataset, extraction):
        self.dataset = dataset
        self.identity = IdentityResolver(dataset)
        self.index = EvidenceIndex(dataset, extraction)
        self.policy = Policy(dataset.rules)

    def audit(self, request, deletion_authorized):
        if not deletion_authorized:
            return Decision(case_id=request.case_id, deletion_status="NOT_APPLICABLE", steps=[]), {}
        user, aliases = self.identity.resolve(request.email, request.audit_at)
        observations, links = self.index.retrieve(aliases, request.audit_at, request)
        if not observations:
            raise UnresolvedCase("No eligible resource-state evidence for this subject")
        resolved = reconstruct(observations)
        decision = build_decision(request.case_id, resolved, self.policy, request.audit_at)
        if decision.deletion_status == "COMPLETE" and not any(
            observation.category == "USER_PROFILE" and observation.state == "ABSENT"
            for values in resolved.values() for observation in values
        ):
            raise UnresolvedCase("No grounded primary-profile absence proof for a complete verdict")
        validate_citations(decision, request.audit_at, self.dataset.citation_times)
        facts = []
        for resource in sorted(resolved):
            for observation in resolved[resource]:
                fact = asdict(observation)
                fact["identifiers"] = sorted(fact["identifiers"])
                facts.append(fact)
        return decision, {"user_id": user, "resource_count": len(resolved), "facts": facts,
                          "linking_activity_ids": [link["activity_id"] for link in links]}
