# Autore:      Alessio Spina
# Descrizione: Attiva war mode e lancia il potere maestria "Colpo di Scudo"
#              (potere 10) sull'ultimo target.

import API

ARGV_POTERE = 10
API.SysMsg("[MDA] POTERE COLPO DI SCUDO", 40)
API.SetWarMode(True)
API.Msg(f".castmaestro {ARGV_POTERE}")
if API.WaitForTarget():
    API.Target(API.LastTargetSerial)