# Autore:      Alessio Spina
# Descrizione: Permette di aggiungere, modificare o rimuovere manualmente tile
#              nel file maze_v2_data.json. Tramite un gump si sceglie la modalita'
#              (Verde, Rosso, Blu, Cancella) e si clicca il tile nel mondo.
#              Se si cancella un tile BLU o un suo landing, rimuove anche
#              la voce corrispondente dalla lista portali.

import API
import os
import json

DATA_FILE = os.path.join(os.path.dirname(API.ScriptPath), "maze_v2_data.json")

S_GREEN = 1
S_RED   = 2
S_BLUE  = 3

S_MARK  = {S_GREEN: 68, S_RED: 32, S_BLUE: 88}
S_LABEL = {S_GREEN: "VERDE", S_RED: "ROSSO", S_BLUE: "BLU", 0: "CANCELLA"}
S_COLOR = {S_GREEN: "#00CC00", S_RED: "#CC2222", S_BLUE: "#2288FF", 0: "#888888"}

MODE_DELETE = 0

def load_raw():
    if not os.path.exists(DATA_FILE):
        return {"tiles": [], "portals": []}
    try:
        with open(DATA_FILE, "r") as f:
            raw = json.load(f)
        if "portals" not in raw:
            raw["portals"] = []
        return raw
    except Exception:
        return {"tiles": [], "portals": []}

def save_raw(raw):
    with open(DATA_FILE, "w") as f:
        json.dump(raw, f)

def apply_tile(tx, ty, mode, raw):
    tiles   = raw.get("tiles", [])
    portals = raw.get("portals", [])

    # Rimuovi voce esistente per questo tile
    tiles = [t for t in tiles if not (t[0] == tx and t[1] == ty)]
    API.RemoveMarkedTile(tx, ty)

    if mode == MODE_DELETE:
        # Rimuovi anche portali che referenziano questo tile
        portals_before = len(portals)
        portals = [p for p in portals
                   if not (p[0] == tx and p[1] == ty)
                   and not (p[2] == tx and p[3] == ty)]
        portals_removed = portals_before - len(portals)
        msg = "Rimosso (" + str(tx) + "," + str(ty) + ")"
        if portals_removed > 0:
            msg += " + " + str(portals_removed) + " portali"
        hue = 33
    else:
        tiles.append([int(tx), int(ty), int(mode)])
        API.MarkTile(tx, ty, S_MARK[mode])
        msg = "Aggiunto " + S_LABEL[mode] + " (" + str(tx) + "," + str(ty) + ")"
        hue = S_MARK[mode]

    raw["tiles"]   = tiles
    raw["portals"] = portals
    save_raw(raw)
    API.SysMsg(msg + " | tot=" + str(len(tiles)), hue)
    return raw, msg

def main():
    mode    = [S_GREEN]
    do_sel  = [False]
    do_exit = [False]

    # ── Gump ──────────────────────────────────────────────────────
    GW, GH = 300, 170
    g = API.CreateModernGump(60, 60, GW, GH, False)

    bg = API.CreateGumpColorBox(0.93, "#111827")
    bg.SetRect(0, 0, GW, GH)
    g.Add(bg)

    lbl_mode = API.CreateGumpTTFLabel("Modalita': VERDE", 13, S_COLOR[S_GREEN])
    lbl_mode.SetRect(8, 4, GW - 16, 20)
    g.Add(lbl_mode)

    BTN_W, BTN_H = 62, 28
    modes_def = [
        (S_GREEN,     "Verde",    10),
        (S_RED,       "Rosso",    78),
        (S_BLUE,      "Blu",     146),
        (MODE_DELETE, "Cancella", 214),
    ]
    for m, label, bx in modes_def:
        btn = API.CreateSimpleButton(label, BTN_W, BTN_H)
        btn.SetRect(bx, 30, BTN_W, BTN_H)
        g.Add(btn)
        def make_mode_cb(mv):
            def cb():
                mode[0] = mv
                lbl_mode.SetText("Modalita': " + S_LABEL[mv])
            return cb
        API.AddControlOnClick(btn, make_mode_cb(m))

    btn_sel = API.CreateSimpleButton("Seleziona tile", 180, 30)
    btn_sel.SetRect(10, 68, 180, 30)
    g.Add(btn_sel)
    def on_sel(): do_sel[0] = True
    API.AddControlOnClick(btn_sel, on_sel)

    lbl_status = API.CreateGumpTTFLabel("Pronto.", 11, "#AAAAAA")
    lbl_status.SetRect(8, 106, GW - 16, 18)
    g.Add(lbl_status)

    btn_exit = API.CreateSimpleButton("Esci", 80, 26)
    btn_exit.SetRect(110, 132, 80, 26)
    g.Add(btn_exit)
    def on_exit(): do_exit[0] = True
    API.AddControlOnClick(btn_exit, on_exit)

    API.AddGump(g)
    API.SysMsg("MazeMarker (V2) avviato.", 88)

    raw = load_raw()
    API.SysMsg("Caricati " + str(len(raw["tiles"])) + " tile, " +
               str(len(raw["portals"])) + " portali.", 68)

    # ── Loop ──────────────────────────────────────────────────────
    while not do_exit[0]:
        API.ProcessCallbacks()
        API.Pause(0.05)

        if do_sel[0]:
            do_sel[0] = False
            lbl_status.SetText("Clicca un tile nel mondo (60s)...")
            tgt = API.RequestAnyTarget(60)
            if tgt:
                tx, ty = int(tgt.X), int(tgt.Y)
                raw, msg = apply_tile(tx, ty, mode[0], raw)
                lbl_status.SetText(msg)
            else:
                lbl_status.SetText("Nessun target selezionato.")

    g.Dispose()
    API.SysMsg("MazeMarker chiuso.", 68)

main()
