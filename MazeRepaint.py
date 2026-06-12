# Autore:      Alessio Spina
# Descrizione: Carica i dati del labirinto da maze_v2_data.json e ridisegna
#              la mappa su un gump grafico a celle colorate, aggiornando in
#              tempo reale la posizione del giocatore.

import API
import os
import json

DATA_FILE = os.path.join(os.path.dirname(API.ScriptPath), "maze_v2_data.json")

X_MIN, X_MAX = 5129, 5210
Y_MIN, Y_MAX = 2359, 2457
MAX_PX = 600

S_UNKNOWN, S_GREEN, S_RED, S_BLUE, S_WALL = 0, 1, 2, 3, 4
S_RGB  = [(40,40,40), (0,180,0), (220,0,0), (0,100,255), (10,10,10)]
S_MARK = [0, 68, 32, 88, 900]
RGB_PLAYER = (180, 0, 255)


def rgb_hex(r, g, b):
    h = "0123456789ABCDEF"
    return "#" + h[r>>4]+h[r&15] + h[g>>4]+h[g&15] + h[b>>4]+h[b&15]


def load_data():
    state = {}
    portals = {}
    if not os.path.exists(DATA_FILE):
        API.SysMsg("File non trovato: " + DATA_FILE, 32)
        return state, portals
    try:
        with open(DATA_FILE, "r") as f:
            raw = json.load(f)
        for item in raw.get("tiles", []):
            state[(item[0], item[1])] = item[2]
        for p in raw.get("portals", []):
            portals[(p[0], p[1])] = (p[2], p[3])
        API.SysMsg("Caricati " + str(len(state)) + " tile, " + str(len(portals)) + " portali.", 68)
    except Exception:
        API.SysMsg("Errore lettura dati.", 33)
    return state, portals


def save_data(state, portals):
    tiles = [[int(t[0]), int(t[1]), int(k)] for t, k in state.items()]
    portal_list = [[int(b[0]), int(b[1]), int(l[0]), int(l[1])]
                   for b, l in portals.items()]
    with open(DATA_FILE, "w") as f:
        json.dump({"tiles": tiles, "portals": portal_list}, f)


def build_portal_colors(portals):
    colors = {}
    for landing in set(portals.values()):
        colors[landing] = (
            API.Random.Next(80, 256),
            API.Random.Next(80, 256),
            API.Random.Next(80, 256),
        )
    return colors


def tile_color(tile, kind, portals, portal_colors):
    if kind == S_BLUE:
        landing = portals.get(tile)
        if landing is not None:
            return portal_colors.get(landing, S_RGB[S_BLUE])
    return S_RGB[kind]


def main():
    API.SysMsg("=== MAZE REPAINT ===", 88)

    state, portals = load_data()
    save_data(state, portals)
    portal_colors = build_portal_colors(portals)

    W = X_MAX - X_MIN + 1
    H = Y_MAX - Y_MIN + 1
    cell_sz = max(1, MAX_PX // max(W, H))
    sz = max(1, cell_sz - 1)
    gw = W * cell_sz + 4
    gh = H * cell_sz + 4

    gump = API.CreateModernGump(20, 20, gw, gh, False)
    bg = API.CreateGumpColorBox(1.0, "#111111")
    bg.SetRect(0, 0, gw, gh)
    gump.Add(bg)

    cells = [[None] * W for _ in range(H)]
    unk_color = rgb_hex(*S_RGB[S_UNKNOWN])
    row = 0
    while row < H:
        col = 0
        while col < W:
            box = API.CreateGumpColorBox(1.0, unk_color)
            box.SetRect(col * cell_sz + 2, row * cell_sz + 2, sz, sz)
            gump.Add(box)
            cells[row][col] = box
            col += 1
        row += 1

    for tile, kind in state.items():
        c = tile[0] - X_MIN
        r = tile[1] - Y_MIN
        if 0 <= r < H and 0 <= c < W:
            cr, cg, cb = tile_color(tile, kind, portals, portal_colors)
            cells[r][c].SetBaseColor(cr, cg, cb, 255)
        if kind != S_UNKNOWN:
            API.MarkTile(tile[0], tile[1], S_MARK[kind])

    API.AddGump(gump)

    prev_player = None
    while not gump.IsDisposed:
        px, py = int(API.Player.X), int(API.Player.Y)
        cur = (px, py)
        if cur != prev_player:
            if prev_player is not None:
                pc = prev_player[0] - X_MIN
                pr = prev_player[1] - Y_MIN
                if 0 <= pr < H and 0 <= pc < W:
                    kind = state.get(prev_player, S_UNKNOWN)
                    cr, cg, cb = tile_color(prev_player, kind, portals, portal_colors)
                    cells[pr][pc].SetBaseColor(cr, cg, cb, 255)
            pc2 = px - X_MIN
            pr2 = py - Y_MIN
            if 0 <= pr2 < H and 0 <= pc2 < W:
                cells[pr2][pc2].SetBaseColor(RGB_PLAYER[0], RGB_PLAYER[1], RGB_PLAYER[2], 255)
            prev_player = cur
        API.ProcessCallbacks()
        API.Pause(0.15)

    API.SysMsg("[MazeRepaint] Chiuso.", 88)


main()
