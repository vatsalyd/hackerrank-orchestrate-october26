from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import replace

from .extraction import resource_kind
from .identifiers import identifiers, normalize
from .models import Observation, UnresolvedCase, instant


class EvidenceIndex:
    def __init__(self, dataset, extraction):
        self.dataset, self.extraction = dataset, extraction
        self.by_identifier, self.by_resource = defaultdict(list), defaultdict(list)
        for observation in extraction.observations:
            self.by_resource[(observation.system_id, observation.resource_id)].append(observation)
            for value in observation.identifiers:
                self.by_identifier[value].append(observation)

    def retrieve(self, subject_ids, cutoff, request=None, subject_reference=None):
        resources, observations, links = set(), [], []
        for value in subject_ids:
            for obs in self.by_identifier.get(value, []):
                if obs.eligible(cutoff):
                    resources.add((obs.system_id, obs.resource_id))
        aliases = {}
        for activity in self.dataset.activities:
            if instant(activity["event_time"]) > instant(cutoff):
                continue
            if identifiers(activity["details"]) & subject_ids:
                resource = activity["resource_id"]
                system = resource_kind(resource)[0] or activity["target_system"]
                resources.add((system, resource))
                links.append(activity)
                # Explicit catalog links ground an external business reference to a resource.
                match = re.search(r"\(([^)]+)\)", activity["details"])
                if activity["event_type"] == "LINK_RESOURCE_IDENTITY" and match:
                    aliases[normalize(match[1])] = (system, resource)
        # Remap an artifact's literal business reference using only eligible catalog links.
        for obs in self.extraction.observations:
            target = aliases.get(normalize(obs.resource_id))
            if target and obs.eligible(cutoff):
                observations.append(replace(obs, system_id=target[0], resource_id=target[1]))
                resources.discard((obs.system_id, obs.resource_id))
                resources.add(target)
        for resource in sorted(resources):
            observations.extend(obs for obs in self.by_resource.get(resource, []) if obs.eligible(cutoff))
        for table in self.extraction.tables:
            if max(instant(table.captured_at), instant(table.observed_at)) > instant(cutoff):
                continue
            for system, resource in resources:
                if (table.category == "USER_PROFILE" and table.scope.startswith("customer_profiles")
                    and system == table.system_id and resource_kind(resource)[1] == table.category and resource not in table.resources):
                    observations.append(Observation(table.evidence_id, table.captured_at, table.observed_at,
                        system, resource, table.category, "ABSENT", subject_ids, table.scope,
                        f"{table.scope}:query:{resource}", {"query": resource, "rows": 0}, 4))
        # A deleted row can lose its physical key while the supplied stable subject
        # reference remains a valid indexed lookup target. Use it for negative
        # verification only, never to synthesize a destructive record action.
        has_profile=any(obs.category=='USER_PROFILE' for obs in observations)
        if subject_reference and not has_profile:
            for table in self.extraction.tables:
                if (table.supports_subject_query and table.category=='USER_PROFILE'
                    and max(instant(table.captured_at),instant(table.observed_at))<=instant(cutoff)
                    and not (table.subject_identifiers & subject_ids)):
                    observations.append(Observation(table.evidence_id,table.captured_at,table.observed_at,
                        table.system_id,subject_reference,'USER_PROFILE','ABSENT',subject_ids,table.scope,
                        f'{table.scope}:subject-lookup',{'lookup_reference':subject_reference,
                        'binding_kind':'subject_lookup','matched_rows':0,'complete_snapshot':True},4))
        return observations, links


def reconstruct(observations):
    """Latest direct state for each concrete scope; preserve independent replica state."""
    scoped = defaultdict(list)
    known_restore = {(obs.system_id,obs.resource_id) for obs in observations
        if obs.category == "BACKUP_ARCHIVE" and obs.state in {"ACTIVE","BLOCKED"}}
    for obs in observations:
        if obs.category == "BACKUP_ARCHIVE" and obs.state == "PRESENT" and (obs.system_id,obs.resource_id) in known_restore:
            # Archive presence is not a later change to restore authorization.
            continue
        # Replica-specific evidence remains independent of a primary/generic read.
        scope = obs.scope if "replica" in obs.scope else ""
        scoped[(obs.system_id, obs.resource_id, scope)].append(obs)
    resolved = defaultdict(list)
    for (system, resource, scope), values in scoped.items():
        newest_time = max(instant(obs.observed_at) for obs in values)
        current = [obs for obs in values if instant(obs.observed_at) == newest_time]
        strength = max(obs.strength for obs in current)
        current = [obs for obs in current if obs.strength == strength]
        states = {obs.state for obs in current}
        if len(states) > 1:
            raise UnresolvedCase(f"Conflicting simultaneous evidence for {system}/{resource}/{scope}: {sorted(states)}")
        resolved[(system, resource)].append(sorted(current, key=lambda o: (o.evidence_id, o.location))[0])
    return resolved
