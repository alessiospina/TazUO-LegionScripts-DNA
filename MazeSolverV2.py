import API
import os
import json

# ── Costanti ────────────────────────────────────────────────────

DATA_FILE = os.path.join(os.path.dirname(API.ScriptPath), "maze_v2_data.json")

START = (5154, 2369)
GOAL  = (5204, 2367)
KNOWN_BAD = [(5154, 2367), (5154, 2366)]

X_MIN, X_MAX = 5129, 5210
Y_MIN, Y_MAX = 2359, 2457
MAX_PX = 600

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

S_UNKNOWN, S_GREEN, S_RED, S_BLUE, S_WALL = 0, 1, 2, 3, 4
S_LABEL = ["?", "VERDE", "ROSSO", "BLU", "MURO"]
S_HUE   = [946, 68, 32, 88, 900]
S_MARK  = [0, 68, 32, 88, 900]
S_RGB   = [(40,40,40), (0,180,0), (220,0,0), (0,100,255), (10,10,10)]
RGB_PLAYER = (180, 0, 255)
RGB_TARGET = (255, 165, 0)
HUE_TARGET = 53

INF_PRIO    = 999999
STALL_LIMIT = 25
SAVE_EVERY  = 25
TELE_DIST   = 3   # Chebyshev > TELE_DIST = teleport reale, non lag

# Palette per colorare le zone (verdi mantengono famiglia di tinte verdi)
ZONE_PALETTE = [
    (0, 180, 0),
    (40, 200, 80),
    (120, 220, 30),
    (0, 160, 120),
    (80, 180, 40),
    (160, 220, 60),
    (0, 200, 160),
    (100, 200, 0),
    (60, 160, 100),
]


# ── Union-Find sui tile verdi ──────────────────────────────────

class DSU:
    def __init__(self):
        self.parent = {}
        self.size = {}

    def add(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.size[x] = 1

    def find(self, x):
        if x not in self.parent:
            return None
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        cur = x
        while self.parent[cur] != root:
            nxt = self.parent[cur]
            self.parent[cur] = root
            cur = nxt
        return root

    def union(self, a, b):
        ra = self.find(a); rb = self.find(b)
        if ra is None or rb is None or ra == rb:
            return
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]


# ── Modello: stato + zone + portali ───────────────────────────

class Maze:
    def __init__(self):
        self.state = {}      # (x,y) -> S_*
        self.dsu = DSU()     # solo verdi
        self.portals = {}    # blue_tile -> landing
        self.landings = {}   # landing -> blue_tile

    def kind(self, tile):
        return self.state.get(tile, S_UNKNOWN)

    def zone_of(self, tile):
        return self.dsu.find(tile)

    def set(self, tile, kind, landing=None):
        prev = self.state.get(tile)
        self.state[tile] = kind
        if kind == S_GREEN:
            self.dsu.add(tile)
            for dx, dy, _ in DIRS:
                nb = (tile[0]+dx, tile[1]+dy)
                if self.state.get(nb) == S_GREEN:
                    self.dsu.union(tile, nb)
        if kind == S_BLUE and landing is not None:
            self.portals[tile] = landing
            self.landings[landing] = tile
        return prev

    def zone_of_player(self, px, py):
        if self.kind((px, py)) == S_GREEN:
            return self.zone_of((px, py))
        for dx, dy, _ in DIRS:
            nb = (px+dx, py+dy)
            if self.kind(nb) == S_GREEN:
                return self.zone_of(nb)
        return None

    def green_adj(self, tile, in_zone=None):
        """Vicini verdi di tile; opzionalmente filtrati per zona."""
        out = []
        for dx, dy, _ in DIRS:
            nb = (tile[0]+dx, tile[1]+dy)
            if self.kind(nb) == S_GREEN:
                if in_zone is None or self.zone_of(nb) == in_zone:
                    out.append(nb)
        return out


# ── Persistenza ────────────────────────────────────────────────

