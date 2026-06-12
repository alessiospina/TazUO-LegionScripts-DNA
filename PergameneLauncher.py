# Autore:      Alessio Spina
# Descrizione: Al primo click cerca la pergamena di livello piu' alto nello zaino
#              e mostra una preview. Al secondo click entro 3s la lancia direttamente
#              sull'ultimo target senza cercare di nuovo.

import re
import time

DOUBLE_CLICK_WINDOW = 3.0
SHARED_TIME   = "PergameneLauncher_LastClick"
SHARED_SCROLL = "PergameneLauncher_Scroll"   # formato: "serial|nome|livello"


class Pergamena:
    def __init__(self, nome, livello, seriale):
        self.nome    = nome
        self.livello = livello
        self.seriale = seriale

    def __lt__(self, other):
        return self.livello < other.livello


def get_cached():
    raw = API.GetSharedVar(SHARED_SCROLL)
    if not raw:
        return None
    parts = raw.split("|", 2)
    if len(parts) != 3:
        return None
    try:
        return Pergamena(parts[1], int(parts[2]), int(parts[0]))
    except Exception:
        return None


def save_cached(p):
    API.SetSharedVar(SHARED_SCROLL, str(p.seriale) + "|" + p.nome + "|" + str(p.livello))


def clear_cached():
    API.RemoveSharedVar(SHARED_TIME)
    API.RemoveSharedVar(SHARED_SCROLL)


def find_best():
    items = API.FindTypeAll(0x0E36, API.Backpack)
    if not items:
        API.SysMsg("[" + API.ScriptName + "] Nessuna pergamena nello zaino.")
        return None
    pergamene = []
    for item in items:
        API.ClickObject(item)
        m = re.search(r'(\d+)\s+Liv', item.Name)
        if m:
            pergamene.append(Pergamena(item.Name, int(m.group(1)), item.Serial))
    if not pergamene:
        API.SysMsg("[" + API.ScriptName + "] Nessuna pergamena lanciabile trovata.")
        return None
    pergamene.sort(reverse=True)
    return pergamene[0]


def launch(scelta):
    API.SysMsg("[" + API.ScriptName + "] Lancio: " + scelta.nome + " (Liv " + str(scelta.livello) + ")")
    API.SetWarMode(True)
    API.UseObject(scelta.seriale)
    if not API.WaitForTarget():
        API.SysMsg("[" + API.ScriptName + "] Target non arrivato.")
        return
    API.Target(API.LastTargetSerial)


# --- Main ---
now      = time.time()
raw_time = API.GetSharedVar(SHARED_TIME)
last     = float(raw_time) if raw_time else 0.0
cached   = get_cached()

if last != 0.0 and (now - last) <= DOUBLE_CLICK_WINDOW and cached is not None:
    # Secondo click: spara la pergamena gia' trovata
    clear_cached()
    launch(cached)
else:
    # Primo click: cerca, salva e mostra preview
    best = find_best()
    if best is None:
        clear_cached()
    else:
        save_cached(best)
        API.SetSharedVar(SHARED_TIME, str(now))
        API.SysMsg(
            "[" + API.ScriptName + "] Preview: " + best.nome +
            " (Liv " + str(best.livello) + ")"
            " — secondo click entro " + str(int(DOUBLE_CLICK_WINDOW)) + "s per lanciare."
        )
