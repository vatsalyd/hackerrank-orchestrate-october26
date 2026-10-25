from .models import Decision, OPERATIONS, Step


def build_decision(case_id, resolved, policy, cutoff=None):
    violations, compliant = [], []
    for resource, observations in sorted(resolved.items()):
        evaluated = [(obs, policy.apply(obs, cutoff)) for obs in observations]
        bad = [(obs, treatment) for obs, treatment in evaluated if not treatment.compliant]
        if bad:
            # One required action per logical resource, even when several replicas prove it.
            choices = sorted(bad, key=lambda pair: (-pair[0].strength, pair[0].evidence_id))
            violations.append(choices[0])
        else:
            compliant.append(sorted(evaluated, key=lambda pair: (-pair[0].strength, pair[0].evidence_id))[0])
    steps = []
    def add(obs, phase, operation, evidence=""):
        steps.append(Step(step_no=1, phase=phase, system_id=obs.system_id, resource_id=obs.resource_id,
                          operation=operation, state=OPERATIONS[phase][operation], evidence_id=evidence))
    if violations:
        for obs, treatment in violations:
            add(obs, "FINDING", treatment.finding, obs.evidence_id)
            add(obs, "REMEDIATION", treatment.remediation)
            add(obs, "VERIFICATION", treatment.verification)
        # Verify the required final state of every discovered relevant resource.
        for obs, treatment in compliant:
            add(obs, "VERIFICATION", treatment.verification)
        status = "INCOMPLETE"
    else:
        for obs, treatment in compliant:
            add(obs, "VERIFICATION", treatment.verification, obs.evidence_id)
        status = "COMPLETE"
    steps = [step.model_copy(update={"step_no": i}) for i, step in enumerate(sorted(steps, key=lambda s: s.sort_key()), 1)]
    return Decision(case_id=case_id, deletion_status=status, steps=steps)