def load_maze(maze):
    for t in KNOWN_BAD:
        maze.set(t, S_RED)
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, "r") as f:
            raw = json.load(f)
        for item in raw.get("tiles", []):
            maze.set((item[0], item[1]), item[2])
        for p in raw.get("portals", []):
            blue = (p[0], p[1])
            landing = (p[2], p[3])
            maze.portals[blue] = landing
            maze.landings[landing] = blue
        API.SysMsg("Caricati " + str(len(maze.state)) + " tile, " +
                   str(len(maze.portals)) + " portali.", 68)
    except Exception:
        API.SysMsg("Errore lettura dati, riparto.", 33)


def save_maze(maze):
    tiles = [[int(t[0]), int(t[1]), int(k)] for t, k in maze.state.items()]
    portals = [[int(b[0]), int(b[1]), int(l[0]), int(l[1])]
               for b, l in maze.portals.items()]
    with open(DATA_FILE, "w") as f:
        json.dump({"tiles": tiles, "portals": portals}, f)


# ── A* intra-zona ──────────────────────────────────────────────

def astar_green(start, goal, maze):
    if maze.kind(goal) != S_GREEN:
        return None
    # Se start non e' verde, accetta che la prima mossa sia su un verde adiacente
    if maze.kind(start) != S_GREEN:
        return None
    if maze.zone_of(start) != maze.zone_of(goal):
        return None

    gx, gy = goal
    def h(p): return abs(p[0]-gx) + abs(p[1]-gy)
    open_list = [(h(start), start)]
    came = {}
    gscore = {start: 0}
    closed = set()
    while open_list:
        open_list.sort(key=lambda kv: kv[0])
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
            if nb in closed or maze.kind(nb) != S_GREEN:
                continue
            ng = gscore[cur] + 1
            if nb not in gscore or ng < gscore[nb]:
                came[nb] = cur
                gscore[nb] = ng
                open_list.append((ng + h(nb), nb))
    return None


# ── Multi-zona: pianificazione via grafo dei portali ──────────

def build_zone_graph(maze):
    """Per ogni portale BLU di cui conosciamo il landing, crea un arco
       (zona_di_blue) -> (zona_di_landing) etichettato (blue, landing)."""
    edges = {}  # zone_id -> list of (blue, landing, dest_zone)
    for blue, landing in maze.portals.items():
        src_greens = maze.green_adj(blue)
        if not src_greens:
            continue
        src_zone = maze.zone_of(src_greens[0])
        dst_zone = maze.zone_of(landing)
        if src_zone is None or dst_zone is None:
            continue
        edges.setdefault(src_zone, []).append((blue, landing, dst_zone))
    return edges


def plan_zone_path(src_zone, dst_zone, maze):
    """BFS sul grafo delle zone. Ritorna lista di ('portal', blue, landing)
       da eseguire in sequenza, oppure None."""
    if src_zone == dst_zone:
        return []
    edges = build_zone_graph(maze)
    came = {}
    visited = {src_zone}
    queue = [src_zone]
    while queue:
        z = queue.pop(0)
        if z == dst_zone:
            actions = []
            while z in came:
                src, blue, landing = came[z]
                actions.append(("portal", blue, landing))
                z = src
            return actions[::-1]
        for blue, landing, dz in edges.get(z, []):
            if dz in visited:
                continue
            visited.add(dz)
            came[dz] = (z, blue, landing)
            queue.append(dz)
    return None


# ── Movimento di basso livello ─────────────────────────────────

