import API
import os
import json

DATA_FILE  = os.path.join(os.path.dirname(API.ScriptPath), "maze_data.json")
ROUTE_FILE = os.path.join(os.path.dirname(API.ScriptPath), "maze_route.txt")

START = (5154, 2369)
GOAL  = (5204, 2367)

KNOWN_BAD = [(5154, 2367), (5154, 2366)]

# ── Area di scansione (centrata su START) ─────────────────────
RADIUS_X = 260
RADIUS_Y = 100
X_MIN = START[0] - RADIUS_X
X_MAX = START[0] + RADIUS_X
Y_MIN = START[1] - RADIUS_Y
Y_MAX = START[1] + RADIUS_Y

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

# ── Snake order per BFS ───────────────────────────────────────

def make_snake_order():
    idx = {}
    i = 0
    for ri, y in enumerate(range(Y_MIN, Y_MAX + 1)):
        if ri % 2 == 0:
            for x in range(X_MIN, X_MAX + 1):
                idx[(x, y)] = i
                i += 1
        else:
            for x in range(X_MAX, X_MIN - 1, -1):
                idx[(x, y)] = i
                i += 1
    return idx

# ── Gump (acceptMouseInput=False) ─────────────────────────────

def rgb_hex(r, g, b):
    h = "0123456789ABCDEF"
    return "#" + h[r>>4]+h[r&15] + h[g>>4]+h[g&15] + h[b>>4]+h[b&15]

def create_gump(cells):
    gw = TILE_W * CELL + 4
    gh = TILE_H * CELL + 4
    gump = API.CreateModernGump(20, 20, gw, gh, False)
    bg = API.CreateGumpColorBox(1.0, "#111111")
    bg.SetRect(0, 0, gw, gh)
    gump.Add(bg)
    unk = rgb_hex(*S_RGB[S_UNKNOWN])
    cell_sz = max(1, CELL - 1)
    for row in range(TILE_H):
        for col in range(TILE_W):
            c = API.CreateGumpColorBox(1.0, unk)
            c.SetRect(col * CELL + 2, row * CELL + 2, cell_sz, cell_sz)
            gump.Add(c)
            cells[row][col] = c
    API.AddGump(gump)

def paint(cells, x, y, state_val, is_player=False):
    col = x - X_MIN
    row = y - Y_MIN
    if 0 <= row < TILE_H and 0 <= col < TILE_W and cells[row][col] is not None:
        r, g, b = RGB_PLAYER if is_player else S_RGB[state_val]
        cells[row][col].SetBaseColor(r, g, b, 255)
    if not is_player and state_val != S_UNKNOWN:
        API.MarkTile(x, y, S_MARK[state_val])

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

def navigate_green(target, state):
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
        API.Pause(0.1)
        API.Run(dname)
        API.Pause(0.1)
        if (int(API.Player.X), int(API.Player.Y)) != (sx, sy):
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
    API.Pause(1.0)
    px, py = int(API.Player.X), int(API.Player.Y)
    if px == cx and py == cy:
        return S_WALL
    if px == tx and py == ty:
        return S_GREEN
    return S_RED

# ── Helper ────────────────────────────────────────────────────

def expand_queue(pos, state, queue):
    x, y = pos
    for ddx, ddy, _ in DIRS:
        nb = (x+ddx, y+ddy)
        if X_MIN<=nb[0]<=X_MAX and Y_MIN<=nb[1]<=Y_MAX and nb not in state and nb not in queue:
            queue.add(nb)

