"""Independent fictional scenarios run through the actual CLI, without network."""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit.models import Decision


class EndToEndTest(unittest.TestCase):
    def test_three_authorization_and_policy_scenarios(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); dataset=root/'dataset'; evidence=dataset/'evidence/records'
            evidence.mkdir(parents=True)
            def write(name, fields, rows):
                with (dataset/name).open('w',encoding='utf-8',newline='') as stream:
                    writer=csv.DictWriter(stream,fieldnames=fields.split(','));writer.writeheader();writer.writerows(rows)
            write('user_identities.csv','user_id,name,email,phone,email_hash,updated_at',[
                dict(user_id=f'user_{i}',name=f'Fixture {i}',email=f'fixture{i}@example.test',phone='',email_hash='',updated_at='2026-01-01T00:00:00Z') for i in range(3)])
            write('user_audit_log.csv','audit_id,user_id,event_time,field_name,old_value,new_value',[])
            write('system_activity.csv','activity_id,event_time,event_type,source_system,target_system,resource_id,reported_result,details',[])
            write('deletion_rules.csv','rule_id,data_category,condition,required_action',[
                dict(rule_id=f'r{i}',data_category=category,condition=condition,required_action=action) for i,(category,condition,action) in enumerate([
                    ('USER_PROFILE','Always','DELETE'),('SUPPORT_MESSAGE','Shared context','REDACT'),
                    ('SECURITY_AUDIT_LOG','Within supplied retention','RETAIN'),('BACKUP_ARCHIVE','Restore can be blocked','RETAIN')])])
            write('evidence_files.csv','file_id,file_path,origin,captured_at',[
                dict(file_id='fixture_capture',file_path='evidence/records/fixture.json',origin='independent_fixture',captured_at='2026-02-01T00:00:00Z')])
            records=[]
            for user,system,resource,category,state in [
                ('user_1','account_service','account_clean','USER_PROFILE','NOT_FOUND'),
                ('user_1','security_service','audit_record_clean','SECURITY_AUDIT_LOG','FOUND'),
                ('user_2','account_service','account_remaining','USER_PROFILE','FOUND'),
                ('user_2','integration_service','data_flow_active','DATA_FLOW','ACTIVE'),
                ('user_2','backup_service','backup_active','BACKUP_ARCHIVE','ACTIVE'),
                ('user_2','support_platform','support_shared','SUPPORT_MESSAGE','IDENTIFIABLE')]:
                records.append(dict(recorded_at='2026-02-01T00:00:00Z',system=system,resource_id=resource,
                    record_type=category,result=state,subject_reference=user))
            (evidence/'fixture.json').write_text(json.dumps({'records':records}),encoding='utf-8')
            write('sample_deletion_requests.csv','case_id,email,requested_at,reported_status,reported_at,audit_at,request_text',[
                dict(case_id=f'fixture_{i}',email=f'fixture{i}@example.test',requested_at='2026-01-15T00:00:00Z',
                    reported_status='COMPLETE',reported_at='2026-01-20T00:00:00Z',audit_at='2026-02-02T00:00:00Z',
                    request_text='Please export my data.' if i==0 else 'Please delete my account and personal data.') for i in range(3)])
            output=root/'output.csv'
            run=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'main.py'),'run','--sample',
                '--local-intent','--dataset',str(dataset),'--cache',str(root/'cache'),'--diagnostics-dir',str(root/'diagnostics'),
                '--output',str(output)],capture_output=True,text=True,cwd=root)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            with output.open(encoding='utf-8',newline='') as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual([r['deletion_status'] for r in rows],['NOT_APPLICABLE','COMPLETE','INCOMPLETE'])
            self.assertEqual(rows[0]['steps_json'],'[]')
            for row in rows:
                Decision(case_id=row['case_id'],deletion_status=row['deletion_status'],steps=json.loads(row['steps_json']))
            steps=json.loads(rows[2]['steps_json'])
            self.assertEqual([s['operation'] for s in steps if s['phase']=='REMEDIATION'],
                ['DISABLE_DATA_FLOW','BLOCK_RESTORE','DELETE_RECORD','REDACT_RECORD'])
