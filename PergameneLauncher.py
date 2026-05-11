# Author:      Alessio Spina
# Date:        2026-05-11
# Description: Cerca nello zaino tutte le pergamene (graphic 0x0E36), seleziona
#              quella di livello piu' alto e la lancia sull'ultimo target.

import re


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
            lv = PergamenaLauncher.parse_level(item.Name)
            if lv is not None:
                pergamene.append(Pergamena(item.Name, lv, item.Serial))
        return pergamene

    @staticmethod
    def launch(scelta):
        API.SysMsg(f"[PergamenaLauncher] Lancio: {scelta.nome} (Liv {scelta.livello})")
        API.SetWarMode(True)
        API.UseObject(scelta.seriale)
        if not API.WaitForTarget():
            API.SysMsg("[PergamenaLauncher] Target non arrivato.")
            return
        API.Target(API.LastTargetSerial)

    @staticmethod
    def run():
        items = API.FindTypeAll(PergamenaLauncher.GRAPHIC, API.Backpack)
        if not items:
            API.SysMsg("[PergamenaLauncher] Nessuna pergamena trovata nello zaino.")
            return
        pergamene = PergamenaLauncher.build_list(items)
        if not pergamene:
            API.SysMsg("[PergamenaLauncher] Nessuna pergamena lanciabile trovata.")
            return
        pergamene.sort(reverse=True)
        PergamenaLauncher.launch(pergamene[0])


PergamenaLauncher.run()
