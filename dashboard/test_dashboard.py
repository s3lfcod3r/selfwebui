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
  self.assertIn('OpenClaw (Verlauf) · cloud',result['agenten'])
if __name__=='__main__':unittest.main()