def re_enter_via_portal(last_green, state, portal_map):
    """
    Cerca un portale BLU noto da cui last_green è raggiungibile via A*,
    ci entra fisicamente e naviga fino a last_green.
    Ritorna True se last_green viene raggiunto.
    """
    for landing_pos, blue_tile_pos in portal_map.items():
        # Il portale è utile solo se last_green è raggiungibile dal suo landing
        if astar_green(landing_pos, last_green, state) is None:
            continue
        # Trova tile verde adiacente al tile BLU (approccio nella regione corrente)
        btx, bty = blue_tile_pos
        approach = None
        for ddx, ddy, _ in DIRS:
            adj = (btx+ddx, bty+ddy)
            if state.get(adj, S_UNKNOWN) == S_GREEN:
                approach = adj
                break
        if approach is None:
            continue
        # Naviga all'approccio
        if not navigate_green(approach, state):
            continue
        # Salta sul tile BLU
        dx, dy = btx - int(API.Player.X), bty - int(API.Player.Y)
        dname = next((dn for adx,ady,dn in DIRS if adx==dx and ady==dy), None)
        if dname is None:
            continue
        API.Turn(dname); API.Pause(0.1)
        API.Run(dname); API.Pause(0.3)
        if (int(API.Player.X), int(API.Player.Y)) != landing_pos:
            continue  # teleport inatteso, prova altro portale
        # Ora siamo nel landing della regione corretta
        return navigate_green(last_green, state)
    return False

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

    # ── Crea mappa grafica (gump non bloccante) ───────────────
    cells = [[None]*TILE_W for _ in range(TILE_H)]
    API.SysMsg("Creo gump (" + str(TILE_W*TILE_H) + " celle)...", 946)
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

    snake_ord = make_snake_order()
    last_green = START
    counts = {S_GREEN:0, S_RED:0, S_BLUE:0, S_WALL:0}
    portal_map = {}   # {landing_pos: blue_tile_pos} — per rientrare in zone isolate

    queue = set()
    for (gx, gy), gs in state.items():
        if gs == S_GREEN:
            expand_queue((gx, gy), state, queue)

    processed = 0
    SAVE_EVERY = 30

    while queue:
        target = min(queue, key=lambda t: snake_ord.get(t, 999999))
        queue.discard(target)

        if target in state:
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

        if not navigate_green(approach, state):
            API.SysMsg("Nav fallita verso (" + str(tx) + "," + str(ty) + "). Salto.", 33)
            continue

        # Verifica adiacenza Chebyshev = 1
        if max(abs(int(API.Player.X)-tx), abs(int(API.Player.Y)-ty)) != 1:
            continue

        paint(cells, int(API.Player.X), int(API.Player.Y), S_GREEN, is_player=True)

        result = classify(tx, ty)
        state[target] = result
        counts[result] = counts.get(result, 0) + 1
        processed += 1
        paint(cells, tx, ty, result)

        pct = processed * 100 // (TILE_W * TILE_H)
        API.SysMsg("[" + str(pct) + "%] (" + str(tx) + "," + str(ty) + ") " + S_LABEL[result], S_HUE[result])

        if result == S_GREEN:
            last_green = target
            expand_queue(target, state, queue)
            if target == GOAL:
                API.SysMsg("=== GOAL RAGGIUNTO! ===", 68)
            if processed % SAVE_EVERY == 0:
                save_data(state)

        elif result == S_RED:
            landed = (int(API.Player.X), int(API.Player.Y))
            API.SysMsg("Teleport a (" + str(landed[0]) + "," + str(landed[1]) + ")! Torno...", 32)
            if landed not in state:
                state[landed] = S_GREEN
                paint(cells, landed[0], landed[1], S_GREEN)
                expand_queue(landed, state, queue)
            save_data(state)

            if not navigate_green(last_green, state):
                # A* diretto fallito: prova a rientrare via portale BLU noto
                if re_enter_via_portal(last_green, state, portal_map):
                    API.SysMsg("Rientrato via portale, riprendo BFS.", 88)
                else:
                    # Zona genuinamente nuova: tile e' BLU
                    state[target] = S_BLUE
                    paint(cells, tx, ty, S_BLUE)
                    counts[S_RED] -= 1
                    counts[S_BLUE] = counts.get(S_BLUE, 0) + 1
                    cur = (int(API.Player.X), int(API.Player.Y))
                    API.SysMsg("TILE BLU -> atterrato a (" + str(cur[0]) + "," + str(cur[1]) + "), continuo da qui.", 88)
                    if cur not in state:
                        state[cur] = S_GREEN
                        paint(cells, cur[0], cur[1], S_GREEN)
                    expand_queue(cur, state, queue)
                    portal_map[cur] = target  # landing_pos → blue_tile_pos
                    last_green = cur
                    save_data(state)

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
