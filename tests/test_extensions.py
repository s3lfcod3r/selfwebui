import sys
import unittest
sys.path.insert(0,'/opt/selfwebui/extensions')
from worker_panel import summary

class TelemetryTests(unittest.TestCase):
    def test_allowlist_and_invalid_metrics(self):
        result=summary({'phase':'generating','updated':100,'tps':float('nan'),
            'tokens':12,'prompt':'private','api_key':'private','tool':'secret path'},105)
        self.assertEqual(result,{'phase':'generating','updated':100,'tokens':12,'stale':False})

    def test_stale_measurements(self):
        self.assertTrue(summary({'phase':'generating','updated':10},30)['stale'])
        self.assertFalse(summary({'phase':'fertig','updated':10},30)['stale'])


import fehlerchats

class LeereAntwortTests(unittest.TestCase):
    def test_only_completed_reasoning_without_text_counts(self):
        denken='[{"type":"reasoning","status":"completed","content":[]}]'
        self.assertTrue(fehlerchats.leere_antwort('',denken))
        self.assertTrue(fehlerchats.leere_antwort('  ',[{'type':'reasoning','status':'completed'}]))
        self.assertFalse(fehlerchats.leere_antwort('Hallo',denken))                                 # hat geantwortet
        self.assertFalse(fehlerchats.leere_antwort('','[{"type":"reasoning","status":"in_progress"}]'))  # abgebrochen
        self.assertFalse(fehlerchats.leere_antwort('','[{"type":"reasoning","status":"completed"},{"type":"function_call"}]'))
        self.assertFalse(fehlerchats.leere_antwort('',''))
        self.assertFalse(fehlerchats.leere_antwort('','kaputt'))
        self.assertFalse(fehlerchats.leere_antwort('','[]'))


class FehlerchatTests(unittest.TestCase):
    def test_error_text_and_user_abort(self):
        self.assertEqual(fehlerchats.fehler_text({'error':' Boom '}),'Boom')
        self.assertEqual(fehlerchats.fehler_text(None),'')
        self.assertEqual(fehlerchats.fehler_text({'files':[]}),'')
        self.assertTrue(fehlerchats.ignorierbar('Cancelled by user request'))
        self.assertFalse(fehlerchats.ignorierbar('Jinja Exception: No user query found'))

    def test_open_error_must_be_current_finished_assistant_message(self):
        ok=fehlerchats.ist_fehlerfall('assistant',True,{'error':'Boom'},'m1','m1')
        self.assertEqual(ok,'Boom')
        self.assertEqual(fehlerchats.ist_fehlerfall('assistant',True,{'error':'Boom'},'m1','m2'),'')   # spaeter ging es weiter
        self.assertEqual(fehlerchats.ist_fehlerfall('assistant',False,{'error':'Boom'},'m1','m1'),'')  # laeuft noch
        self.assertEqual(fehlerchats.ist_fehlerfall('user',True,{'error':'Boom'},'m1','m1'),'')
        self.assertEqual(fehlerchats.ist_fehlerfall('assistant',True,{'error':'aborted by user'},'m1','m1'),'')
        self.assertEqual(fehlerchats.ist_fehlerfall('assistant',True,{},'m1','m1'),'')


import io,urllib.error
import worker_panel as panel

