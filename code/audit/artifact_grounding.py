"""Ground model interpretations in independently extracted literal references."""
import re

from .identifiers import RESOURCE, normalize
from .native_artifacts import native_records


def literal_resources(text):
    prefixes=r"account|analytics|search|support|export|marketing|backup|data_flow|audit_record|tombstone|object|legal_hold"
    text=re.sub(r"\b("+prefixes+r")\s*_\s*([A-Za-z0-9]+)\b",r"\1_\2",text)
    return {match.group() for match in RESOURCE.finditer(text)}


def ground_records(records, text, kind_for_resource, primary_only=False, resource_identifiers=None):
    native=list(native_records(text))
    refs=literal_resources(text) | {record['resource_id'] for record in native}
    primary_categories={record['category'] for record in native}
    grounded, issues=[],[]
    category_system={category:system for system,category in (
        kind_for_resource(ref) for ref in refs) if category!='UNKNOWN'}
    for record in records:
        record=dict(record)
        category=record['category']
        if primary_only and primary_categories and category not in primary_categories:
            issues.append('Skipped a related-link claim outside the primary artifact category')
            continue
        resource=record['resource_id']
        if resource not in refs:
            candidates=[candidate for candidate in native if candidate['category']==category]
            supplied={normalize(value) for value in record.get('identifiers',[])}
            matches=[candidate for candidate in candidates if candidate['identifiers'] & supplied]
            if len(matches)==1:
                resource=matches[0]['resource_id']
            elif len(candidates)==1:
                resource=candidates[0]['resource_id']
            else:
                compatible=[ref for ref in refs if kind_for_resource(ref)[1]==category]
                if len(compatible)!=1:
                    issues.append('Model reference could not be bound uniquely to a literal artifact reference')
                    continue
                resource=compatible[0]
        system, literal_category=kind_for_resource(resource)
        if literal_category!='UNKNOWN' and literal_category!=category and category!='SECONDARY_IDENTIFIER':
            issues.append('Model category conflicts with the literal resource type')
            continue
        record['resource_id']=resource
        if resource_identifiers is not None and resource in resource_identifiers:
            record['identifiers']=sorted(resource_identifiers[resource])
        record['system_id']=system or category_system.get(category) or record['system_id']
        if category in {'USER_PROFILE','SUPPORT_ATTACHMENT','USER_EXPORT','MARKETING_PROFILE','SEARCH_INDEX_ENTRY'} and record['state']=='IDENTIFIABLE':
            record['state']='PRESENT'
        grounded.append(record)
    return grounded,issues
