# Autore:      Alessio Spina
# Descrizione: Contatore EXP. Traccia PX, kill, media, PX/h e kill/h.
#              Salva nome sessione, coordinate e mappa su JSON.

import API
import re
import os
import json
from datetime import datetime

DATA_FILE  = os.path.join(os.path.dirname(API.ScriptPath), "exp_sessions.json")
DT_FMT     = "%Y-%m-%dT%H:%M:%S"
MAP_NAMES  = {0: "Felucca", 1: "Trammel", 2: "Ilshenar", 3: "Malas", 4: "Tokuno", 5: "TerMur"}

# --- Stato sessione ---
session_name   = "Sessione"
session_map    = ""
session_coords = (0, 0, 0)
session_start  = datetime.now()
total_exp      = 0
kill_count     = 0
exp_per_kill   = []
last_journal_time = None

paused           = False
paused_at        = None
total_paused     = 0.0
session_active   = False
waiting_for_name = False
name_dialog      = None
name_textbox     = None

PX_PATTERN = re.compile(r"hai guadagnato\s+([\d\.,]+)\s*px", re.IGNORECASE)

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------
def get_map_name():
    return MAP_NAMES.get(API.GetMap(), "Mappa " + str(API.GetMap()))

def snapshot_location():
    return (API.Player.X, API.Player.Y, API.Player.Z), get_map_name()

def fmt_time(seconds):
    s = max(int(seconds), 0)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"

def fmt_num(n):
    return f"{int(n):,}".replace(",", ".")

def get_elapsed():
    raw = (datetime.now() - session_start).total_seconds()
    cur = (datetime.now() - paused_at).total_seconds() if (paused and paused_at) else 0.0
    return max(raw - total_paused - cur, 0.0)

# -----------------------------------------------------------------------
# Persistenza
# -----------------------------------------------------------------------
def load_sessions():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("sessions", [])
        except Exception:
            pass
    return []

def save_session(start_dt, end_dt, t_exp, k_count, t_paused_sec, kills, name, coords, map_name):
    sessions = load_sessions()
    sessions.append({
        "name":       name,
        "map":        map_name,
        "coords":     list(coords),
        "start":      start_dt.strftime(DT_FMT),
        "end":        end_dt.strftime(DT_FMT),
        "total_exp":  t_exp,
        "kill_count": k_count,
        "paused_sec": int(t_paused_sec),
        "kills": [{"time": ts.strftime("%H:%M:%S"), "exp": xp} for ts, xp in kills]
    })
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"sessions": sessions}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        API.SysMsg(f"ExpCounter: errore salvataggio: {e}")

# -----------------------------------------------------------------------
# Gump principale
# -----------------------------------------------------------------------
W, H  = 300, 284
y0    = 46
ROW   = 28

gump = API.Gumps.CreateModernGump(80, 80, W, H, resizable=False)
gump.SetBorderSize(3)

bg = API.Gumps.CreateGumpColorBox(0.93, "#0C0C14")
bg.SetRect(0, 0, W, H)
gump.Add(bg)

# header background leggermente diverso
hdr_bg = API.Gumps.CreateGumpColorBox(0.40, "#1A1A2E")
hdr_bg.SetRect(0, 0, W, y0 - 4)
gump.Add(hdr_bg)

lbl_name = API.Gumps.CreateGumpTTFLabel("EXP Counter", 17, "#E8C030", "alagard")
lbl_name.SetRect(8, 7, 145, 28)
gump.Add(lbl_name)

lbl_status_live   = API.Gumps.CreateGumpTTFLabel("● LIVE",  13, "#00E87A")
lbl_status_paused = API.Gumps.CreateGumpTTFLabel("● PAUSA", 13, "#FF9900")
lbl_status_live.SetRect(154, 10, 58, 22)
lbl_status_paused.SetRect(154, 10, 58, 22)

btn_storico = API.Gumps.CreateSimpleButton("Storico", 52, 22)
btn_storico.DisplayBorder = True
btn_storico.AlwaysShowBackground = True
btn_storico.SetBackgroundColor(60, 40, 100, 200)
btn_storico.SetRect(214, 10, 52, 22)
gump.Add(btn_storico)

