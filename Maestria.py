# Autore:      Alessio Spina
# Descrizione: Attiva war mode e lancia il potere maestria "Maestria"
#              (potere 6) sull'ultimo target.

import API

ARGV_POTERE = 6
API.SysMsg("[MDA] POTERE MAESTRIA", 30)
API.SetWarMode(True)
API.Msg(f".castmaestro {ARGV_POTERE}")
if API.WaitForTarget():
    API.Target(API.LastTargetSerial)