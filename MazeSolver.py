import API
import os
import json

DATA_FILE     = os.path.join(os.path.dirname(API.ScriptPath), "maze_data.json")
ROUTE_FILE    = os.path.join(os.path.dirname(API.ScriptPath), "maze_route.txt")
LANDINGS_FILE = os.path.join(os.path.dirname(API.ScriptPath), "maze_blue_landings.json")

START = (5154, 2369)
GOAL  = (5204, 2367)

KNOWN_BAD = [(5154, 2367), (5154, 2366)]

# ── Area di scansione (angoli reali del labirinto) ────────────
X_MIN = 5129
X_MAX = 5210
Y_MIN = 2359
Y_MAX = 2457

TILE_W = X_MAX - X_MIN + 1
TILE_H = Y_MAX - Y_MIN + 1

MAX_PX = 600
CELL = max(1, MAX_PX // max(TILE_W, TILE_H))

DIRS = [
    ( 1,  0, "east"),
    (-1,  0, "west"),
    ( 0, -1, "north"),
    ( 0,  1, "south"),
    ( 1, -1, "northeast"),
    ( 1,  1, "southeast"),
    (-1, -1, "northwest"),
    (-1,  1, "southwest"),
]

S_UNKNOWN = 0
S_GREEN   = 1
S_RED     = 2
S_BLUE    = 3
S_WALL    = 4

S_LABEL = ["?", "VERDE", "ROSSO", "BLU", "MURO"]
S_HUE   = [946, 68, 32, 88, 900]
S_MARK  = [0, 68, 32, 88, 900]
S_RGB   = [(40,40,40), (0,180,0), (220,0,0), (0,100,255), (10,10,10)]
RGB_PLAYER = (255, 220, 0)
RGB_TARGET = (255, 165,  0)   # arancione: tile in corso di classificazione
HUE_TARGET = 53
RGB_QUEUED = (180, 160,  0)   # giallo scuro: tile in coda da visitare

DISP = {}   # display config, popolato in main() dopo la scansione statica

# ── Persistenza ───────────────────────────────────────────────

def load_data():
    state = {}
    for t in KNOWN_BAD:
        state[t] = S_RED
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                raw = json.load(f)
            for item in raw.get("tiles", []):
                state[(item[0], item[1])] = item[2]
            API.SysMsg("Caricati " + str(len(state)) + " tile.", 68)
        except Exception:
            API.SysMsg("Errore lettura dati, riparto da zero.", 33)
    return state

def save_data(state):
    tiles = [[int(x), int(y), int(s)] for (x, y), s in state.items()]
    with open(DATA_FILE, "w") as f:
        json.dump({"tiles": tiles}, f)

def load_landings():
    if not os.path.exists(LANDINGS_FILE):
        return []
    try:
        with open(LANDINGS_FILE, "r") as f:
            return json.load(f).get("landings", [])
    except Exception:
        return []

def save_landings(landings):
    with open(LANDINGS_FILE, "w") as f:
        json.dump({"landings": landings}, f)

def compute_display_cfg(state, margin=15):
    tiles = list(state.keys())
    if tiles:
        xs = [t[0] for t in tiles]
        ys = [t[1] for t in tiles]
        x_min = max(X_MIN, min(xs) - margin)
        x_max = min(X_MAX, max(xs) + margin)
        y_min = max(Y_MIN, min(ys) - margin)
        y_max = min(Y_MAX, max(ys) + margin)
    else:
        x_min = START[0] - margin
        x_max = START[0] + margin
        y_min = START[1] - margin
        y_max = START[1] + margin
    w = x_max - x_min + 1
    h = y_max - y_min + 1
    cell = max(1, MAX_PX // max(w, h))
    return {"x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max,
            "w": w, "h": h, "cell": cell}

# ── Priorità BFS: distanza dal player al vicino verde più vicino ──

def reachable_greens(px, py, state):
    """Insieme dei tile S_GREEN raggiungibili da (px, py) via catena di verdi adiacenti.
    Permette di sapere in anticipo quali zone della mappa sono accessibili dalla
    posizione attuale senza dover lanciare A* su ogni candidato."""
    visited = set()
    stack = []
    if state.get((px, py), S_UNKNOWN) == S_GREEN:
        stack.append((px, py))
        visited.add((px, py))
    else:
        for ddx, ddy, _ in DIRS:
            nb = (px+ddx, py+ddy)
            if state.get(nb, S_UNKNOWN) == S_GREEN:
                stack.append(nb)
                visited.add(nb)
    while stack:
        cx, cy = stack.pop()
        for ddx, ddy, _ in DIRS:
            nb = (cx+ddx, cy+ddy)
            if state.get(nb, S_UNKNOWN) == S_GREEN and nb not in visited:
                visited.add(nb)
                stack.append(nb)
    return visited

def tile_priority(t, state, px, py, reachable=None):
    x, y = t
    best = 999999
    for ddx, ddy, _ in DIRS:
        nb = (x+ddx, y+ddy)
        if state.get(nb, S_UNKNOWN) == S_GREEN:
            if reachable is not None and nb not in reachable:
                continue
            d = abs(nb[0]-px) + abs(nb[1]-py)
            if d < best:
                best = d
    return best

# ── Gump (acceptMouseInput=False) ─────────────────────────────

def rgb_hex(r, g, b):
    h = "0123456789ABCDEF"
    return "#" + h[r>>4]+h[r&15] + h[g>>4]+h[g&15] + h[b>>4]+h[b&15]

def create_gump(cells):
    dw   = DISP["w"];    dh   = DISP["h"];    dc = DISP["cell"]
    gw = dw * dc + 4
    gh = dh * dc + 4
    gump = API.CreateModernGump(20, 20, gw, gh, False)
    bg = API.CreateGumpColorBox(1.0, "#111111")
    bg.SetRect(0, 0, gw, gh)
    gump.Add(bg)
    unk = rgb_hex(*S_RGB[S_UNKNOWN])
    cell_sz = max(1, dc - 1)
    for row in range(dh):
        for col in range(dw):
            c = API.CreateGumpColorBox(1.0, unk)
            c.SetRect(col * dc + 2, row * dc + 2, cell_sz, cell_sz)
            gump.Add(c)
            cells[row][col] = c
    API.AddGump(gump)

def paint(cells, x, y, state_val, is_player=False):
    col = x - DISP["x_min"]
    row = y - DISP["y_min"]
    if 0 <= row < DISP["h"] and 0 <= col < DISP["w"] and cells[row][col] is not None:
        r, g, b = RGB_PLAYER if is_player else S_RGB[state_val]
        cells[row][col].SetBaseColor(r, g, b, 255)
    if not is_player and state_val != S_UNKNOWN:
        API.MarkTile(x, y, S_MARK[state_val])

def paint_highlight(cells, x, y):
    col = x - DISP["x_min"]
    row = y - DISP["y_min"]
    if 0 <= row < DISP["h"] and 0 <= col < DISP["w"] and cells[row][col] is not None:
        cells[row][col].SetBaseColor(RGB_TARGET[0], RGB_TARGET[1], RGB_TARGET[2], 255)
    API.MarkTile(x, y, HUE_TARGET)

def paint_queued(cells, x, y):
    col = x - DISP["x_min"]
    row = y - DISP["y_min"]
    if 0 <= row < DISP["h"] and 0 <= col < DISP["w"] and cells[row][col] is not None:
        cells[row][col].SetBaseColor(RGB_QUEUED[0], RGB_QUEUED[1], RGB_QUEUED[2], 255)

# ── A* su tile verdi ──────────────────────────────────────────

def astar_green(start, goal, state):
    gx, gy = goal
    h = lambda p: abs(p[0]-gx) + abs(p[1]-gy)
    open_list = [(h(start), start)]
    came = {}
    gscore = {start: 0}
    closed = set()
    while open_list:
        open_list.sort(key=lambda t: t[0])
        _, cur = open_list.pop(0)
        if cur in closed:
            continue
        closed.add(cur)
        if cur == goal:
            path = []
            while cur in came:
                path.append(cur)
                cur = came[cur]
            path.append(start)
            return path[::-1]
        cx, cy = cur
        for dx, dy, _ in DIRS:
            nb = (cx+dx, cy+dy)
            if nb in closed:
                continue
            if state.get(nb, S_UNKNOWN) != S_GREEN and nb != goal:
                continue
            ng = gscore[cur] + 1
            if nb not in gscore or ng < gscore[nb]:
                came[nb] = cur
                gscore[nb] = ng
                open_list.append((ng + h(nb), nb))
    return None

def navigate_green(target, state, misclass=None):
    px, py = int(API.Player.X), int(API.Player.Y)
    if (px, py) == target:
        return True
    path = astar_green((px, py), target, state)
    if not path or len(path) < 2:
        return False
    for sx, sy in path[1:]:
        if (int(API.Player.X), int(API.Player.Y)) == (sx, sy):
            continue
        dx, dy = sx - int(API.Player.X), sy - int(API.Player.Y)
        dname = next((d for ddx,ddy,d in DIRS if ddx==dx and ddy==dy), None)
        if dname is None:
            return False
        API.Turn(dname)
        API.Pause(0.15)
        API.Run(dname)
        # Polling: aspetta che il player raggiunga il passo (max 2s)
        for _ in range(10):
            API.Pause(0.2)
            if (int(API.Player.X), int(API.Player.Y)) == (sx, sy):
                break
        actual = (int(API.Player.X), int(API.Player.Y))
        if actual != (sx, sy):
            # Distingue teleport reale da semplice lag/movimento mancato:
            # un portale BLU sposta di molte tile; un fallimento lascia il player vicino.
            cheby = max(abs(actual[0] - sx), abs(actual[1] - sy))
            if cheby > 3 and misclass is not None:
                misclass["tile"]   = (sx, sy)
                misclass["landed"] = actual
            return False
    return True

# ── Classificazione tile ──────────────────────────────────────

def classify(tx, ty):
    cx, cy = int(API.Player.X), int(API.Player.Y)
    dx, dy = tx - cx, ty - cy
    dname = next((d for ddx,ddy,d in DIRS if ddx==dx and ddy==dy), None)
    if dname is None:
        return S_WALL
    API.Turn(dname)
    API.Pause(0.3)
    API.Walk(dname)
    # Polling: esce appena il player si muove (tollerante ai save di gioco, max 5s)
    for _ in range(50):
        API.Pause(0.2)
        px, py = int(API.Player.X), int(API.Player.Y)
        if px != cx or py != cy:
            break
    if px == cx and py == cy:
        return S_WALL
    # Pausa di stabilizzazione: evita di leggere coordinate intermedie
    # trasmesse dal server durante l'animazione di movimento.
    API.Pause(0.35)
    px, py = int(API.Player.X), int(API.Player.Y)
    if px == tx and py == ty:
        return S_GREEN
    if (px, py) == START:
        return S_RED   # riporta al punto di partenza
    return S_BLUE      # porta altrove

# ── Helper ────────────────────────────────────────────────────

def can_reach_any_queued(state, queue, px, py, reachable=None):
    """True se almeno uno dei tile in coda ha un vicino verde nella componente
    connessa di verdi raggiungibile da (px,py). Controlla tutta la coda (non
    solo i top-10 per Manhattan) usando il pre-computato reachable_greens."""
    if reachable is None:
        reachable = reachable_greens(px, py, state)
    if not reachable:
        return False
    for t in queue:
        x, y = t
        for ddx, ddy, _ in DIRS:
            if (x+ddx, y+ddy) in reachable:
                return True
    return False

def expand_queue(pos, state, queue, skipped=None, cells=None):
    x, y = pos
    for ddx, ddy, _ in DIRS:
        nb = (x+ddx, y+ddy)
        if X_MIN<=nb[0]<=X_MAX and Y_MIN<=nb[1]<=Y_MAX and nb not in state and nb not in queue:
            queue.add(nb)
            if cells is not None:
                paint_queued(cells, nb[0], nb[1])

# ── Queue debug gump ──────────────────────────────────────────

QUEUE_ROWS = 15

def create_queue_gump():
    gw = 230
    gh = QUEUE_ROWS * 20 + 48
    g = API.CreateModernGump(650, 20, gw, gh, False)
    bg = API.CreateGumpColorBox(0.9, "#0d1117")
    bg.SetRect(0, 0, gw, gh)
    g.Add(bg)
    hdr = API.CreateGumpTTFLabel("Coda: 0 tile", 12, "#FFFFFF")
    hdr.SetRect(5, 5, gw - 10, 18)
    g.Add(hdr)
    rows = []
    for i in range(QUEUE_ROWS):
        lbl = API.CreateGumpTTFLabel("---", 11, "#88CCFF")
        lbl.SetRect(5, 28 + i * 20, gw - 10, 16)
        g.Add(lbl)
        rows.append(lbl)
    API.AddGump(g)
    return hdr, rows

def update_queue_gump(hdr, rows, queue, state, px, py, nav_fails):
    sorted_q = sorted(queue, key=lambda t: tile_priority(t, state, px, py))
    hdr.SetText("Coda: " + str(len(sorted_q)) + " tile")
    for i in range(QUEUE_ROWS):
        if i < len(sorted_q):
            x, y = sorted_q[i]
            prio = tile_priority((x, y), state, px, py)
            indicator = " [V]" if prio < 999999 else " [X]"
            fails = nav_fails.get((x, y), 0)
            fail_str = "" if fails == 0 else " f" + str(fails)
            rows[i].SetText("(" + str(x) + "," + str(y) + ")" + indicator + fail_str)
        else:
            rows[i].SetText("---")

def re_enter_via_portal(target_landing, state, portal_map):
    """
    Cerca un portale BLU noto, ci entra fisicamente e ritorna True se il
    player atterra in un landing valido. Se target_landing è il landing di
    un portale registrato, lo prova per primo (utile in modalità manuale).
    """
    items = list(portal_map.items())
    if target_landing in portal_map:
        items.sort(key=lambda kv: 0 if kv[0] == target_landing else 1)
    for landing_pos, blue_tile_pos in items:
        btx, bty = blue_tile_pos
        # Trova tile verde adiacente al tile BLU raggiungibile dalla posizione corrente
        approach = None
        for ddx, ddy, _ in DIRS:
            adj = (btx+ddx, bty+ddy)
            if state.get(adj, S_UNKNOWN) == S_GREEN:
                approach = adj
                break
        if approach is None:
            continue
        if not navigate_green(approach, state):
            continue
        dx, dy = btx - int(API.Player.X), bty - int(API.Player.Y)
        dname = next((dn for adx,ady,dn in DIRS if adx==dx and ady==dy), None)
        if dname is None:
            continue
        API.Turn(dname); API.Pause(0.1)
        API.Run(dname); API.Pause(0.3)
        actual = (int(API.Player.X), int(API.Player.Y))
        if actual != landing_pos:
            continue  # portale cambiato, prova il prossimo
        return True   # siamo al landing, il chiamante aggiorna last_green
    return False

# ── Scelta modalità ───────────────────────────────────────────

def ask_mode():
    GW, GH = 450, 110
    g = API.CreateGump(True, True, True)
    g.SetRect(380, 280, GW, GH)
    bg = API.CreateGumpColorBox(0.92, "#16213e")
    bg.SetRect(0, 0, GW, GH)
    g.Add(bg)
    lbl = API.CreateGumpTTFLabel("Modalita' di esplorazione:", 14, "#FFFFFF")
    lbl.SetRect(10, 8, GW - 20, 22)
    g.Add(lbl)

    BTN_W = 140
    btn_auto   = API.CreateSimpleButton("Autonomo (BFS)", BTN_W, 34)
    btn_manual = API.CreateSimpleButton("Scelgo portale", BTN_W, 34)
    btn_vblu   = API.CreateSimpleButton("Verifica BLU",   BTN_W, 34)
    btn_auto.SetRect(10,  44, BTN_W, 34)
    btn_manual.SetRect(155, 44, BTN_W, 34)
    btn_vblu.SetRect(300, 44, BTN_W, 34)
    g.Add(btn_auto); g.Add(btn_manual); g.Add(btn_vblu)

    choice = [None]
    def on_auto():   choice[0] = "auto"
    def on_manual(): choice[0] = "manual"
    def on_vblu():   choice[0] = "verify_blue"
    API.AddControlOnClick(btn_auto,   on_auto)
    API.AddControlOnClick(btn_manual, on_manual)
    API.AddControlOnClick(btn_vblu,   on_vblu)
    API.AddGump(g)

    while choice[0] is None:
        API.ProcessCallbacks()
        API.Pause(0.1)
    g.Dispose()
    return choice[0]

def pick_blue_tile(blue_tiles):
    landings = load_landings()
    landing_map = {}
    for entry in landings:
        landing_map[(entry[0], entry[1])] = (entry[2], entry[3])

    ROW_H = 46
    VISIBLE = min(len(blue_tiles), 8)
    LIST_H  = VISIBLE * ROW_H
    GUMP_W  = 310
    GUMP_H  = LIST_H + 70

    g = API.CreateGump(True, True, True)
    g.SetRect(350, 180, GUMP_W, GUMP_H)
    bg = API.CreateGumpColorBox(0.92, "#16213e")
    bg.SetRect(0, 0, GUMP_W, GUMP_H)
    g.Add(bg)
    lbl = API.CreateGumpTTFLabel("Seleziona portale BLU:", 13, "#FFFFFF")
    lbl.SetRect(8, 6, GUMP_W - 16, 22)
    g.Add(lbl)

    sa = API.CreateGumpScrollArea(0, 32, GUMP_W, LIST_H)
    g.Add(sa)

    choice = ["waiting"]

    def make_cb(tile):
        def cb(): choice[0] = tile
        return cb

    for i, tile in enumerate(blue_tiles):
        tx, ty = tile
        row_y = i * ROW_H
        coord = API.CreateGumpTTFLabel("(" + str(tx) + ", " + str(ty) + ")", 12, "#88CCFF")
        coord.SetRect(5, row_y + 4, 230, 18)
        sa.Add(coord)
        if (tx, ty) in landing_map:
            lx, ly = landing_map[(tx, ty)]
            land_text = "-> (" + str(lx) + ", " + str(ly) + ")"
            land_color = "#AAFFAA"
        else:
            land_text = "-> ?"
            land_color = "#888888"
        land_lbl = API.CreateGumpTTFLabel(land_text, 11, land_color)
        land_lbl.SetRect(5, row_y + 24, 230, 16)
        sa.Add(land_lbl)
        btn = API.CreateSimpleButton("Vai", 55, 24)
        btn.SetRect(245, row_y + 11, 55, 24)
        sa.Add(btn)
        API.AddControlOnClick(btn, make_cb(tile))

    btn_cancel = API.CreateSimpleButton("Annulla", 100, 28)
    btn_cancel.SetRect(90, 38 + LIST_H, 100, 28)
    g.Add(btn_cancel)
    def on_cancel(): choice[0] = None
    API.AddControlOnClick(btn_cancel, on_cancel)

    API.AddGump(g)
    while choice[0] == "waiting":
        API.ProcessCallbacks()
        API.Pause(0.1)
    g.Dispose()
    return choice[0]


def enter_portal_manually(state, cells, portal_map, queue):
    blue_tiles = sorted([(x, y) for (x, y), s in state.items() if s == S_BLUE], key=lambda t: t[0])

    if blue_tiles:
        selected = pick_blue_tile(blue_tiles)
        if selected is None:
            API.SysMsg("Selezione annullata. Modalita' autonoma.", 33)
            return (int(API.Player.X), int(API.Player.Y))
        tx, ty = selected
    else:
        API.SysMsg("Nessun portale BLU noto. Clicca il tile nel mondo (3 min)...", 33)
        tgt = API.RequestAnyTarget(180)
        if not tgt:
            API.SysMsg("Nessun target. Modalita' autonoma.", 33)
            return (int(API.Player.X), int(API.Player.Y))
        tx, ty = int(tgt.X), int(tgt.Y)

    API.SysMsg("Portale selezionato: (" + str(tx) + "," + str(ty) + ")", 68)

    if not (X_MIN <= tx <= X_MAX and Y_MIN <= ty <= Y_MAX):
        API.SysMsg("Tile fuori area. Modalita' autonoma.", 33)
        return (int(API.Player.X), int(API.Player.Y))

    # Trova tile verde adiacente per avvicinarsi
    approach = None
    for ddx, ddy, _ in DIRS:
        adj = (tx+ddx, ty+ddy)
        if state.get(adj, S_UNKNOWN) == S_GREEN:
            approach = adj
            break
    if approach is None:
        API.SysMsg("Nessun tile verde adiacente. Impossibile avvicinarsi.", 33)
        return (int(API.Player.X), int(API.Player.Y))

    if not navigate_green(approach, state):
        API.SysMsg("Navigazione verso il target fallita.", 33)
        return (int(API.Player.X), int(API.Player.Y))

    if max(abs(int(API.Player.X)-tx), abs(int(API.Player.Y)-ty)) != 1:
        API.SysMsg("Non adiacente al target. Salto.", 33)
        return (int(API.Player.X), int(API.Player.Y))

    result = classify(tx, ty)

    if result == S_WALL:
        API.SysMsg("Il tile e' un muro.", 900)
        state[(tx, ty)] = S_WALL
        paint(cells, tx, ty, S_WALL)
        return (int(API.Player.X), int(API.Player.Y))

    if result == S_GREEN:
        API.SysMsg("Tile verde. Parto da qui.", 68)
        state[(tx, ty)] = S_GREEN
        paint(cells, tx, ty, S_GREEN)
        expand_queue((tx, ty), state, queue, cells=cells)
        return (tx, ty)

    landed = (int(API.Player.X), int(API.Player.Y))
    if result == S_RED:
        # Porta allo START — classifica correttamente e torna all'ultimo verde
        state[(tx, ty)] = S_RED
        paint(cells, tx, ty, S_RED)
        API.SysMsg("Il tile porta a START (rosso). Torno...", 32)
        return (int(API.Player.X), int(API.Player.Y))

    # result == S_BLUE: porta in zona nuova
    state[(tx, ty)] = S_BLUE
    paint(cells, tx, ty, S_BLUE)
    API.SysMsg("Portale BLU -> atterrato a (" + str(landed[0]) + "," + str(landed[1]) + ")", 88)
    if landed not in state:
        state[landed] = S_GREEN
        paint(cells, landed[0], landed[1], S_GREEN)
    expand_queue(landed, state, queue, cells=cells)
    portal_map[landed] = (tx, ty)
    save_data(state)
    return landed

# ── Verifica BLU ─────────────────────────────────────────────

def verify_blue_tiles(state, cells, portal_map, queue):
    """
    Naviga tutti i tile S_BLUE per verificarne il comportamento reale:
      S_GREEN → riclassifica, espandi coda
      S_RED   → riclassifica
      S_BLUE  → mantieni, salva landing in LANDINGS_FILE
      S_WALL  → riclassifica
    """
    landings = load_landings()
    blue_tiles = [(x, y) for (x, y), s in state.items() if s == S_BLUE]

    if not blue_tiles:
        API.SysMsg("Nessun tile BLU da verificare.", 33)
        return

    px, py = int(API.Player.X), int(API.Player.Y)
    blue_tiles.sort(key=lambda t: abs(t[0]-px) + abs(t[1]-py))
    API.SysMsg("Verifica " + str(len(blue_tiles)) + " tile BLU...", 88)

    for bt in blue_tiles:
        if state.get(bt, S_BLUE) != S_BLUE:
            continue  # già riclassificato in questo ciclo

        tx, ty = bt

        approach = None
        for ddx, ddy, _ in DIRS:
            adj = (tx+ddx, ty+ddy)
            if state.get(adj, S_UNKNOWN) == S_GREEN:
                approach = adj
                break

        if approach is None:
            API.SysMsg("BLU (" + str(tx) + "," + str(ty) + ") nessun verde adiacente. Salto.", 33)
            continue

        if not navigate_green(approach, state):
            API.SysMsg("BLU (" + str(tx) + "," + str(ty) + ") nav fallita. Salto.", 33)
            continue

        if max(abs(int(API.Player.X)-tx), abs(int(API.Player.Y)-ty)) != 1:
            API.SysMsg("BLU (" + str(tx) + "," + str(ty) + ") non adiacente. Salto.", 33)
            continue

        paint_highlight(cells, tx, ty)
        result = classify(tx, ty)

        if result == S_GREEN:
            state[bt] = S_GREEN
            paint(cells, tx, ty, S_GREEN)
            expand_queue(bt, state, queue, cells=cells)
            API.SysMsg("BLU->VERDE (" + str(tx) + "," + str(ty) + ")", 68)
            save_data(state)

        elif result == S_RED:
            state[bt] = S_RED
            paint(cells, tx, ty, S_RED)
            API.SysMsg("BLU->ROSSO (" + str(tx) + "," + str(ty) + ")", 32)
            save_data(state)
            # Siamo allo START; il prossimo navigate_green gestirà il ritorno

        elif result == S_BLUE:
            landed = (int(API.Player.X), int(API.Player.Y))
            API.SysMsg("BLU (" + str(tx) + "," + str(ty) + ") -> " + str(landed), 88)
            landings.append([int(tx), int(ty), int(landed[0]), int(landed[1])])
            save_landings(landings)
            if landed not in state:
                state[landed] = S_GREEN
                paint(cells, landed[0], landed[1], S_GREEN)
            expand_queue(landed, state, queue, cells=cells)
            portal_map[landed] = bt
            save_data(state)
            if not can_reach_any_queued(state, queue, landed[0], landed[1]):
                if re_enter_via_portal(landed, state, portal_map):
                    API.SysMsg("Rientrato via portale.", 68)
                else:
                    API.SysMsg("Zona isolata dopo BLU. Riavvia.", 900)
                    break

        elif result == S_WALL:
            state[bt] = S_WALL
            paint(cells, tx, ty, S_WALL)
            API.SysMsg("BLU->MURO (" + str(tx) + "," + str(ty) + ")", 900)
            save_data(state)

    API.SysMsg("Verifica BLU terminata.", 68)


# ── Main ──────────────────────────────────────────────────────

def main():
    API.SysMsg("=== MAZE SCANNER v2 ===", 88)
    API.SysMsg("Area " + str(TILE_W) + "x" + str(TILE_H) + "  cella=" + str(CELL) + "px", 68)
    API.Pause(1)

    state = load_data()

    # ── FASE 1: Scansione statica (senza movimento) ───────────
    API.SysMsg("FASE 1: scansione statics nell'area...", 88)
    statics = API.GetStaticsInArea(X_MIN, Y_MIN, X_MAX, Y_MAX)
    n_pre = 0
    if statics:
        for s in statics:
            if s.IsImpassible:
                pos = (int(s.X), int(s.Y))
                if pos not in state:
                    state[pos] = S_WALL
                    n_pre += 1
    API.SysMsg("Muri statici pre-classificati: " + str(n_pre), 900)
    save_data(state)

    # ── Calcola bounds visualizzazione dalla mappa corrente ───
    DISP.update(compute_display_cfg(state))
    API.SysMsg("Display " + str(DISP["w"]) + "x" + str(DISP["h"]) + " cell=" + str(DISP["cell"]) + "px", 68)

    # ── Crea mappa grafica (gump non bloccante) ───────────────
    cells = [[None]*DISP["w"] for _ in range(DISP["h"])]
    API.SysMsg("Creo gump (" + str(DISP["w"]*DISP["h"]) + " celle)...", 946)
    create_gump(cells)
    for (x, y), s in state.items():
        paint(cells, x, y, s)
    API.SysMsg("Mappa pronta. FASE 2: BFS...", 68)
    API.Pause(0.5)

    # ── FASE 2: Navigazione BFS ───────────────────────────────
    if (int(API.Player.X), int(API.Player.Y)) != START:
        API.SysMsg("Raggiungo START...", 946)
        API.Pathfind(START[0], START[1], wait=True, timeout=30)
        API.Pause(0.5)
        if (int(API.Player.X), int(API.Player.Y)) != START:
            API.SysMsg("Impossibile raggiungere START. Stop.", 32)
            return

    if START not in state:
        state[START] = S_GREEN
    paint(cells, START[0], START[1], S_GREEN)

    last_green = START
    counts = {S_GREEN:0, S_RED:0, S_BLUE:0, S_WALL:0}
    portal_map = {}   # {landing_pos: blue_tile_pos} — per rientrare in zone isolate
    nav_fails  = {}   # {tile: n_fallimenti_consecutivi}
    skipped    = set()  # tile definitivamente ignorate (>=3 fallimenti)

    # ── Scelta modalità (prima di costruire la coda) ──────────────
    mode = ask_mode()
    queue = set()
    current_landing = None  # zona target in modalità manuale
    if mode == "manual":
        # Entra nel portale, poi espande la coda da tutti i verdi noti
        # (tile_priority metterà in cima quelli vicini al player)
        last_green = enter_portal_manually(state, cells, portal_map, queue)
        API.SysMsg("BFS riparte da (" + str(last_green[0]) + "," + str(last_green[1]) + ")", 88)
        # Se l'enter_portal_manually ha confermato un BLU, last_green è in portal_map.
        if last_green in portal_map:
            current_landing = last_green

    # In entrambe le modalità: riempie la coda da tutti i verdi noti
    for (gx, gy), gs in state.items():
        if gs == S_GREEN:
            expand_queue((gx, gy), state, queue, cells=cells)

    q_hdr, q_rows = create_queue_gump()

    if mode == "verify_blue":
        verify_blue_tiles(state, cells, portal_map, queue)
        save_data(state)
        API.SysMsg("Fine. V=" + str(sum(1 for s in state.values() if s==S_GREEN)) +
                   " R=" + str(sum(1 for s in state.values() if s==S_RED)) +
                   " B=" + str(sum(1 for s in state.values() if s==S_BLUE)), 68)
        return

    processed = 0
    SAVE_EVERY = 30

    while queue:
        px_cur, py_cur = int(API.Player.X), int(API.Player.Y)
        reachable = reachable_greens(px_cur, py_cur, state)
        update_queue_gump(q_hdr, q_rows, queue, state, px_cur, py_cur, nav_fails)

        target = min(queue, key=lambda t, p=px_cur, q=py_cur, r=reachable: tile_priority(t, state, p, q, r))

        # Se anche il miglior target ha priorità "infinita" -> nessun tile in coda
        # è raggiungibile via verdi dalla posizione attuale. Inutile lanciare A*.
        if tile_priority(target, state, px_cur, py_cur, reachable) >= 999999:
            API.SysMsg("Zona corrente isolata da " + str(len(queue)) + " tile in coda. Rientro portale...", 33)
            portal_target = current_landing if (mode == "manual" and current_landing is not None) else last_green
            if re_enter_via_portal(portal_target, state, portal_map):
                last_green = (int(API.Player.X), int(API.Player.Y))
                API.SysMsg("Rientrato a " + str(last_green), 88)
                continue
            API.SysMsg("Rientro fallito. Stop.", 900)
            break

        queue.discard(target)

        if target in state:
            continue
        if target in skipped:
            continue

        tx, ty = target

        # Trova tile verde adiacente al target
        approach = None
        for ddx, ddy, _ in DIRS:
            adj = (tx+ddx, ty+ddy)
            if state.get(adj, S_UNKNOWN) == S_GREEN:
                approach = adj
                break
        if approach is None:
            continue

        px_now, py_now = int(API.Player.X), int(API.Player.Y)
        path_ok = astar_green((px_now, py_now), approach, state)
        misclass = {}
        if not navigate_green(approach, state, misclass):
            if "tile" in misclass:
                # Tile verde mal classificato: era un teleport
                bad, landed_mc = misclass["tile"], misclass["landed"]
                new_s = S_RED if landed_mc == START else S_BLUE
                state[bad] = new_s
                paint(cells, bad[0], bad[1], new_s)
                API.SysMsg("Corretto tile (" + str(bad[0]) + "," + str(bad[1]) + ") -> " + S_LABEL[new_s], S_HUE[new_s])
                if new_s == S_BLUE:
                    if landed_mc not in state:
                        state[landed_mc] = S_GREEN
                        paint(cells, landed_mc[0], landed_mc[1], S_GREEN)
                    expand_queue(landed_mc, state, queue, cells=cells)
                    portal_map[landed_mc] = bad
                    last_green = landed_mc
                    skipped.clear(); nav_fails.clear()
                else:
                    navigate_green(last_green, state)
            elif path_ok is None:
                # A* ha detto subito "irraggiungibile": deterministico, inutile riprovare.
                skipped.add(target)
                API.SysMsg("(" + str(tx) + "," + str(ty) + ") irraggiungibile via verdi. Salto.", 900)
            else:
                fails = nav_fails.get(target, 0) + 1
                nav_fails[target] = fails
                API.SysMsg("Nav fallita (" + str(tx) + "," + str(ty) + ") pos?(" + str(px_now) + "," + str(py_now) + ") [" + str(fails) + "/3]", 33)
                if fails >= 3:
                    skipped.add(target)
                    API.SysMsg("Tile (" + str(tx) + "," + str(ty) + ") ignorata.", 900)
            continue

        nav_fails[target] = 0  # reset al successo

        # Verifica adiacenza Chebyshev = 1
        if max(abs(int(API.Player.X)-tx), abs(int(API.Player.Y)-ty)) != 1:
            continue

        paint(cells, int(API.Player.X), int(API.Player.Y), S_GREEN, is_player=True)
        paint_highlight(cells, tx, ty)

        result = classify(tx, ty)
        state[target] = result
        counts[result] = counts.get(result, 0) + 1
        processed += 1
        paint(cells, tx, ty, result)

        pct = processed * 100 // (TILE_W * TILE_H)
        API.SysMsg("[" + str(pct) + "%] (" + str(tx) + "," + str(ty) + ") " + S_LABEL[result], S_HUE[result])

        if result == S_GREEN:
            last_green = target
            expand_queue(target, state, queue, skipped, cells)
            if target == GOAL:
                API.SysMsg("=== GOAL RAGGIUNTO! ===", 68)
            if processed % SAVE_EVERY == 0:
                save_data(state)

        elif result == S_RED:
            cur = (int(API.Player.X), int(API.Player.Y))
            API.SysMsg("Rimandato a " + str(cur) + ". Verifico raggiungibilita'...", 32)
            save_data(state)
            # Modalità manuale: se siamo lontani dal landing target, forza il rientro
            # nel portale originale prima di esplorare la zona di START.
            forced_back = False
            if mode == "manual" and current_landing is not None:
                dist_to_landing = abs(cur[0] - current_landing[0]) + abs(cur[1] - current_landing[1])
                if dist_to_landing > 10:
                    if re_enter_via_portal(current_landing, state, portal_map):
                        last_green = (int(API.Player.X), int(API.Player.Y))
                        API.SysMsg("Modalita' manuale: rientrato nel landing " + str(last_green), 88)
                        forced_back = True
            if forced_back:
                pass
            elif can_reach_any_queued(state, queue, cur[0], cur[1]):
                last_green = cur
                API.SysMsg("Tile raggiungibili. Continuo.", 68)
            elif re_enter_via_portal(last_green, state, portal_map):
                last_green = (int(API.Player.X), int(API.Player.Y))
                API.SysMsg("Rientrato via portale a " + str(last_green), 88)
            else:
                API.SysMsg("Nessun tile raggiungibile e portale inaccessibile. Riavvia.", 900)
                break

        elif result == S_BLUE:
            landed = (int(API.Player.X), int(API.Player.Y))
            API.SysMsg("Portale BLU -> atterrato a " + str(landed), 88)
            if landed not in state:
                state[landed] = S_GREEN
                paint(cells, landed[0], landed[1], S_GREEN)
            expand_queue(landed, state, queue, cells=cells)
            portal_map[landed] = target
            if mode == "manual":
                current_landing = landed  # zona di interesse aggiornata
            save_data(state)
            if can_reach_any_queued(state, queue, landed[0], landed[1]):
                last_green = landed
                skipped.clear(); nav_fails.clear()
                API.SysMsg("Nuova zona esplorabile. Reset e continuo.", 88)
            elif re_enter_via_portal(last_green, state, portal_map):
                last_green = (int(API.Player.X), int(API.Player.Y))
                API.SysMsg("Zona isolata. Rientrato via portale a " + str(last_green), 88)
            else:
                API.SysMsg("Zona isolata e portale inaccessibile. Riavvia.", 900)
                break

    remaining = sum(1 for x in range(X_MIN, X_MAX+1)
                    for y in range(Y_MIN, Y_MAX+1)
                    if (x, y) not in state)
    save_data(state)
    if remaining > 0:
        API.SysMsg("BFS esaurita. Non classificati: " + str(remaining), 33)
        API.SysMsg("Zone isolate: nessun percorso verde le collega.", 33)
    else:
        API.SysMsg("=== SCANSIONE COMPLETATA ===", 68)
    API.SysMsg("V=" + str(counts[S_GREEN]) + " R=" + str(counts[S_RED]) +
               " B=" + str(counts[S_BLUE]) + " M=" + str(counts[S_WALL]), 68)


main()