btn_close = API.Gumps.CreateSimpleButton("X", 26, 26)
btn_close.DisplayBorder = True
btn_close.AlwaysShowBackground = True
btn_close.SetBackgroundColor(180, 30, 30, 220)
btn_close.SetRect(W - 30, 6, 26, 26)
gump.Add(btn_close)
lbl_status_paused.SetAlpha(0.0)
gump.Add(lbl_status_live)
gump.Add(lbl_status_paused)

sep_gold = API.Gumps.CreateGumpColorBox(1.0, "#E8C030")
sep_gold.SetRect(0, y0 - 4, W, 2)
gump.Add(sep_gold)

def add_row(label, y, color_val):
    lh = API.Gumps.CreateGumpTTFLabel(label, 13, "#FFFFFF")
    lh.SetRect(12, y, 110, 20)
    gump.Add(lh)
    lv = API.Gumps.CreateGumpTTFLabel("—", 18, color_val)
    lv.SetRect(126, y - 3, W - 136, 24)
    gump.Add(lv)
    return lv

lbl_total = add_row("PX totali",  y0,          "#00E87A")
lbl_kill  = add_row("Kill",       y0 + ROW,    "#00CCFF")
lbl_avg   = add_row("Media/kill", y0 + ROW*2,  "#FF9900")
lbl_time  = add_row("Durata",     y0 + ROW*3,  "#E0E0E0")
lbl_rate  = add_row("PX/ora",     y0 + ROW*4,  "#FF5577")
lbl_kph   = add_row("Kill/ora",   y0 + ROW*5,  "#77AAFF")
lbl_last  = add_row("Ultimo PX",  y0 + ROW*6,  "#DDCC55")

sep_mid = API.Gumps.CreateGumpColorBox(0.6, "#2A2A3A")
sep_mid.SetRect(0, y0 + ROW*7 + 5, W, 2)
gump.Add(sep_mid)

# Bottoni riga 1 — colorati
BW, BH, GAP = 128, 28, 12
x0b   = (W - 2*BW - GAP) // 2
btn_y = y0 + ROW*7 + 10

def make_btn(label, r, g, b, w=BW):
    btn = API.Gumps.CreateSimpleButton(label, w, BH)
    btn.DisplayBorder = True
    btn.AlwaysShowBackground = True
    btn.SetBackgroundColor(r, g, b, 210)
    return btn

btn_toggle = make_btn("Pausa",  180,  90,  15)
btn_nuovo  = make_btn("Nuovo",   30,  90, 190)
btn_toggle.SetRect(x0b,          btn_y, BW, BH)
btn_nuovo.SetRect(x0b + BW+GAP,  btn_y, BW, BH)
btn_toggle.SetAlpha(0.0)
gump.Add(btn_toggle)
gump.Add(btn_nuovo)


