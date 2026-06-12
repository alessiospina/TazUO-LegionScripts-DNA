# Autore:      Alessio Spina
# Descrizione: Attiva war mode e lancia il potere maestria "Disarmare"
#              (potere 1) sull'ultimo target.

import API

ARGV_POTERE = 1
API.SysMsg("[MDA] POTERE DISARMARE", 50)
API.SetWarMode(True)
API.Msg(f".castmaestro {ARGV_POTERE}")
if API.WaitForTarget():
    API.Target(API.LastTargetSerial)