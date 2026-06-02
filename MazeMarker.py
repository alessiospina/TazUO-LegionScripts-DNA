import API
import os
import json

DATA_FILE = os.path.join(os.path.dirname(API.ScriptPath), "maze_data.json")

S_GREEN = 1
S_RED   = 2
S_BLUE  = 3

S_MARK  = {S_GREEN: 68, S_RED: 32, S_BLUE: 88}
S_LABEL = {S_GREEN: "VERDE", S_RED: "ROSSO", S_BLUE: "BLU", 0: "CANCELLA"}
S_COLOR = {S_GREEN: "#00CC00", S_RED: "#CC2222", S_BLUE: "#2288FF", 0: "#888888"}

MODE_DELETE = 0

def load_tiles():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f).get("tiles", [])
    except Exception:
        return []

def save_tiles(tiles):
    with open(DATA_FILE, "w") as f:
        json.dump({"tiles": tiles}, f)

def apply_tile(tx, ty, mode, tiles):
    # Rimuove voce esistente per questo tile (qualunque tipo fosse)
    tiles = [t for t in tiles if not (t[0] == tx and t[1] == ty)]
    API.RemoveMarkedTile(tx, ty)

    if mode == MODE_DELETE:
        msg = "Rimosso (" + str(tx) + "," + str(ty) + ")"
        hue = 33
    else:
        tiles.append([int(tx), int(ty), int(mode)])
        API.MarkTile(tx, ty, S_MARK[mode])
        msg = "Aggiunto " + S_LABEL[mode] + " (" + str(tx) + "," + str(ty) + ")"
        hue = S_MARK[mode]

    save_tiles(tiles)
    API.SysMsg(msg + " | tot=" + str(len(tiles)), hue)
    return tiles, msg

def main():
    mode    = [S_GREEN]   # modalita' corrente
    do_sel  = [False]     # richiesta selezione tile
    do_exit = [False]     # richiesta uscita

    # ── Gump ──────────────────────────────────────────────────────
    GW, GH = 300, 170
    g = API.CreateModernGump(60, 60, GW, GH, False)

    bg = API.CreateGumpColorBox(0.93, "#111827")
    bg.SetRect(0, 0, GW, GH)
    g.Add(bg)

    # Label modalita' corrente
    lbl_mode = API.CreateGumpTTFLabel("Modalita': VERDE", 13, S_COLOR[S_GREEN])
    lbl_mode.SetRect(8, 4, GW - 16, 20)
    g.Add(lbl_mode)

    # Bottoni modalita'
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

    # Bottone seleziona tile
    btn_sel = API.CreateSimpleButton("Seleziona tile", 180, 30)
    btn_sel.SetRect(10, 68, 180, 30)
    g.Add(btn_sel)
    def on_sel(): do_sel[0] = True
    API.AddControlOnClick(btn_sel, on_sel)

    # Label status
    lbl_status = API.CreateGumpTTFLabel("Pronto.", 11, "#AAAAAA")
    lbl_status.SetRect(8, 106, GW - 16, 18)
    g.Add(lbl_status)

    # Bottone esci
    btn_exit = API.CreateSimpleButton("Esci", 80, 26)
    btn_exit.SetRect(110, 132, 80, 26)
    g.Add(btn_exit)
    def on_exit(): do_exit[0] = True
    API.AddControlOnClick(btn_exit, on_exit)

    API.AddGump(g)
    API.SysMsg("MazeMarker avviato.", 88)

    tiles = load_tiles()
    API.SysMsg("Caricati " + str(len(tiles)) + " tile.", 68)

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
                tiles, msg = apply_tile(tx, ty, mode[0], tiles)
                lbl_status.SetText(msg)
            else:
                lbl_status.SetText("Nessun target selezionato.")

    g.Dispose()
    API.SysMsg("MazeMarker chiuso.", 68)

main()
