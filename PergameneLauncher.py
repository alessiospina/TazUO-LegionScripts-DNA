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


class PergamenaLauncher:

    GRAPHIC = 0x0E36

    @staticmethod
    def parse_level(name):
        m = re.search(r'(\d+)\s+Liv', name)
        return int(m.group(1)) if m else 0

    @staticmethod
    def build_list(items):
        pergamene = []
        for item in items:
            pergamene.append(Pergamena(item.Name, PergamenaLauncher.parse_level(item.Name), item.Serial))
        return pergamene

    @staticmethod
    def sort_by_level(pergamene):
        i = 1
        while i < len(pergamene):
            current = pergamene[i]
            j = i - 1
            while j >= 0 and pergamene[j].livello < current.livello:
                pergamene[j + 1] = pergamene[j]
                j -= 1
            pergamene[j + 1] = current
            i += 1

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
        PergamenaLauncher.sort_by_level(pergamene)
        PergamenaLauncher.launch(pergamene[0])


PergamenaLauncher.run()
