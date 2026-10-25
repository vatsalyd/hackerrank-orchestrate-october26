"""Format-specific extraction preserving observation time, scope, and provenance."""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

from .identifiers import identifiers, normalize
from .llm import ARTIFACT_PROMPT
from .models import ArtifactResult, Observation, instant

COLLECTIONS = {
    "customer_profiles": ("account_service", "USER_PROFILE"),
    "customer_search_documents": ("search_service", "SEARCH_INDEX_ENTRY"),
    "customer_analytics_reports": ("analytics_platform", "ANALYTICS_PROFILE"),
    "customer_export_jobs": ("export_service", "USER_EXPORT"),
    "connector_configurations": ("integration_service", "DATA_FLOW"),
    "backup_catalog": ("backup_service", "BACKUP_ARCHIVE"),
    "security_audit_events": ("security_service", "SECURITY_AUDIT_LOG"),
    "retained_order_records": ("legal_archive", "LEGAL_HOLD_RECORD"),
    "ticket_attachments": ("support_platform", "SUPPORT_ATTACHMENT"),
    "support_conversations": ("support_platform", "SUPPORT_MESSAGE"),
    "deleted_customer_references": ("identity_service", "ACCOUNT_TOMBSTONE"),
}
PREFIXES = {
    "account": ("account_service", "USER_PROFILE"), "search": ("search_service", "SEARCH_INDEX_ENTRY"),
    "analytics": ("analytics_platform", "ANALYTICS_PROFILE"), "support": ("support_platform", "SUPPORT_MESSAGE"),
    "export": ("export_service", "USER_EXPORT"), "marketing": ("marketing_platform", "MARKETING_PROFILE"),
    "cache": ("cache_service", "CACHE_ENTRY"), "email_delivery": ("email_delivery_service", "EMAIL_DELIVERY_LOG"),
    "audit_record": ("security_service", "SECURITY_AUDIT_LOG"), "legal_hold": ("legal_archive", "LEGAL_HOLD_RECORD"),
    "backup": ("backup_service", "BACKUP_ARCHIVE"), "data_flow": ("integration_service", "DATA_FLOW"),
    "tombstone": ("identity_service", "ACCOUNT_TOMBSTONE"), "object": ("object_storage", "SUPPORT_ATTACHMENT"),
}
STATE_MAP = {"NOT_FOUND": "ABSENT", "FOUND": "PRESENT", "IDENTIFIABLE": "IDENTIFIABLE",
             "REDACTED": "REDACTED", "ANONYMIZED": "ANONYMIZED", "ACTIVE": "ACTIVE",
             "DISABLED": "DISABLED", "BLOCKED": "BLOCKED", "PRESENT": "PRESENT", "ABSENT": "ABSENT"}
NULLS = {None, "", "null", "NULL", "[REDACTED]", "redacted", "REDACTED", "removed", "-"}


def resource_kind(resource: str):
    prefix = resource.rsplit("_", 1)[0]
    return PREFIXES.get(prefix, ("", "UNKNOWN"))


def flattened(value, prefix=""):
    result = {}
    if isinstance(value, dict):
        for key, item in value.items():
            result.update(flattened(item, key))
    elif not isinstance(value, list):
        result[prefix] = value
    return result


def record_state(record, category):
    if "result" in record and record.get("record_type"):
        return STATE_MAP.get(str(record["result"]).upper(), "UNKNOWN")
    if category == "USER_PROFILE" and "status_code" in record:
        return "ABSENT" if record["status_code"] == 404 else "PRESENT" if record["status_code"] == 200 else "UNKNOWN"
    if category == "SEARCH_INDEX_ENTRY" and "hits" in record:
        return "PRESENT" if record["hits"] else "ABSENT"
    if category == "DATA_FLOW":
        flag = record.get("enabled")
        return ("ACTIVE" if flag == 1 else "DISABLED") if type(flag) in {bool,int} and flag in (0,1) else "UNKNOWN"
    if category == "BACKUP_ARCHIVE":
        flag = record.get("restore_allowed")
        return ("ACTIVE" if flag == 1 else "BLOCKED") if type(flag) in {bool,int} and flag in (0,1) else "UNKNOWN"
    if category in {"ANALYTICS_PROFILE", "PRODUCT_TELEMETRY", "SUPPORT_MESSAGE", "ACCOUNT_TOMBSTONE", "EMAIL_DELIVERY_LOG"}:
        flat = flattened(record)
        keys = {"email", "phone", "email_hash", "name", "full_name", "display_name", "requester_email", "requester_phone", "requester_name"}
        if category in {"ANALYTICS_PROFILE", "PRODUCT_TELEMETRY"}:
            keys |= {"user_id", "customer_reference", "subject_reference"}
        exposed = any(isinstance(flat.get(k), (str, int)) and flat.get(k) not in NULLS for k in keys)
        if category in {"SUPPORT_MESSAGE", "EMAIL_DELIVERY_LOG"}:
            exposed |= bool(identifiers(record.get("message_text", record.get("message_excerpt", ""))))
        return "IDENTIFIABLE" if exposed else ("ANONYMIZED" if category in {"ANALYTICS_PROFILE", "PRODUCT_TELEMETRY"} else "REDACTED")
    return "PRESENT"


