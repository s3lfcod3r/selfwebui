"""Classify failed tool results: cause, self-fixable or not, and a next step."""
import json

def diagnose(result):
    """Classify a failed tool result so the planner can decide: retry, narrow, or ask the user."""
    text=json.dumps(result,ensure_ascii=False).lower() if isinstance(result,dict) else ''
    code=result.get('exit_code') if isinstance(result,dict) else None
    rules=[
     ('text_mehrdeutig',('mal vor',),True,'Der zu ersetzende Text kommt mehrfach vor. Mehr umgebende Zeilen in "alt" aufnehmen oder alle=true setzen.'),
     ('text_nicht_gefunden',('alt nicht gefunden',),True,'Datei mit datei_lesen erneut lesen und den Text exakt (Leerzeichen, Einrückung) kopieren.'),
     ('zeitlimit',('abbruch nach','timeout'),True,'Befehl war zu breit oder zu langsam. Neuen, engeren Auftrag mit festem Pfad, kleiner Suchtiefe und "timeout 60" starten; nicht dieselbe Suche wiederholen.'),
     ('browser_nicht_verbunden',('arbeiter verbinden','browser antwortet nicht','nicht freigegeben'),False,'Sven muss den Arbeiter-Browser im Panel verbinden bzw. den Tab offen lassen. Bis dahin ohne Browser weiterarbeiten oder warten.'),
     ('git_identitaet',('author identity unknown','please tell me who you are'),True,'Git-Name/E-Mail nur im betroffenen Repo setzen (git config user.name/user.email ohne --global) und Commit wiederholen.'),
     ('zugangsdaten_fehlen',('could not read username','authentication failed','terminal prompts disabled'),False,'Es sind keine Zugangsdaten hinterlegt. Sven muss Push/Login selbst bereitstellen; nichts erraten.'),
     ('befehl_fehlt',('command not found',),True,'Werkzeug fehlt auf dem Host. Vorhandene Alternative nutzen (z. B. grep statt rg) oder Nutzer fragen, bevor etwas installiert wird.'),
     ('pfad_fehlt',('no such file','nicht gefunden'),True,'Pfad prüfen: übergeordneten Ordner mit ls auflisten, dann korrigierten Pfad verwenden.'),
     ('keine_berechtigung',('permission denied','operation not permitted'),False,'Rechte reichen nicht. Nicht umgehen; Sven fragen.'),
    ]
    for name,needles,selbst,tipp in rules:
        if any(n in text for n in needles):
            return {'ursache':name,'selbst_behebbar':selbst,'vorschlag':tipp}
    if code not in (None,0):
        return {'ursache':'exit_code_%s'%code,'selbst_behebbar':False,'vorschlag':'Ausgabe im Protokoll lesen, Ursache benennen und bei Unsicherheit Sven fragen.'}
    return {'ursache':'unbekannt','selbst_behebbar':False,'vorschlag':'Protokoll prüfen und Fehler ehrlich melden.'}
