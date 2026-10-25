from .models import Decision, instant


def validate_citations(decision: Decision, cutoff: str, citation_times: dict[str, str]):
    for step in decision.steps:
        if step.evidence_id:
            captured = citation_times.get(step.evidence_id)
            if captured is None or instant(captured) > instant(cutoff):
                raise ValueError(f"Unknown or post-cutoff citation: {step.evidence_id}")