def step_to(sx, sy):
    """Un passo verso (sx,sy). Ritorna ('ok'|'teleport'|'fail', pos)."""
    cx, cy = int(API.Player.X), int(API.Player.Y)
    if (cx, cy) == (sx, sy):
        return ("ok", (cx, cy))
    dx, dy = sx - cx, sy - cy
    dname = next((d for ddx, ddy, d in DIRS if ddx == dx and ddy == dy), None)
    if dname is None:
        return ("fail", (cx, cy))
    API.Turn(dname); API.Pause(0.15)
    API.Run(dname)
    for _ in range(10):
        API.Pause(0.2)
        if (int(API.Player.X), int(API.Player.Y)) == (sx, sy):
            return ("ok", (sx, sy))
    nx, ny = int(API.Player.X), int(API.Player.Y)
    if max(abs(nx-sx), abs(ny-sy)) > TELE_DIST:
        return ("teleport", (nx, ny))
    return ("fail", (nx, ny))


def navigate_intra_zone(target, maze):
    """Cammina via A* su verdi fino a target. Se un tile verde si rivela
       teleport, lo riclassifica e ritorna False."""
    px, py = int(API.Player.X), int(API.Player.Y)
    if (px, py) == target:
        return True
    path = astar_green((px, py), target, maze)
    if not path or len(path) < 2:
        return False
    for sx, sy in path[1:]:
        result, pos = step_to(sx, sy)
        if result == "ok":
            continue
        if result == "teleport":
            kind = S_RED if pos == START else S_BLUE
            maze.set((sx, sy), kind, landing=pos if kind == S_BLUE else None)
            API.SysMsg("Verde mal-classificato (" + str(sx) + "," + str(sy) +
                       ") -> " + S_LABEL[kind], S_HUE[kind])
            return False
        return False
    return True


def classify_step(tx, ty):
    """Walk su (tx,ty); ritorna (kind, landed)."""
    cx, cy = int(API.Player.X), int(API.Player.Y)
    dx, dy = tx - cx, ty - cy
    dname = next((d for ddx, ddy, d in DIRS if ddx == dx and ddy == dy), None)
    if dname is None:
        return (S_WALL, (cx, cy))
    API.Turn(dname); API.Pause(0.3)
    API.Walk(dname)
    moved = False
    for _ in range(50):
        API.Pause(0.2)
        if (int(API.Player.X), int(API.Player.Y)) != (cx, cy):
            moved = True
            break
    if not moved:
        return (S_WALL, (cx, cy))
    API.Pause(0.35)   # stabilizzazione anti-interpolazione
    px, py = int(API.Player.X), int(API.Player.Y)
    if (px, py) == (tx, ty):
        return (S_GREEN, (px, py))
    if (px, py) == START:
        return (S_RED, (px, py))
    return (S_BLUE, (px, py))


def traverse_portal(blue, landing, maze):
    """Avvicinati al BLU e attraversalo; verifica atterraggio == landing."""
    src_greens = maze.green_adj(blue)
    if not src_greens:
        return False
    if not navigate_intra_zone(src_greens[0], maze):
        return False
    cx, cy = int(API.Player.X), int(API.Player.Y)
    dx, dy = blue[0] - cx, blue[1] - cy
    dname = next((d for ddx, ddy, d in DIRS if ddx == dx and ddy == dy), None)
    if dname is None:
        return False
    API.Turn(dname); API.Pause(0.1)
    API.Run(dname); API.Pause(0.5)
    return (int(API.Player.X), int(API.Player.Y)) == landing


# ── Display ────────────────────────────────────────────────────

def rgb_hex(r, g, b):
    h = "0123456789ABCDEF"
    return "#" + h[r>>4]+h[r&15] + h[g>>4]+h[g&15] + h[b>>4]+h[b&15]


