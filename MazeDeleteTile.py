import API
import os
import json

DATA_FILE = os.path.join(os.path.dirname(API.ScriptPath), "maze_data.json")

def load_data():
    if not os.path.exists(DATA_FILE):
        API.SysMsg("maze_data.json non trovato.", 33)
        return None
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        API.SysMsg("Errore lettura maze_data.json.", 33)
        return None

def save_data(raw):
    with open(DATA_FILE, "w") as f:
        json.dump(raw, f)

def main():
    API.SysMsg("=== MazeDeleteTile ===", 88)
    API.SysMsg("Clicca un tile per rimuoverlo. Premi ESC o aspetta 60s per uscire.", 68)

    while True:
        tgt = API.RequestAnyTarget(60)
        if not tgt:
            API.SysMsg("Nessun target. Uscita.", 68)
            break

        tx, ty = int(tgt.X), int(tgt.Y)

        raw = load_data()
        if raw is None:
            break

        tiles = raw.get("tiles", [])
        before = len(tiles)
        tiles = [t for t in tiles if not (t[0] == tx and t[1] == ty)]
        after = len(tiles)

        if before == after:
            API.SysMsg("Tile (" + str(tx) + "," + str(ty) + ") non presente nel JSON.", 33)
        else:
            raw["tiles"] = tiles
            save_data(raw)
            API.RemoveMarkedTile(tx, ty)
            API.SysMsg("Rimosso (" + str(tx) + "," + str(ty) + "). Totale: " + str(after) + " tile.", 68)

        API.SysMsg("Clicca un altro tile oppure aspetta 60s per uscire.", 946)

main()
