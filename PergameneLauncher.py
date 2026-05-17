# Author:      Alessio Spina
# Date:        2026-05-11
# Description: Cerca nello zaino tutte le pergamene (graphic 0x0E36), seleziona
#              quella di livello piu' alto e la lancia sull'ultimo target.
#              Richiede doppio click (due avvii entro 3 secondi) per attivarsi.

import re
import time

DOUBLE_CLICK_WINDOW = 3.0  # secondi
SHARED_VAR = "PergameneLauncher_LastClick"


def is_double_click():
    now = time.time()
    raw = API.GetSharedVar(SHARED_VAR)
    last = float(raw) if raw else 0.0

    if last != 0.0 and (now - last) <= DOUBLE_CLICK_WINDOW:
        API.RemoveSharedVar(SHARED_VAR)
        return True

    API.SetSharedVar(SHARED_VAR, str(now))
    API.SysMsg(f"[{API.ScriptName}] Secondo click entro 3s per lanciare.")
    return False


class Pergamena:
    def __init__(self, nome, livello, seriale):
        self.nome = nome
        self.livello = livello
        self.seriale = seriale

    def __lt__(self, other):
        return self.livello < other.livello


class PergamenaLauncher:

    GRAPHIC = 0x0E36

    @staticmethod
    def parse_level(name):
        m = re.search(r'(\d+)\s+Liv', name)
        return int(m.group(1)) if m else None

    @staticmethod
    def build_list(items):
        pergamene = []
        for item in items:
            API.ClickObject(item)          
            lv = PergamenaLauncher.parse_level(item.Name)
            API.SysMsg(f"[{API.ScriptName}] name={item.Name} liv={lv}")
            if lv is not None:
                pergamene.append(Pergamena(item.Name, lv, item.Serial))
        return pergamene

    @staticmethod
    def launch(scelta):
        API.SysMsg(f"[{API.ScriptName}] Lancio: {scelta.nome} (Liv {scelta.livello})")
        API.SetWarMode(True)
        API.UseObject(scelta.seriale)
        if not API.WaitForTarget():
            API.SysMsg(f"[{API.ScriptName}] Target non arrivato.")
            return
        API.Target(API.LastTargetSerial)

    @staticmethod
    def run():
        items = API.FindTypeAll(PergamenaLauncher.GRAPHIC, API.Backpack)
        API.SysMsg(f"[{API.ScriptName}]{items}")
        if not items:
            API.SysMsg(f"[{API.ScriptName}] Nessuna pergamena trovata nello zaino.")
            return
        pergamene = PergamenaLauncher.build_list(items)
        if not pergamene:
            API.SysMsg(f"[{API.ScriptName}] Nessuna pergamena lanciabile trovata.")
            return
        pergamene.sort(reverse=True)
        PergamenaLauncher.launch(pergamene[0])


if is_double_click():
    PergamenaLauncher.run()