def compute_display(maze, margin=15):
    w = X_MAX - X_MIN + 1
    h = Y_MAX - Y_MIN + 1
    cell = max(1, MAX_PX // max(w, h))
    return {"x_min": X_MIN, "y_min": Y_MIN, "w": w, "h": h, "cell": cell}


class MapView:
    def __init__(self, disp):
        self.disp = disp
        self.cells = [[None] * disp["w"] for _ in range(disp["h"])]
        self.zone_colors = {}

    def create(self):
        d = self.disp
        gw = d["w"] * d["cell"] + 4
        gh = d["h"] * d["cell"] + 4
        gump = API.CreateModernGump(20, 20, gw, gh, False)
        bg = API.CreateGumpColorBox(1.0, "#111111")
        bg.SetRect(0, 0, gw, gh)
        gump.Add(bg)
        unk = rgb_hex(*S_RGB[S_UNKNOWN])
        sz = max(1, d["cell"] - 1)
        for r in range(d["h"]):
            for c in range(d["w"]):
                cell = API.CreateGumpColorBox(1.0, unk)
                cell.SetRect(c * d["cell"] + 2, r * d["cell"] + 2, sz, sz)
                gump.Add(cell)
                self.cells[r][c] = cell
        API.AddGump(gump)

    def _zone_rgb(self, zone_root):
        if zone_root is None:
            return S_RGB[S_GREEN]
        if zone_root not in self.zone_colors:
            idx = len(self.zone_colors) % len(ZONE_PALETTE)
            self.zone_colors[zone_root] = ZONE_PALETTE[idx]
        return self.zone_colors[zone_root]

    def _cell_at(self, tile):
        x, y = tile
        col = x - self.disp["x_min"]
        row = y - self.disp["y_min"]
        if 0 <= row < self.disp["h"] and 0 <= col < self.disp["w"]:
            return self.cells[row][col]
        return None

    def paint(self, tile, kind, maze=None):
        cell = self._cell_at(tile)
        if cell is None:
            return
        if kind == S_GREEN and maze is not None:
            r, g, b = self._zone_rgb(maze.zone_of(tile))
        else:
            r, g, b = S_RGB[kind]
        cell.SetBaseColor(r, g, b, 255)
        if kind != S_UNKNOWN:
            API.MarkTile(tile[0], tile[1], S_MARK[kind])

    def paint_player(self, tile):
        cell = self._cell_at(tile)
        if cell is not None:
            r, g, b = RGB_PLAYER
            cell.SetBaseColor(r, g, b, 255)

    def repaint_tile(self, tile, maze):
        kind = maze.kind(tile)
        self.paint(tile, kind, maze)

    def paint_target(self, tile):
        cell = self._cell_at(tile)
        if cell is not None:
            r, g, b = RGB_TARGET
            cell.SetBaseColor(r, g, b, 255)
        API.MarkTile(tile[0], tile[1], HUE_TARGET)

    def repaint_all(self, maze):
        # Reset palette per riassegnare colori dopo merge di zone
        self.zone_colors = {}
        for tile, kind in maze.state.items():
            self.paint(tile, kind, maze)


# ── Status panel ───────────────────────────────────────────────

class StatusView:
    def __init__(self):
        self.gump = None
        self.lbl_state = None
        self.lbl_queue = None
        self.lbl_zone = None
        self.lbl_counts = None
        self.lbl_stall = None

    def create(self):
        gw, gh = 270, 116
        g = API.CreateModernGump(650, 20, gw, gh, False)
        bg = API.CreateGumpColorBox(0.9, "#0d1117")
        bg.SetRect(0, 0, gw, gh)
        g.Add(bg)
        def mk(text, y, color):
            l = API.CreateGumpTTFLabel(text, 12, color)
            l.SetRect(6, y, gw - 12, 16)
            g.Add(l)
            return l
        self.lbl_state  = mk("Stato: --",   4, "#FFD080")
        self.lbl_queue  = mk("Coda: 0",    22, "#88CCFF")
        self.lbl_zone   = mk("Zona: -",    40, "#88FFAA")
        self.lbl_counts = mk("V0 R0 B0 M0", 58, "#FFFFFF")
        self.lbl_stall  = mk("Stall: 0",   76, "#FF9999")
        API.AddGump(g)
        self.gump = g

    def update(self, fsm_state, queue, maze, counts, stall, player_zone):
        self.lbl_state.SetText("Stato: " + fsm_state)
        self.lbl_queue.SetText("Coda: " + str(len(queue)))
        zstr = "-" if player_zone is None else str(player_zone)[-6:]
        self.lbl_zone.SetText("Zona: " + zstr + "  Portali: " + str(len(maze.portals)))
        self.lbl_counts.SetText("V" + str(counts.get(S_GREEN, 0)) +
                                " R" + str(counts.get(S_RED, 0)) +
                                " B" + str(counts.get(S_BLUE, 0)) +
                                " M" + str(counts.get(S_WALL, 0)))
        self.lbl_stall.SetText("Stall: " + str(stall) + "/" + str(STALL_LIMIT))


# ── Coda di esplorazione ──────────────────────────────────────

def expand_queue(pos, maze, queue):
    x, y = pos
    for dx, dy, _ in DIRS:
        nb = (x+dx, y+dy)
        if X_MIN <= nb[0] <= X_MAX and Y_MIN <= nb[1] <= Y_MAX:
            if maze.kind(nb) == S_UNKNOWN:
                statics = API.GetStaticsAt(nb[0], nb[1])
                if statics and any(s.IsImpassible for s in statics):
                    maze.set(nb, S_WALL)
                else:
                    queue.add(nb)


def pick_target_in_zone(queue, maze, px, py, player_zone):
    """Trova il tile in coda con vicino verde nella zona del player a
       minima distanza Manhattan dal player. Ritorna (tile, approach) o
       (None, None)."""
    best = None
    best_d = INF_PRIO
    best_app = None
    for t in queue:
        x, y = t
        for dx, dy, _ in DIRS:
            nb = (x+dx, y+dy)
            if maze.kind(nb) == S_GREEN and maze.zone_of(nb) == player_zone:
                d = abs(nb[0]-px) + abs(nb[1]-py)
                if d < best_d:
                    best_d = d
                    best = t
                    best_app = nb
    return best, best_app


def zone_demand(queue, maze):
    """zone_id -> n tile in coda con un vicino verde in quella zona."""
    out = {}
    for t in queue:
        x, y = t
        seen_zones = set()
        for dx, dy, _ in DIRS:
            nb = (x+dx, y+dy)
            if maze.kind(nb) == S_GREEN:
                z = maze.zone_of(nb)
                if z is not None and z not in seen_zones:
                    seen_zones.add(z)
                    out[z] = out.get(z, 0) + 1
    return out


# ── UI: scelta modalità + scelta portale ──────────────────────

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
    def on_a(): choice[0] = "auto"
    def on_m(): choice[0] = "manual"
    def on_v(): choice[0] = "verify_blue"
    API.AddControlOnClick(btn_auto,   on_a)
    API.AddControlOnClick(btn_manual, on_m)
    API.AddControlOnClick(btn_vblu,   on_v)
    API.AddGump(g)
    while choice[0] is None:
        API.ProcessCallbacks()
        API.Pause(0.1)
    g.Dispose()
    return choice[0]


def pick_blue_tile(maze):
    blue_tiles = sorted([t for t, k in maze.state.items() if k == S_BLUE])
    if not blue_tiles:
        return None
    ROW_H = 46
    VISIBLE = min(len(blue_tiles), 8)
    LIST_H = VISIBLE * ROW_H
    GUMP_W = 310
    GUMP_H = LIST_H + 70
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
    def make_cb(t):
        def cb(): choice[0] = t
        return cb
    for i, tile in enumerate(blue_tiles):
        tx, ty = tile
        row_y = i * ROW_H
        coord = API.CreateGumpTTFLabel("(" + str(tx) + ", " + str(ty) + ")",
                                       12, "#88CCFF")
        coord.SetRect(5, row_y + 4, 230, 18)
        sa.Add(coord)
        landing = maze.portals.get(tile)
        if landing is not None:
            land_text = "-> (" + str(landing[0]) + ", " + str(landing[1]) + ")"
            color = "#AAFFAA"
        else:
            land_text = "-> ?"
            color = "#888888"
        ll = API.CreateGumpTTFLabel(land_text, 11, color)
        ll.SetRect(5, row_y + 24, 230, 16)
        sa.Add(ll)
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


# ── Modalità manuale: attraversa portale scelto ──────────────

def manual_enter_portal(maze, view):
    selected = pick_blue_tile(maze)
    if selected is None:
        return None
    approach = None
    for dx, dy, _ in DIRS:
        nb = (selected[0]+dx, selected[1]+dy)
        if maze.kind(nb) == S_GREEN:
            approach = nb
            break
    if approach is None or not navigate_intra_zone(approach, maze):
        API.SysMsg("Non riesco ad avvicinarmi al portale.", 33)
        return None
    kind, landed = classify_step(selected[0], selected[1])
    maze.set(selected, kind, landing=landed if kind == S_BLUE else None)
    view.paint(selected, kind, maze)
    if kind != S_BLUE:
        API.SysMsg("Il tile selezionato e' " + S_LABEL[kind] + ".", 33)
        return None
    if maze.kind(landed) == S_UNKNOWN:
        maze.set(landed, S_GREEN)
    view.repaint_all(maze)
    save_maze(maze)
    API.SysMsg("Atterrato a " + str(landed), 88)
    return maze.zone_of(landed)


# ── FSM Explorer ──────────────────────────────────────────────

class Explorer:
    def __init__(self, maze, view, status, mode):
        self.maze = maze
        self.view = view
        self.status = status
        self.mode = mode
        self.queue = set()
        self.counts = {S_GREEN: 0, S_RED: 0, S_BLUE: 0, S_WALL: 0}
        self.skipped = set()
        self.nav_fails = {}
        self.stall = 0
        self.fsm = "EXPLORE"
        self.target_zone = None
        self.last_landing = None
        self.aborted_reason = None

    def is_terminal(self):
        return self.fsm in ("DONE", "ABORT")

    def seed_queue(self):
        for tile, kind in self.maze.state.items():
            if kind == S_GREEN:
                expand_queue(tile, self.maze, self.queue)

    def step(self):
        if self.fsm == "EXPLORE":
            self._step_explore()
        elif self.fsm == "REBOUND":
            self._step_rebound()
        elif self.fsm == "VERIFY_BLUE":
            self._step_verify_blue()

    def _check_stall(self):
        if self.stall >= STALL_LIMIT:
            self.aborted_reason = "Stall " + str(self.stall) + "/" + str(STALL_LIMIT)
            self.fsm = "ABORT"

    def _publish(self, pzone):
        self.status.update(self.fsm, self.queue, self.maze, self.counts,
                           self.stall, pzone)

    def _step_explore(self):
        if not self.queue:
            self.fsm = "DONE"
            return
        px, py = int(API.Player.X), int(API.Player.Y)
        pzone = self.maze.zone_of_player(px, py)
        self._publish(pzone)

        if pzone is None:
            API.SysMsg("Player fuori da zone note -> REBOUND", 33)
            self.fsm = "REBOUND"
            return

        target, approach = pick_target_in_zone(self.queue, self.maze, px, py, pzone)
        if target is None:
            API.SysMsg("Zona corrente esaurita -> REBOUND", 88)
            self.fsm = "REBOUND"
            return

        self.queue.discard(target)
        if self.maze.kind(target) != S_UNKNOWN or target in self.skipped:
            return

        self.view.paint_target(target)

        if not navigate_intra_zone(approach, self.maze):
            fails = self.nav_fails.get(target, 0) + 1
            self.nav_fails[target] = fails
            if fails >= 3:
                self.skipped.add(target)
                API.SysMsg("(" + str(target[0]) + "," + str(target[1]) +
                           ") ignorato.", 900)
            self.stall += 1
            self._check_stall()
            return

        px2, py2 = int(API.Player.X), int(API.Player.Y)
        if max(abs(px2 - target[0]), abs(py2 - target[1])) != 1:
            return
        self.view.paint_player((px2, py2))

        kind, landed = classify_step(target[0], target[1])
        self.maze.set(target, kind, landing=landed if kind == S_BLUE else None)
        self.counts[kind] = self.counts.get(kind, 0) + 1
        self.nav_fails[target] = 0
        self.stall = 0

        API.SysMsg("(" + str(target[0]) + "," + str(target[1]) + ") " +
                   S_LABEL[kind], S_HUE[kind])

        if kind == S_GREEN:
            self.view.paint(target, S_GREEN, self.maze)
            expand_queue(target, self.maze, self.queue)
        elif kind == S_BLUE:
            self.view.paint(target, S_BLUE, self.maze)
            if self.maze.kind(landed) == S_UNKNOWN:
                self.maze.set(landed, S_GREEN)
                self.counts[S_GREEN] = self.counts.get(S_GREEN, 0) + 1
            expand_queue(landed, self.maze, self.queue)
            self.last_landing = landed
            if self.mode == "manual":
                self.target_zone = self.maze.zone_of(landed)
            self.view.repaint_all(self.maze)
        elif kind == S_RED:
            self.view.paint(target, S_RED, self.maze)
        else:
            self.view.paint(target, S_WALL, self.maze)

        total = self.counts[S_GREEN] + self.counts[S_BLUE]
        if total > 0 and total % SAVE_EVERY == 0:
            save_maze(self.maze)
        if target == GOAL and kind == S_GREEN:
            API.SysMsg("=== GOAL RAGGIUNTO! ===", 68)

    def _step_rebound(self):
        demand = zone_demand(self.queue, self.maze)
        if not demand:
            API.SysMsg("Nessuna zona ha tile in coda. FATTO.", 68)
            self.fsm = "DONE"
            return

        # Preferenza: manuale -> target_zone se ha domanda; altrimenti zona con piu domanda
        if self.mode == "manual" and self.target_zone in demand:
            tz = self.target_zone
        else:
            tz = max(demand, key=lambda z: demand[z])

        px, py = int(API.Player.X), int(API.Player.Y)
        cur_zone = self.maze.zone_of_player(px, py)
        self._publish(cur_zone)

        if cur_zone == tz:
            self.fsm = "EXPLORE"
            return

        API.SysMsg("REBOUND -> zona " + str(tz)[-6:] +
                   " (" + str(demand[tz]) + " tile)", 88)

        if cur_zone is None:
            # Non in zona: pathfind a START e ritenta
            API.Pathfind(START[0], START[1], wait=True, timeout=20)
            API.Pause(0.5)
            self.stall += 1
            self._check_stall()
            return

        plan = plan_zone_path(cur_zone, tz, self.maze)
        if not plan:
            API.SysMsg("Nessun piano " + str(cur_zone)[-6:] + " -> " +
                       str(tz)[-6:] + ".", 33)
            self.stall += 1
            self._check_stall()
            return

        for action in plan:
            if action[0] != "portal":
                continue
            _, blue, landing = action
            if not traverse_portal(blue, landing, self.maze):
                API.SysMsg("Portale " + str(blue) + " fallito.", 33)
                self.stall += 1
                self._check_stall()
                return

        self.stall = 0
        self.fsm = "EXPLORE"

    def _step_verify_blue(self):
        blue_tiles = [t for t, k in self.maze.state.items() if k == S_BLUE]
        if not blue_tiles:
            self.fsm = "DONE"
            return
        px, py = int(API.Player.X), int(API.Player.Y)
        blue_tiles.sort(key=lambda t: abs(t[0]-px) + abs(t[1]-py))
        pzone = self.maze.zone_of_player(px, py)
        self._publish(pzone)
        for bt in blue_tiles:
            if self.maze.kind(bt) != S_BLUE:
                continue
            adj_greens = self.maze.green_adj(bt)
            if not adj_greens:
                continue
            if not navigate_intra_zone(adj_greens[0], self.maze):
                continue
            cx, cy = int(API.Player.X), int(API.Player.Y)
            if max(abs(cx-bt[0]), abs(cy-bt[1])) != 1:
                continue
            self.view.paint_target(bt)
            kind, landed = classify_step(bt[0], bt[1])
            self.maze.set(bt, kind, landing=landed if kind == S_BLUE else None)
            if kind == S_BLUE and self.maze.kind(landed) == S_UNKNOWN:
                self.maze.set(landed, S_GREEN)
                expand_queue(landed, self.maze, self.queue)
            self.view.repaint_all(self.maze)
            save_maze(self.maze)
        self.fsm = "DONE"


# ── Bootstrap ─────────────────────────────────────────────────

def reach_start():
    if (int(API.Player.X), int(API.Player.Y)) == START:
        return True
    API.SysMsg("Raggiungo START...", 946)
    API.Pathfind(START[0], START[1], wait=True, timeout=30)
    API.Pause(0.5)
    return (int(API.Player.X), int(API.Player.Y)) == START


def static_prescan(maze):
    API.SysMsg("FASE 1: pre-scansione muri statici...", 88)
    statics = API.GetStaticsInArea(X_MIN, Y_MIN, X_MAX, Y_MAX)
    n = 0
    if statics:
        for s in statics:
            if s.IsImpassible:
                pos = (int(s.X), int(s.Y))
                if maze.kind(pos) == S_UNKNOWN:
                    maze.set(pos, S_WALL)
                    n += 1
    API.SysMsg("Muri pre-classificati: " + str(n), 900)


# ── Main ──────────────────────────────────────────────────────

def main():
    API.SysMsg("=== MAZE SOLVER V2 ===", 88)
    API.Pause(0.5)

    maze = Maze()
    load_maze(maze)
    static_prescan(maze)
    save_maze(maze)

    disp = compute_display(maze)
    view = MapView(disp)
    view.create()
    view.repaint_all(maze)
    API.Pause(0.4)

    if not reach_start():
        API.SysMsg("Impossibile raggiungere START. Stop.", 32)
        return
    if maze.kind(START) != S_GREEN:
        maze.set(START, S_GREEN)
    view.paint(START, S_GREEN, maze)

    mode = ask_mode()
    status = StatusView()
    status.create()

    explorer = Explorer(maze, view, status, mode)

    if mode == "manual":
        tz = manual_enter_portal(maze, view)
        if tz is not None:
            explorer.target_zone = tz
            API.SysMsg("Zona target = " + str(tz)[-6:], 88)
        else:
            API.SysMsg("Modalita' auto.", 33)

    if mode == "verify_blue":
        explorer.fsm = "VERIFY_BLUE"

    explorer.seed_queue()

    prev_player = None
    while not explorer.is_terminal():
        cur_player = (int(API.Player.X), int(API.Player.Y))
        if cur_player != prev_player:
            if prev_player is not None:
                view.repaint_tile(prev_player, maze)
            view.paint_player(cur_player)
            prev_player = cur_player
        explorer.step()
        API.Pause(0.05)

    save_maze(maze)
    if explorer.aborted_reason:
        API.SysMsg("ABORT: " + explorer.aborted_reason, 32)
    else:
        API.SysMsg("=== FINE ===", 68)
    c = explorer.counts
    API.SysMsg("V" + str(c[S_GREEN]) + " R" + str(c[S_RED]) +
               " B" + str(c[S_BLUE]) + " M" + str(c[S_WALL]) +
               " | Portali: " + str(len(maze.portals)) +
               " Zone: " + str(len(set(maze.zone_of(t)
                                       for t, k in maze.state.items()
                                       if k == S_GREEN))), 68)


main()
