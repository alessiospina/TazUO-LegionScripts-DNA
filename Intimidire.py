# Autore:      Alessio Spina
# Descrizione: Attiva war mode e lancia il potere maestria "Intimidire"
#              (potere 4) sull'ultimo target.

import API

ARGV_POTERE = 4
API.SysMsg("[MDA] POTERE INTIMIDIRE", 60)
API.SetWarMode(True)
API.Msg(f".castmaestro {ARGV_POTERE}")
if API.WaitForTarget():
    API.Target(API.LastTargetSerial)