# -----------------------------------------------------------------------
# Dialog nome sessione
# -----------------------------------------------------------------------
def show_name_dialog():
    global name_dialog, name_textbox, waiting_for_name
    waiting_for_name = True
    DW, DH = 260, 104

    name_dialog = API.Gumps.CreateModernGump(220, 220, DW, DH, resizable=False)
    name_dialog.SetBorderSize(3)

    dbg = API.Gumps.CreateGumpColorBox(0.93, "#0C0C14")
    dbg.SetRect(0, 0, DW, DH)
    name_dialog.Add(dbg)

    dtitle = API.Gumps.CreateGumpTTFLabel("Nome sessione", 14, "#E8C030", "alagard")
    dtitle.SetRect(10, 6, DW, 22)
    name_dialog.Add(dtitle)

    dsep = API.Gumps.CreateGumpColorBox(1.0, "#E8C030")
    dsep.SetRect(0, 30, DW, 2)
    name_dialog.Add(dsep)

    name_textbox = API.Gumps.CreateGumpTextBox("", DW - 20, 26)
    name_textbox.SetRect(10, 36, DW - 20, 26)
    name_dialog.Add(name_textbox)
    name_textbox.SetFocus()

    dbtn = make_btn("Avvia", 20, 140, 60)
    dbtn.SetRect(DW//2 - 45, 68, 90, 26)
    name_dialog.Add(dbtn)

    def on_avvia():
        global session_name, session_coords, session_map, waiting_for_name, name_dialog
        global session_start, session_active
        session_name = (name_textbox.Text or "").strip() or "Sessione"
        session_coords, session_map = snapshot_location()
        session_start  = datetime.now()
        session_active = True
        btn_toggle.SetAlpha(1.0)
        lbl_name.SetText(session_name)
        waiting_for_name = False
        if name_dialog:
            name_dialog.Dispose()
            name_dialog = None

    API.Gumps.AddControlOnClick(dbtn, lambda: on_avvia())
    API.Gumps.AddGump(name_dialog)

# -----------------------------------------------------------------------
# Callbacks
# -----------------------------------------------------------------------
def on_close():
    if kill_count > 0:
        save_session(session_start, datetime.now(), total_exp, kill_count,
                     total_paused, exp_per_kill, session_name, session_coords, session_map)
        API.SysMsg("ExpCounter: sessione salvata.")
    API.Stop()

API.Gumps.AddControlOnDisposed(gump, on_close)
API.Gumps.AddGump(gump)
API.Gumps.AddControlOnClick(btn_close,   lambda: do_close())
API.Gumps.AddControlOnClick(btn_toggle,  lambda: do_toggle_pausa())
API.Gumps.AddControlOnClick(btn_nuovo,   lambda: do_nuovo())
API.Gumps.AddControlOnClick(btn_storico, lambda: open_storico())

# -----------------------------------------------------------------------
# Azioni
# -----------------------------------------------------------------------
def update_gump():
    if not session_active:
        return
    elapsed = get_elapsed()
    hours   = elapsed / 3600.0 if elapsed > 0 else 0.0001
    avg     = total_exp / kill_count if kill_count > 0 else 0
    lbl_total.SetText(fmt_num(total_exp))
    lbl_kill.SetText(str(kill_count))
    lbl_avg.SetText(fmt_num(avg))
    lbl_time.SetText(fmt_time(elapsed))
    lbl_rate.SetText(fmt_num(total_exp / hours))
    lbl_kph.SetText(f"{kill_count / hours:.1f}")
    if exp_per_kill:
        lbl_last.SetText(fmt_num(exp_per_kill[-1][1]))

def do_close():
    if kill_count > 0:
        save_session(session_start, datetime.now(), total_exp, kill_count,
                     total_paused, exp_per_kill, session_name, session_coords, session_map)
        API.SysMsg("ExpCounter: sessione salvata.")
    API.Stop()

def do_toggle_pausa():
    global paused, paused_at, total_paused
    if not session_active:
        return
    if not paused:
        paused    = True
        paused_at = datetime.now()
        lbl_status_live.SetAlpha(0.0)
        lbl_status_paused.SetAlpha(1.0)
        btn_toggle.SetText("Riprendi")
        btn_toggle.SetBackgroundColor(20, 140, 60, 210)
        API.SysMsg("ExpCounter: in pausa.")
    else:
        if paused_at is not None:
            total_paused += (datetime.now() - paused_at).total_seconds()
        paused    = False
        paused_at = None
        lbl_status_live.SetAlpha(1.0)
        lbl_status_paused.SetAlpha(0.0)
        btn_toggle.SetText("Pausa")
        btn_toggle.SetBackgroundColor(180, 90, 15, 210)
        API.SysMsg("ExpCounter: ripreso.")

def do_nuovo():
    global total_exp, kill_count, exp_per_kill, last_journal_time
    global session_start, paused, paused_at, total_paused, session_active
    if session_active and kill_count > 0:
        save_session(session_start, datetime.now(), total_exp, kill_count,
                     total_paused, exp_per_kill, session_name, session_coords, session_map)
        API.SysMsg("ExpCounter: sessione precedente salvata.")
    total_exp         = 0
    kill_count        = 0
    exp_per_kill      = []
    last_journal_time = None
    paused            = False
    paused_at         = None
    total_paused      = 0.0
    session_active    = False
    btn_toggle.SetAlpha(0.0)
    btn_toggle.SetText("Pausa")
    btn_toggle.SetBackgroundColor(180, 90, 15, 210)
    lbl_status_live.SetAlpha(1.0)
    lbl_status_paused.SetAlpha(0.0)
    show_name_dialog()

def open_storico():
    sessions = load_sessions()
    if not sessions:
        API.SysMsg("ExpCounter: nessuna sessione salvata.")
        return

    SW       = 620
    row_h    = 28
    header_y = 58
    n        = len(sessions)
    scroll_h = min(n * row_h, 350)
    SH       = header_y + scroll_h + 16

    sg = API.Gumps.CreateModernGump(150, 120, SW, SH, resizable=True)
    sg.SetBorderSize(3)

    sbg = API.Gumps.CreateGumpColorBox(0.93, "#0C0C14")
    sbg.SetRect(0, 0, SW, SH)
    sg.Add(sbg)

    hbg = API.Gumps.CreateGumpColorBox(0.40, "#1A1A2E")
    hbg.SetRect(0, 0, SW, 32)
    sg.Add(hbg)

    stitle = API.Gumps.CreateGumpTTFLabel("  Storico Sessioni", 17, "#E8C030", "alagard")
    stitle.SetRect(0, 6, SW, 26)
    sg.Add(stitle)

    sgsep = API.Gumps.CreateGumpColorBox(1.0, "#E8C030")
    sgsep.SetRect(0, 34, SW, 2)
    sg.Add(sgsep)

    cols = [
        ("Nome",   0,  110), ("Mappa", 112,  80), ("Coord", 194, 90),
        ("Data",   286, 90), ("Durata",378,  58), ("PX",    438, 90), ("Kill", 530, 44),
    ]
    for txt, x, w in cols:
        lh = API.Gumps.CreateGumpTTFLabel(txt, 12, "#505060")
        lh.SetRect(x + 4, 38, w, 18)
        sg.Add(lh)

    scroll = API.Gumps.CreateGumpScrollArea(6, header_y, SW - 12, scroll_h)
    sg.Add(scroll)

    for i, s in enumerate(sessions[::-1]):
        y = i * row_h
        try:
            start_dt = datetime.strptime(s["start"], DT_FMT)
            end_dt   = datetime.strptime(s["end"],   DT_FMT)
            t_paused = s.get("paused_sec", 0)
            active   = max((end_dt - start_dt).total_seconds() - t_paused, 0)
            t_exp    = s.get("total_exp", 0)
            k_count  = s.get("kill_count", 0)
            coords   = s.get("coords", [0, 0, 0])
            coord_s  = str(coords[0]) + "," + str(coords[1])

            if i % 2 == 0:
                rb = API.Gumps.CreateGumpColorBox(0.07, "#FFFFFF")
                rb.SetRect(0, y, SW - 12, row_h - 1)
                scroll.Add(rb)

            c = "#CCCCCC" if i % 2 == 0 else "#999999"

            def add(txt, x, w, color=c):
                lb = API.Gumps.CreateGumpTTFLabel(txt, 13, color)
                lb.SetRect(x + 4, y + 6, w, 18)
                scroll.Add(lb)

            add(s.get("name", "—"),                    0,  110)
            add(s.get("map",  "—"),                   112,  80)
            add(coord_s,                               194,  90)
            add(start_dt.strftime("%d/%m %H:%M"),      286,  90)
            add(fmt_time(active),                      378,  58)
            add(fmt_num(t_exp),                        438,  90, "#00E87A")
            add(str(k_count),                          530,  44, "#00CCFF")
        except Exception:
            pass

    API.Gumps.AddGump(sg)

# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------
API.ClearJournal("px")
API.SysMsg("ExpCounter avviato.")

while True:
    API.ProcessCallbacks()
    if waiting_for_name:
        API.Pause(0.1)
        continue

    if session_active and not paused:
        entries = API.GetJournalEntries(5)
        if entries:
            for entry in entries:
                if last_journal_time is not None and entry.Time <= last_journal_time:
                    continue
                if last_journal_time is None or entry.Time > last_journal_time:
                    last_journal_time = entry.Time
                m = PX_PATTERN.search(entry.Text)
                if m:
                    raw = m.group(1).replace(".", "").replace(",", "")
                    try:
                        xp = int(raw)
                        total_exp  += xp
                        kill_count += 1
                        exp_per_kill.append((datetime.now(), xp))
                    except ValueError:
                        pass

    update_gump()
    API.Pause(0.5)
