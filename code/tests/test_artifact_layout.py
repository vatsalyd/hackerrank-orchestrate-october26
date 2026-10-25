import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit.artifact_layout import image_layout, subject_bindings
from audit.extraction import Extractor
from audit.native_artifacts import native_records


def word(text,x,y):
    return dict(text=text,x=x,y=y,width=max(15,len(text)*5),height=10)


class ArtifactLayoutTest(unittest.TestCase):
    def test_tesseract_layout_preserves_multiword_lines(self):
        tsv=('level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
             '1\t1\t0\t0\t0\t0\t0\t0\t1000\t600\t-1\t\n'
             '5\t1\t1\t1\t1\t1\t100\t100\t10\t10\t90\t2\n'
             '5\t1\t1\t1\t1\t2\t120\t100\t30\t10\t90\thits\n')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            image=root/'screen.png'
            image.write_bytes(b'fictional test image')
            with patch('audit.artifact_layout.os',SimpleNamespace(name='posix')), \
                 patch('audit.artifact_layout.shutil.which',return_value='tesseract'), \
                 patch('audit.artifact_layout.subprocess.run',return_value=SimpleNamespace(stdout=tsv)):
                layout=image_layout(image,root/'cache')
        self.assertEqual(layout['text'],'2 hits')
        self.assertEqual(len(layout['words']),2)

    def test_table_ownership_stays_on_its_row(self):
        layout=dict(width=1000,height=600,words=[
            word('export_1',100,100),word('one@example.test',350,101),
            word('export_2',100,150),word('two@example.test',350,149)])
        bindings=subject_bindings(layout)
        self.assertEqual(bindings['export_1']['identifiers'],frozenset({'one@example.test'}))
        self.assertEqual(bindings['export_2']['identifiers'],frozenset({'two@example.test'}))

    def test_selected_panel_excludes_other_rows_and_activity_history(self):
        layout=dict(width=1000,height=600,words=[
            word('export_1',100,100),word('other@example.test',350,100),
            word('export_2',100,150),word('selected@example.test',350,150),
            word('export_2',800,80),word('Owner',800,110),word('selected@example.test',800,135),
            word('Created',800,160),
            word('Activity',800,200),word('unrelated@example.test',800,240)])
        binding=subject_bindings(layout)['export_2']
        self.assertEqual(binding['scope'],'selected_panel')
        self.assertEqual(binding['identifiers'],frozenset({'selected@example.test'}))

    def test_rightmost_table_column_is_not_assumed_to_be_a_detail_panel(self):
        layout=dict(width=1000,height=600,words=[
            word('export_1',800,100),word('one@example.test',900,100),
            word('export_2',800,150),word('two@example.test',900,150)])
        bindings=subject_bindings(layout)
        self.assertEqual(bindings['export_1']['identifiers'],frozenset({'one@example.test'}))
        self.assertEqual(bindings['export_2']['identifiers'],frozenset({'two@example.test'}))

    def test_flat_multi_subject_transcript_cannot_assign_one_flow_to_everyone(self):
        rows=list(native_records('Connections\nother@example.test\nselected@example.test\n'
                                 'data_flow_1\nContinuous sync\n124 events delivered'))
        self.assertFalse(rows[0]['identifiers'])

    def test_extraction_does_not_reintroduce_unbound_transcript_identifiers(self):
        layout=dict(width=1000,height=600,words=[],text=
            'Ready exports\nexport_1\nexport_2\none@example.test\ntwo@example.test')
        extractor=Extractor(SimpleNamespace(),artifact_mode='native')
        with patch('audit.artifact_layout.image_layout',return_value=layout):
            extractor.artifact_file(Path('unused.png'),
                {'file_id':'screenshot','captured_at':'2026-01-01T00:00:00Z'})
        self.assertEqual(len(extractor.observations),2)
        self.assertTrue(all(not obs.identifiers for obs in extractor.observations))

    def test_model_identifiers_and_raw_fields_cannot_override_selected_panel_owner(self):
        layout=dict(width=1000,height=600,words=[word('export_2',800,80),
            word('Owner',800,110),word('selected@example.test',800,130),
            word('Created',800,160),word('Activity',800,200)],
            text='Ready exports\nexport_2\nother@example.test\nselected@example.test')
        class Model:
            def json(self,*args,validator=None,**kwargs):
                result={'text':layout['text'],'records':[dict(resource_id='export_2',category='USER_EXPORT',
                    system_id='export_service',state='PRESENT',observed_at='',
                    identifiers=['selected@example.test','other@example.test'],fields={'email':'other@example.test'})]}
                validator(result)
                return result
        extractor=Extractor(SimpleNamespace(),Model(),artifact_mode='model')
        with patch('audit.artifact_layout.image_layout',return_value=layout):
            extractor.artifact_file(Path('unused.png'),
                {'file_id':'screenshot','origin':'export_service','captured_at':'2026-01-01T00:00:00Z'})
        self.assertEqual(extractor.observations[0].identifiers,frozenset({'selected@example.test'}))
