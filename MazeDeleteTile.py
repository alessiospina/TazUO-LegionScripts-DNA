# Autore:      Alessio Spina
# Descrizione: Rimuove tile dal file maze_v2_data.json cliccandoli nel mondo.
#              Se il tile eliminato e' un portale BLU o un suo landing,
#              rimuove anche la voce corrispondente dalla lista portali.

import API
import os
import json

DATA_FILE = os.path.join(os.path.dirname(API.ScriptPath), "maze_v2_data.json")

def load_data():
    if not os.path.exists(DATA_FILE):
        API.SysMsg("maze_v2_data.json non trovato.", 33)
        return None
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        API.SysMsg("Errore lettura maze_v2_data.json.", 33)
        return None

def save_data(raw):
    with open(DATA_FILE, "w") as f:
        json.dump(raw, f)

def main():
    API.SysMsg("=== MazeDeleteTile (V2) ===", 88)
    API.SysMsg("Clicca un tile per rimuoverlo. Aspetta 60s per uscire.", 68)

    while True:
        tgt = API.RequestAnyTarget(60)
        if not tgt:
            API.SysMsg("Nessun target. Uscita.", 68)
            break

        tx, ty = int(tgt.X), int(tgt.Y)

        raw = load_data()
        if raw is None:
            break

        # Rimuovi dalla lista tiles
        tiles = raw.get("tiles", [])
        before = len(tiles)
        tiles = [t for t in tiles if not (t[0] == tx and t[1] == ty)]
        after = len(tiles)

        if before == after:
            API.SysMsg("Tile (" + str(tx) + "," + str(ty) + ") non presente.", 33)
            API.SysMsg("Clicca un altro tile oppure aspetta 60s per uscire.", 946)
            continue

        # Rimuovi portali che referenziano questo tile (come BLU o come landing)
        portals = raw.get("portals", [])
        portals_before = len(portals)
        portals = [p for p in portals
                   if not (p[0] == tx and p[1] == ty)   # era il tile BLU
                   and not (p[2] == tx and p[3] == ty)]  # era il landing
        portals_removed = portals_before - len(portals)

        raw["tiles"] = tiles
        raw["portals"] = portals
        save_data(raw)
        API.RemoveMarkedTile(tx, ty)

        msg = "Rimosso (" + str(tx) + "," + str(ty) + "). Tile rimasti: " + str(after)
        if portals_removed > 0:
            msg += " | Portali rimossi: " + str(portals_removed)
        API.SysMsg(msg, 68)

        API.SysMsg("Clicca un altro tile oppure aspetta 60s per uscire.", 946)

main()
