"""Loop brake for tool calls of small local models.

Small models tend to repeat the same failing call forever. This guard sits in
front of the real tool: identical consecutive calls are answered with a
synthetic hint instead of being forwarded again. Polling a running job is
legitimate and gets a far higher limit.
"""
import hashlib
import json

REPEAT_LIMIT = 3       # identical consecutive calls before the brake engages
POLL_LIMIT = 40        # identical job polls (each waits ~15 s) before a hint
ERROR_LIMIT = 8        # consecutive failed calls before a hard stop message


def fingerprint(args):
    return hashlib.sha256(json.dumps(args, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def is_poll(args):
    return isinstance(args, dict) and bool(args.get('job_id')) and not args.get('auftrag')


class LoopGuard:
    def __init__(self):
        self.last = None
        self.streak = 0
        self.last_result = None
        self.result_streak = 0
        self.errors = 0

    def before(self, args):
        """Return a hint text if this call must not be forwarded, else None."""
        fp = fingerprint(args)
        streak = self.streak + 1 if fp == self.last else 1
        if self.errors >= ERROR_LIMIT:
            return ('STOPP: %d Aufrufe in Folge sind fehlgeschlagen. Rufe das Werkzeug nicht erneut auf. '
                    'Beende deine Arbeit und melde dem Nutzer, welcher Fehler aufgetreten ist.' % self.errors)
        if streak >= REPEAT_LIMIT and not is_poll(args):
            return ('Schleife erkannt: Dieser Aufruf wurde %d-mal identisch ausgeführt und wird nicht erneut '
                    'gesendet. Die Antwort ändert sich nicht. Lies die letzte Antwort, ändere die Argumente '
                    '(Pflichtfeld "auftrag", gültiger Pfad, gültige job_id aus einer früheren Antwort) oder '
                    'melde dem Nutzer, dass du nicht weiterkommst.' % (streak - 1))
        return None

    def after(self, args, result_text, is_error):
        """Record the outcome; return an extra hint to append, if any."""
        fp = fingerprint(args)
        self.streak = self.streak + 1 if fp == self.last else 1
        self.last = fp
        rfp = hashlib.sha256(result_text.encode()).hexdigest()
        self.result_streak = self.result_streak + 1 if rfp == self.last_result else 1
        self.last_result = rfp
        self.errors = self.errors + 1 if is_error else 0
        if is_poll(args) and self.result_streak >= POLL_LIMIT:
            return ('Hinweis: Der Auftrag zeigt seit %d Abfragen keinen Fortschritt. Frage nicht weiter im '
                    'Sekundentakt ab; melde dem Nutzer den Stand und die job_id.' % self.result_streak)
        return None


EXAMPLE = ('Beispiel für einen gültigen Aufruf: {"auftrag": "Repo klonen und Ordner auflisten", '
           '"projekt": "SelfWG", "titel": "SelfWG klonen", "erlaubte_aufrufe": [{"werkzeug": "befehl_werkstatt", '
           '"argumente": {"befehl": "git clone https://github.com/s3lfcod3r/selfwg /media/Safe-Storage/appdata/werkstatt/x/selfwg"}}]}')


def normalize(args):
    """Fill the mandatory 'auftrag' from titel/kontext when a small model forgot it."""
    if not isinstance(args, dict) or args.get('aktion') or args.get('job_id') or args.get('auftrag'):
        return args
    fallback = args.get('titel') or args.get('kontext')
    if isinstance(fallback, str) and fallback.strip():
        return {**args, 'auftrag': fallback.strip()}
    return args
