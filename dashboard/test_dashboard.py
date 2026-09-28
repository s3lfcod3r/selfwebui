import unittest
from unittest.mock import patch
import tokens
class TokenTests(unittest.TestCase):
 def setUp(self):tokens.stand={'roh':{},'tage':{},'spitze':{}}
 def test_poll_does_not_double_count(self):
  tokens.verbuche({'server|RTX2000|ein':100},{})
  tokens.verbuche({'server|RTX2000|ein':100},{})
  tokens.verbuche({'server|RTX2000|ein':125},{})
  self.assertEqual(tokens.antwort()['heute']['gesamt']['ein'],125)
 def test_server_restart(self):
  tokens.verbuche({'server|RTX2000|aus':100},{})
  tokens.verbuche({'server|RTX2000|aus':5},{})
  self.assertEqual(tokens.antwort()['heute']['gesamt']['aus'],105)
 def test_agent_history_not_added_to_server_totals(self):
  result=tokens.summen({'server|RTX2000|ein':10,'agent|cloud|openai|ein':50})
  self.assertEqual(result['gesamt']['ein'],10)
  self.assertEqual(result['agenten'],{})
import tempfile
from pathlib import Path
import projects
class ProjectTests(unittest.TestCase):
 def test_deleted_status_disappears_on_next_request(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);project=root/'example';project.mkdir();status=project/'STATUS.md'
   status.write_text('## Offene Fragen\n- Testfrage?\n',encoding='utf-8')
   with patch.object(projects,'BEREICHE',[('',root)]):
    self.assertEqual(len(projects.status()['projekte']),1)
    status.unlink()
    self.assertEqual(projects.status()['projekte'],[])
 def test_deleted_question_is_not_cached(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);project=root/'example';project.mkdir();status=project/'STATUS.md'
   with patch.object(projects,'BEREICHE',[('',root)]):
    status.write_text('## Offene Fragen\n- Testfrage?\n',encoding='utf-8')
    self.assertEqual(projects.status()['projekte'][0]['fragen'],['Testfrage?'])
    status.write_text('## Offene Fragen\n',encoding='utf-8')
    self.assertEqual(projects.status()['projekte'][0]['fragen'],[])
if __name__=='__main__':unittest.main()