@dataclass
class TableSnapshot:
    evidence_id: str
    captured_at: str
    observed_at: str
    system_id: str
    category: str
    scope: str
    resources: frozenset[str]


class Extractor:
    def __init__(self, dataset, model=None, cache=None):
        self.dataset, self.model = dataset, model
        self.observations = []
        self.tables = []
        self.coverage = {}
        self.artifact_text = {}
        self.skipped = []
        self.cache = cache or Path(".cache")

    def extract(self, structured_only=False):
        for manifest in self.dataset.manifest:
            file_id = manifest["file_id"]
            path = self.dataset.files[file_id]
            before = len(self.observations)
            if structured_only and path.suffix in {".pdf", ".png"}:
                self.skipped.append(file_id)
                continue
            if path.suffix == ".json":
                self.json_file(json.loads(path.read_text(encoding="utf-8")), manifest)
            elif path.suffix == ".sql":
                self.sql_file(path, manifest)
            elif path.suffix == ".log":
                self.log_file(path, manifest)
            elif path.suffix == ".txt":
                self.text_file(path.read_text(encoding="utf-8"), manifest)
            elif path.suffix in {".pdf", ".png"}:
                self.artifact_file(path, manifest)
            else:
                raise ValueError(f"Unsupported evidence format: {path.suffix}")
            self.coverage[file_id] = len(self.observations) - before
            print(f"Extracted {file_id}: {self.coverage[file_id]} observations", flush=True)
        for activity in self.dataset.activities:
            kind, text = activity["event_type"], activity["details"].casefold()
            direct = (kind == "CHECK_DATA_FLOW" and "remains enabled" in text) or (
                kind == "CHECK_RESTORE_ACCESS" and "can still be restored" in text)
            if direct:
                system, category = resource_kind(activity["resource_id"])
                self.add({"file_id":activity["activity_id"],"captured_at":activity["event_time"]},
                    system,activity["resource_id"],category,"ACTIVE",activity,location="details:direct-state-check",strength=1)
        return self

    def add(self, manifest, system, resource, category, state, raw, observed=None, scope="", location="", strength=2, extra_ids=()):
        if not system or not resource or category == "UNKNOWN" or state == "UNKNOWN":
            return
        self.observations.append(Observation(manifest["file_id"], manifest["captured_at"],
            observed or manifest["captured_at"], system, resource, category, state,
            identifiers(raw) | frozenset(normalize(x) for x in extra_ids if x), scope, location, raw, strength))

    def json_file(self, value, manifest, context=None, location="$"):
        context = dict(context or {})
        if isinstance(value, list):
            for i, item in enumerate(value):
                self.json_file(item, manifest, context, f"{location}[{i}]")
        elif isinstance(value, dict):
            for key in ("collection", "data_store", "captured_at"):
                if key in value:
                    context[key] = value[key]
            if "resource_id" in value:
                default_system, default_category = COLLECTIONS.get(context.get("collection"), resource_kind(value["resource_id"]))
                system = value.get("system", default_system)
                category = value.get("record_type", default_category)
                if "storage_class" in value and value["storage_class"] == "ticket_attachment":
                    category = "SUPPORT_ATTACHMENT"
                self.add(manifest, system, value["resource_id"], category, record_state(value, category), value,
                    value.get("recorded_at", value.get("observed_at", context.get("captured_at"))), location=location, strength=3)
                return
            for key, item in value.items():
                self.json_file(item, manifest, context, f"{location}.{key}")

    def sql_file(self, path, manifest):
        sql = path.read_text(encoding="utf-8")
        # Run supplied snapshots in isolated memory, disallow filesystem attachment and extensions.
        connection = sqlite3.connect(":memory:")
        connection.set_authorizer(lambda action, *args: sqlite3.SQLITE_DENY if action in
            (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH) else sqlite3.SQLITE_OK)
        try:
            connection.executescript(sql)
            tables = [name for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            scopes = dict(connection.execute("SELECT origin_system,captured_at FROM snapshot_scope")) if "snapshot_scope" in tables else {}
            for table in tables:
                quoted = '"' + table.replace('"', '""') + '"'
                cursor = connection.execute(f"SELECT * FROM {quoted}")
                columns = [item[0] for item in cursor.description]
                records = [dict(zip(columns, row)) for row in cursor]
                if "resource_id" not in columns:
                    continue
                if "record_json" in columns:
                    for i, wrapper in enumerate(records):
                        record = json.loads(wrapper["record_json"])
                        system, category = COLLECTIONS.get(wrapper.get("collection_name"), resource_kind(wrapper["resource_id"]))
                        system = wrapper.get("origin_system", system)
                        self.add(manifest, system, wrapper["resource_id"], category, record_state(record, category),
                                 record, scope=table, location=f"{table}:row:{i + 1}:record_json", strength=4)
                    continue
                collection = next((name for name in COLLECTIONS if table.startswith(name)), None)
                if collection:
                    system, category = COLLECTIONS[collection]
                elif records:
                    system, category = resource_kind(records[0]["resource_id"])
                else:
                    continue
                observed_at = scopes.get(system,manifest["captured_at"])
                if not scopes or system in scopes:
                    self.tables.append(TableSnapshot(manifest["file_id"], manifest["captured_at"], observed_at,
                        system, category, table, frozenset(row["resource_id"] for row in records)))
                for i, row in enumerate(records):
                    row_system = row.get("system", system)
                    row_category = row.get("record_type", category)
                    self.add(manifest, row_system, row["resource_id"], row_category, record_state(row, row_category), row,
                             row.get("recorded_at", observed_at),
                             scope=table, location=f"{table}:row:{i + 1}", strength=4)
        finally:
            connection.close()

    @staticmethod
    def parse_log(line):
        timestamp = line[:20]
        try:
            instant(timestamp)
        except ValueError:
            return None
        rest = line[20:].strip()
        if rest.startswith("{"):
            fields = json.loads(rest)
        else:
            # Cloud runtime wraps quoted key/value fields inside an escaped message.
            clean = re.sub(r'\bmessage="', '', rest.replace('\\"', '"'))
            # re.findall represents unmatched alternatives as empty strings.
            fields = {key: value or bare for key, value, bare in
                re.findall(r'(\w+)=(?:"([^"\n]*)"|([^\s|]+))', clean)}
            bracket = re.match(r'\[[^]]+\] \[([^]]+)\] \[([^]]+)\] ([^: ]+):', rest)
            pipe = re.match(r'\| [^|]+ \| ([^|]+) \| ([^|]+) \| ([^|]+) \|', rest)
            syslog = re.match(r'<\d+>1 \S+ (\S+) (\S+) - -', rest)
            if bracket or pipe:
                match = bracket or pipe
                fields.update(service=match[1].strip(), trace_id=match[2].strip(), event=match[3].strip())
            elif syslog:
                fields.update(service=syslog[1], trace_id=syslog[2])
        fields["timestamp"] = timestamp
        fields.setdefault("service", fields.get("function", fields.get("system", "")))
        fields.setdefault("trace_id", fields.get("requestId", ""))
        return fields

    def log_file(self, path, manifest):
        lines = []
        traces = defaultdict(list)
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            fields = self.parse_log(line)
            if fields:
                fields["line_no"] = number
                lines.append(fields)
                if fields.get("trace_id"):
                    traces[(fields["service"], fields["trace_id"])].append(fields)
        for fields in lines:
            resource = fields.get("resource_id")
            if not resource:
                continue
            related = traces.get((fields["service"], fields.get("trace_id")), [])
            # Join only preceding trace lines, never later facts into earlier observations.
            ids = frozenset().union(*(identifiers(item) for item in related if item["timestamp"] <= fields["timestamp"]))
            system, category = resource_kind(resource)
            event = fields.get("event", "")
            state = "UNKNOWN"
            if fields.get("record_type"):
                system, category = fields.get("system", system), fields["record_type"]
                state = STATE_MAP.get(fields.get("result", ""), "UNKNOWN")
            elif event in {"profile_lookup_completed", "contact_query_completed"}:
                if event == "contact_query_completed":
                    category, system = "SECONDARY_IDENTIFIER", "support_platform"
                state = "ABSENT" if str(fields.get("rows")) == "0" else "PRESENT" if str(fields.get("rows")) == "1" else "UNKNOWN"
            elif event == "index_query_completed":
                state = "PRESENT" if fields.get("result") == "hit" else "ABSENT" if fields.get("result") in {"miss", "not_found"} else "UNKNOWN"
            elif event in {"message_pii_scan", "attachment_pii_scan", "analytics_identity_scan"}:
                category = {"message_pii_scan": "SUPPORT_MESSAGE", "attachment_pii_scan": "SUPPORT_ATTACHMENT",
                            "analytics_identity_scan": "ANALYTICS_PROFILE"}[event]
                state = "PRESENT" if category == "SUPPORT_ATTACHMENT" else "IDENTIFIABLE"
            elif event in {"analytics_profile_read", "analytics_profile_read_completed"}:
                if event.endswith("completed"):
                    state = record_state(fields, category)
                else:
                    state = "ANONYMIZED" if str(fields.get("direct_identifiers")) == "0" else "IDENTIFIABLE"
            elif event in {"audit_record_read_completed", "legal_hold_record_read_completed"}:
                state = "PRESENT" if str(fields.get("rows")) == "1" else "UNKNOWN"
            elif event in {"connector_heartbeat", "connector_config_loaded", "connector_config_read_completed"}:
                flag = str(fields.get("enabled", fields.get("state", ""))).lower()
                state = "ACTIVE" if flag in {"true", "1", "enabled", "active"} else "DISABLED" if flag in {"false", "0", "disabled", "inactive"} else "UNKNOWN"
            elif event in {"restore_candidate_evaluated", "restore_authorization_completed", "restore_policy_read_completed"}:
                permission = fields.get("restore_allowed", fields.get("allowed", fields.get("decision", fields.get("eligible", ""))))
                if str(fields.get("deletion_block", "")).lower() == "true":
                    permission = "deny"
                state = "ACTIVE" if str(permission).lower() in {"true", "1", "allow", "allowed"} else "BLOCKED" if str(permission).lower() in {"false", "0", "deny", "denied", "blocked"} else "UNKNOWN"
            elif event in {"export_download_check_completed", "export_metadata_read_completed"}:
                available = str(fields.get("available", "")).lower()
                state = "PRESENT" if available == "true" or str(fields.get("http_status")) == "200" else "ABSENT" if available == "false" or str(fields.get("http_status")) in {"404", "410"} else "UNKNOWN"
            elif event == "message_read":
                state = record_state(fields, category)
            elif event == "support_ticket_read_completed":
                state = record_state(fields, category)
            elif event == "retained_order_loaded":
                state = "PRESENT" if fields.get("access") == "allowed" else "UNKNOWN"
            elif event == "contact_lookup_completed":
                category = "SECONDARY_IDENTIFIER"
                state = "PRESENT" if str(fields.get("rows")) == "1" else "ABSENT" if str(fields.get("rows")) == "0" else "UNKNOWN"
            self.add(manifest, system, resource, category, state, fields, fields["timestamp"],
                     location=f"line:{fields['line_no']};trace:{fields.get('trace_id', '')}", extra_ids=ids)

    def text_file(self, text, manifest):
        for number, line in enumerate(text.splitlines(), 1):
            pieces = [value.strip() for value in line.lstrip("- ").split("|")]
            if len(pieces) != 6:
                continue
            at, system, resource, category, state, subject = pieces
            self.add(manifest, system, resource, category, STATE_MAP.get(state, "UNKNOWN"),
                     {"subject_reference": subject}, at, location=f"line:{number}")

    def artifact_file(self, path, manifest):
        if self.model is None:
            from .native_artifacts import artifact_text, native_records
            text = artifact_text(path, self.cache)
            self.artifact_text[manifest["file_id"]] = text
            for number, record in enumerate(native_records(text),1):
                self.add(manifest, record["system_id"], record["resource_id"], record["category"], record["state"],
                         record["fields"], location=f"native-artifact:{number}", extra_ids=record["identifiers"])
            return
        data = {"capture_time": manifest["captured_at"], "source_origin": manifest["origin"]}
        if path.suffix == ".pdf":
            from pypdf import PdfReader
            data["pages"] = [{"page": i, "text": page.extract_text()} for i, page in enumerate(PdfReader(path).pages, 1)]
        result = self.model.json("artifact-extraction-v1", ARTIFACT_PROMPT, data, path if path.suffix == ".png" else None)
        result = ArtifactResult.model_validate(result).model_dump()
        self.artifact_text[manifest["file_id"]] = result["text"]
        for number, record in enumerate(result["records"], 1):
            resource = record["resource_id"]
            default_system, default_category = resource_kind(resource)
            system = default_system or record.get("system_id")
            category = record.get("category", default_category)
            if not system:
                system = next((sys for sys, cat in PREFIXES.values() if cat == category), "")
            if path.suffix == ".pdf" and normalize(resource) not in normalize(" ".join(page["text"] for page in data["pages"])):
                raise ValueError(f"Model supplied a reference absent from native PDF text: {manifest['file_id']}")
            self.add(manifest, system, resource, category, record["state"], record.get("fields", {}),
                     # Business creation dates are not current-state observation times.
                     manifest["captured_at"], location=f"artifact-record:{number}",
                     extra_ids=record.get("identifiers", []))