class BonsaiZustandTests(unittest.TestCase):
    def check(self,opener):
        panel._bonsai_cache.update(zeit=0.0,zustand='unbekannt')
        with patch('urllib.request.urlopen',opener):return panel.bonsai_zustand(now=1000.0)
    def test_ready_loading_off(self):
        ok=lambda url,timeout=0:io.BytesIO(b'{"status":"ok"}')
        loading=Mock(side_effect=urllib.error.HTTPError('u',503,'loading',{},io.BytesIO(b'{}')))
        off=Mock(side_effect=OSError('refused'))
        self.assertEqual(self.check(ok),'bereit')
        self.assertEqual(self.check(loading),'laedt')
        self.assertEqual(self.check(off),'aus')
    def test_result_is_cached_for_five_seconds(self):
        panel._bonsai_cache.update(zeit=1000.0,zustand='bereit')
        boom=Mock(side_effect=AssertionError('darf nicht abgefragt werden'))
        with patch('urllib.request.urlopen',boom):self.assertEqual(panel.bonsai_zustand(now=1003.0),'bereit')
        boom2=Mock(side_effect=OSError('refused'))
        with patch('urllib.request.urlopen',boom2):self.assertEqual(panel.bonsai_zustand(now=1006.0),'aus')


class BonsaiAktivitaetTests(unittest.TestCase):
    def check(self,body):
        panel._aktiv_cache.update(zeit=0.0,wert=None)
        with patch('urllib.request.urlopen',lambda url,timeout=0:io.BytesIO(body)):return panel.bonsai_aktivitaet(now=1000.0)
    def test_reading_writing_and_idle(self):
        lesen=b'[{"is_processing":true,"n_prompt_tokens":130000,"n_prompt_tokens_processed":1200,"next_token":[{"n_decoded":0}]}]'
        schreiben=b'[{"is_processing":true,"n_prompt_tokens":10,"n_prompt_tokens_processed":10,"next_token":[{"n_decoded":42}]}]'
        self.assertEqual(self.check(lesen),{'phase':'liest','gelesen':1200,'gesamt':130000,'geschrieben':0})
        self.assertEqual(self.check(schreiben)['phase'],'schreibt')
        self.assertIsNone(self.check(b'[{"is_processing":false}]'))
        self.assertIsNone(self.check(b'kaputt'))


import asyncio,json
from unittest.mock import patch,Mock
from fastapi import HTTPException
import direct_browser as relay

class Request:
    headers={'authorization':'Bearer test-key'}
    def __init__(self,**data):self.data=data
    async def json(self):return self.data
    async def body(self):return json.dumps(self.data).encode()

class RelayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        relay.lease=None;relay.pending.clear();relay.lock=asyncio.Lock()
        self.auth=patch.object(relay,'admin',return_value='admin');self.auth.start()
        self.key=patch.object(relay.Path,'read_text',return_value='test-key');self.key.start()
    async def asyncTearDown(self):self.auth.stop();self.key.stop()
    async def test_roundtrip_and_controller_ownership(self):
        token=(await relay.connect(Request()))['token']
        with self.assertRaises(HTTPException):await relay.poll(Request(token='wrong'))
        task=asyncio.create_task(relay.command(Request(action='read')))
        await asyncio.sleep(0)
        cmd=await relay.poll(Request(token=token))
        self.assertEqual(cmd['action'],'read')
        self.assertEqual(await relay.poll(Request(token=token)),{})
        await relay.result(Request(token=token,id=cmd['id'],result={'text':'visible'}))
        self.assertEqual(json.loads((await task).body),{'text':'visible'})
        self.assertFalse(relay.pending)
    async def test_readonly_and_disconnected(self):
        self.assertIn('fehler',await relay.command(Request(action='click',interactive=False)))
        self.assertIn('fehler',await relay.command(Request(action='read')))
        self.assertIn('fehler',await relay.command(Request(action='screenshot')))
    async def test_auth_and_disconnect(self):
        wrong=Request(action='read');wrong.headers={'authorization':'Bearer wrong'}
        with self.assertRaises(HTTPException):await relay.command(wrong)
        token=(await relay.connect(Request()))['token']
        with self.assertRaises(HTTPException):await relay.connect(Request())
        task=asyncio.create_task(relay.command(Request(action='read')))
        await asyncio.sleep(0)
        await relay.disconnect(Request(token=token))
        self.assertIn('fehler',json.loads((await task).body))
        self.assertIsNone(relay.lease)

if __name__=='__main__':unittest.main()

