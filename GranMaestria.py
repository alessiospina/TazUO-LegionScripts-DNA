# Autore:      Alessio Spina
# Descrizione: Attiva war mode e lancia il potere maestria "Gran Maestria"
#              (potere 8) sull'ultimo target.

import API

ARGV_POTERE = 8
API.SysMsg("[MDA] POTERE GRAN MAESTRIA", 35)
API.SetWarMode(True)
API.Msg(f".castmaestro {ARGV_POTERE}")
if API.WaitForTarget():
    API.Target(API.LastTargetSerial)