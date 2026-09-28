import unittest,runpy,io,sys,json
from pathlib import Path
from unittest.mock import patch
with patch.object(Path,'read_text',return_value='test-key'),patch.object(sys,'stdin',io.StringIO('')):
 module=runpy.run_path('/opt/selfwebui/integrations/bonsai_mcp.py')
call=module['call']
class PlanTests(unittest.TestCase):
 def test_sequential_contexts(self):
  calls=[]
  def worker(args,meta):
   calls.append((args,meta));return {'content':[{'type':'text','text':'verified result'}],'isError':False}
  with patch.dict(call.__globals__,single=worker):
   result=call({'auftrag':'Review','projekt':'Test','teilauftraege':[{'titel':'One','auftrag':'First'},{'titel':'Two','auftrag':'Second'}]})
  self.assertFalse(result['isError']);self.assertEqual([c[1]['schritt'] for c in calls],[1,2])
  self.assertIn('verified result',calls[1][0]['kontext'])
  self.assertEqual(calls[0][1]['plan'],calls[1][1]['plan'])
 def test_error_stops_plan(self):
  calls=[]
  def worker(args,meta):calls.append(meta);return {'content':[],'isError':True}
  with patch.dict(call.__globals__,single=worker):
   result=call({'auftrag':'Review','teilauftraege':[{'titel':'One','auftrag':'First'},{'titel':'Two','auftrag':'Second'}]})
  self.assertTrue(result['isError']);self.assertEqual(len(calls),1)
 def test_validate_entire_plan_before_execution(self):
  with self.assertRaises(ValueError):call({'auftrag':'Review','teilauftraege':[{'titel':'Missing task'}]})
if __name__=='__main__':unittest.main()
