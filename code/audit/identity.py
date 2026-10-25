from __future__ import annotations

from collections import defaultdict

from .identifiers import normalize
from .models import UnresolvedCase, instant


class IdentityResolver:
    def __init__(self, dataset):
        self.dataset = dataset
        self.cache = {}

    def at(self, cutoff):
        if cutoff in self.cache:
            return self.cache[cutoff]
        subjects = defaultdict(set)
        for row in self.dataset.identities:
            if instant(row["updated_at"]) <= instant(cutoff):
                subjects[row["user_id"]].update(normalize(row[key]) for key in
                    ("user_id", "email", "phone", "email_hash") if row[key])
        for row in self.dataset.audits:
            if instant(row["event_time"]) <= instant(cutoff) and row["field_name"] in {"email", "phone", "email_hash"}:
                subjects[row["user_id"]].add(normalize(row["user_id"]))
                subjects[row["user_id"]].update(normalize(row[key]) for key in ("old_value", "new_value") if row[key])
        aliases = defaultdict(set)
        for user, values in subjects.items():
            for value in values:
                aliases[value].add(user)
        self.cache[cutoff] = subjects, aliases
        return subjects, aliases

    def resolve(self, email, cutoff):
        subjects, aliases = self.at(cutoff)
        users = aliases.get(normalize(email), set())
        if len(users) != 1:
            raise UnresolvedCase(f"Expected one temporally eligible subject; found {len(users)}")
        user = next(iter(users))
        return user, frozenset(value for value in subjects[user] if len(aliases[value]) == 1)
