# Autore:      Alessio Spina
# Descrizione: Contatore EXP in-game con gump grafico. Traccia PX totali,
#              kill, media per kill, PX/ora e kill/ora per sessione.
#              Supporta pausa, reset e storico sessioni salvato su JSON.

import API
import re
import os
import json
from datetime import datetime

# --- Percorso file dati ---
DATA_FILE = os.path.join(os.path.dirname(API.ScriptPath), "exp_sessions.json")

# --- Stato sessione corrente ---
session_start     = datetime.now()
total_exp         = 0
kill_count        = 0
exp_per_kill      = []
last_journal_time = None

# --- Stato pausa ---
paused       = False
paused_at    = None
total_paused = 0.0   # secondi totali trascorsi in pausa

# --- Regex PX dal journal ---
PX_PATTERN = re.compile(r"hai guadagnato\s+([\d\.,]+)\s*px", re.IGNORECASE)

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

def save_session(start_dt, end_dt, t_exp, k_count, t_paused_sec, kills):
    sessions = load_sessions()
    sessions.append({
        "start":      start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "end":        end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
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
# Costruzione del gump principale
# -----------------------------------------------------------------------
W, H = 320, 340

gump = API.Gumps.CreateModernGump(100, 100, W, H, resizable=False)

# sfondo
bg = API.Gumps.CreateGumpColorBox(0.82, "#0D0D0D")
bg.SetRect(0, 0, W, H)
gump.Add(bg)

# titolo
title = API.Gumps.CreateGumpTTFLabel("  EXP Counter", 16, "#FFD700", "alagard")
title.SetRect(0, 8, W - 70, 24)
gump.Add(title)

# indicatore stato LIVE (verde) / PAUSA (giallo) — sovrapposti, uno alla volta visibile
lbl_status_live = API.Gumps.CreateGumpTTFLabel("● LIVE", 11, "#00FF99")
lbl_status_live.SetRect(W - 68, 10, 64, 18)
gump.Add(lbl_status_live)

lbl_status_paused = API.Gumps.CreateGumpTTFLabel("● PAUSA", 11, "#FFAA00")
lbl_status_paused.SetRect(W - 68, 10, 64, 18)
lbl_status_paused.SetAlpha(0.0)
gump.Add(lbl_status_paused)

# separatore titolo
sep_top = API.Gumps.CreateGumpColorBox(0.9, "#FFD700")
sep_top.SetRect(8, 34, W - 16, 2)
gump.Add(sep_top)

# --- statistiche ---
lbl_total_head = API.Gumps.CreateGumpTTFLabel("PX Totali:", 13, "#AAAAAA")
lbl_total_head.SetRect(12, 44, 120, 20)
gump.Add(lbl_total_head)

lbl_total = API.Gumps.CreateGumpTTFLabel("0", 13, "#00FF99")
lbl_total.SetRect(140, 44, 170, 20)
gump.Add(lbl_total)

lbl_kill_head = API.Gumps.CreateGumpTTFLabel("Mostri uccisi:", 13, "#AAAAAA")
lbl_kill_head.SetRect(12, 66, 120, 20)
gump.Add(lbl_kill_head)

lbl_kill = API.Gumps.CreateGumpTTFLabel("0", 13, "#00CFFF")
lbl_kill.SetRect(140, 66, 170, 20)
gump.Add(lbl_kill)

lbl_avg_head = API.Gumps.CreateGumpTTFLabel("Media / kill:", 13, "#AAAAAA")
lbl_avg_head.SetRect(12, 88, 120, 20)
gump.Add(lbl_avg_head)

lbl_avg = API.Gumps.CreateGumpTTFLabel("0", 13, "#FFAA00")
lbl_avg.SetRect(140, 88, 170, 20)
gump.Add(lbl_avg)

lbl_time_head = API.Gumps.CreateGumpTTFLabel("Durata:", 13, "#AAAAAA")
lbl_time_head.SetRect(12, 110, 120, 20)
gump.Add(lbl_time_head)

lbl_time = API.Gumps.CreateGumpTTFLabel("00:00:00", 13, "#FFFFFF")
lbl_time.SetRect(140, 110, 170, 20)
gump.Add(lbl_time)

lbl_rate_head = API.Gumps.CreateGumpTTFLabel("PX / ora:", 13, "#AAAAAA")
lbl_rate_head.SetRect(12, 132, 120, 20)
gump.Add(lbl_rate_head)

lbl_rate = API.Gumps.CreateGumpTTFLabel("0", 13, "#FF6688")
lbl_rate.SetRect(140, 132, 170, 20)
gump.Add(lbl_rate)

lbl_kph_head = API.Gumps.CreateGumpTTFLabel("Kill / ora:", 13, "#AAAAAA")
lbl_kph_head.SetRect(12, 154, 120, 20)
gump.Add(lbl_kph_head)

lbl_kph = API.Gumps.CreateGumpTTFLabel("0", 13, "#88CCFF")
lbl_kph.SetRect(140, 154, 170, 20)
gump.Add(lbl_kph)

lbl_last_head = API.Gumps.CreateGumpTTFLabel("Ultimo PX:", 13, "#AAAAAA")
lbl_last_head.SetRect(12, 176, 120, 20)
gump.Add(lbl_last_head)

lbl_last = API.Gumps.CreateGumpTTFLabel("-", 13, "#EEDD88")
lbl_last.SetRect(140, 176, 170, 20)
gump.Add(lbl_last)

# separatore
sep_mid = API.Gumps.CreateGumpColorBox(0.6, "#555555")
sep_mid.SetRect(8, 202, W - 16, 1)
gump.Add(sep_mid)

# ultimi guadagni in scroll area
lbl_recent_head = API.Gumps.CreateGumpTTFLabel("  Ultimi guadagni:", 11, "#888888")
lbl_recent_head.SetRect(8, 208, W - 16, 16)
gump.Add(lbl_recent_head)

sa = API.Gumps.CreateGumpScrollArea(8, 226, W - 16, 58)
gump.Add(sa)

recent_labels = []
for i in range(8):
    rl = API.Gumps.CreateGumpTTFLabel("", 11, "#CCCCCC")
    rl.SetRect(2, i * 16, W - 24, 16)
    sa.Add(rl)
    recent_labels.append(rl)

# separatore pulsanti
sep_btn = API.Gumps.CreateGumpColorBox(0.6, "#555555")
sep_btn.SetRect(8, 284, W - 16, 1)
gump.Add(sep_btn)

# --- Riga 1: [Pausa] [Riprendi] [Nuovo] ---
BW = 88
BH = 20
GAP = 4
# 3 bottoni centrati: margine sinistro = (320 - 3*88 - 2*4) / 2 = 24
x0 = (W - 3 * BW - 2 * GAP) // 2

btn_pausa = API.Gumps.CreateSimpleButton("Pausa", BW, BH)
btn_pausa.SetRect(x0, 289, BW, BH)
gump.Add(btn_pausa)

btn_riprendi = API.Gumps.CreateSimpleButton("Riprendi", BW, BH)
btn_riprendi.SetRect(x0 + BW + GAP, 289, BW, BH)
gump.Add(btn_riprendi)

btn_nuovo = API.Gumps.CreateSimpleButton("Nuovo", BW, BH)
btn_nuovo.SetRect(x0 + (BW + GAP) * 2, 289, BW, BH)
gump.Add(btn_nuovo)

# separatore riga 2
sep_btn2 = API.Gumps.CreateGumpColorBox(0.6, "#555555")
sep_btn2.SetRect(8, 313, W - 16, 1)
gump.Add(sep_btn2)

# --- Riga 2: [Storico] centrato ---
btn_storico = API.Gumps.CreateSimpleButton("Storico sessioni", 112, BH)
btn_storico.SetRect(W // 2 - 56, 317, 112, BH)
gump.Add(btn_storico)

# -----------------------------------------------------------------------
# Callback chiusura → salva sessione e stop script
# -----------------------------------------------------------------------
def on_close():
    if kill_count > 0:
        save_session(session_start, datetime.now(), total_exp, kill_count, total_paused, exp_per_kill)
        API.SysMsg("ExpCounter: sessione salvata.")
    API.Stop()

API.Gumps.AddControlOnDisposed(gump, on_close)
API.Gumps.AddGump(gump)

# registra callback click (ApiUiNiceButton non ha HasBeenClicked)
API.Gumps.AddControlOnClick(btn_pausa,    lambda: do_pausa())
API.Gumps.AddControlOnClick(btn_riprendi, lambda: do_riprendi())
API.Gumps.AddControlOnClick(btn_nuovo,    lambda: do_nuovo())
API.Gumps.AddControlOnClick(btn_storico,  lambda: open_storico())

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------
def fmt_time(seconds):
    s = max(int(seconds), 0)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"

def fmt_num(n):
    return f"{int(n):,}".replace(",", ".")

def get_elapsed():
    raw = (datetime.now() - session_start).total_seconds()
    cur_pause = (datetime.now() - paused_at).total_seconds() if (paused and paused_at) else 0.0
    return max(raw - total_paused - cur_pause, 0.0)

def update_gump():
    elapsed = get_elapsed()
    hours   = elapsed / 3600.0 if elapsed > 0 else 0.0001

    avg  = total_exp / kill_count if kill_count > 0 else 0
    rate = total_exp / hours
    kph  = kill_count / hours

    lbl_total.SetText(fmt_num(total_exp))
    lbl_kill.SetText(str(kill_count))
    lbl_avg.SetText(fmt_num(avg))
    lbl_time.SetText(fmt_time(elapsed))
    lbl_rate.SetText(fmt_num(rate))
    lbl_kph.SetText(f"{kph:.1f}")
    if exp_per_kill:
        lbl_last.SetText(fmt_num(exp_per_kill[-1][1]))

    recent = exp_per_kill[-8:][::-1]
    for i, rl in enumerate(recent_labels):
        if i < len(recent):
            ts, xp = recent[i]
            rl.SetText(f"  {ts.strftime('%H:%M:%S')}  +{fmt_num(xp)} px")
        else:
            rl.SetText("")

def do_pausa():
    global paused, paused_at
    if paused:
        return
    paused    = True
    paused_at = datetime.now()
    lbl_status_live.SetAlpha(0.0)
    lbl_status_paused.SetAlpha(1.0)
    API.SysMsg("ExpCounter: in pausa.")

def do_riprendi():
    global paused, paused_at, total_paused
    if not paused:
        return
    if paused_at is not None:
        total_paused += (datetime.now() - paused_at).total_seconds()
    paused    = False
    paused_at = None
    lbl_status_live.SetAlpha(1.0)
    lbl_status_paused.SetAlpha(0.0)
    API.SysMsg("ExpCounter: ripreso.")

def do_nuovo():
    global total_exp, kill_count, exp_per_kill, last_journal_time
    global session_start, paused, paused_at, total_paused
    if kill_count > 0:
        save_session(session_start, datetime.now(), total_exp, kill_count, total_paused, exp_per_kill)
        API.SysMsg("ExpCounter: sessione precedente salvata.")
    total_exp         = 0
    kill_count        = 0
    exp_per_kill      = []
    last_journal_time = None
    session_start     = datetime.now()
    paused            = False
    paused_at         = None
    total_paused      = 0.0
    lbl_status_live.SetAlpha(1.0)
    lbl_status_paused.SetAlpha(0.0)
    update_gump()
    API.SysMsg("ExpCounter: nuovo contatore avviato.")

def open_storico():
    sessions = load_sessions()
    if not sessions:
        API.SysMsg("ExpCounter: nessuna sessione salvata.")
        return

    SW = 420
    row_h = 20
    header_y = 52
    n = len(sessions)
    content_h = n * row_h
    scroll_h = min(content_h, 260)
    SH = header_y + scroll_h + 12

    sg = API.Gumps.CreateModernGump(160, 130, SW, SH, resizable=True)

    sbg = API.Gumps.CreateGumpColorBox(0.88, "#080808")
    sbg.SetRect(0, 0, SW, SH)
    sg.Add(sbg)

    stitle = API.Gumps.CreateGumpTTFLabel("  Storico Sessioni", 15, "#FFD700", "alagard")
    stitle.SetRect(0, 8, SW, 20)
    sg.Add(stitle)

    ssep = API.Gumps.CreateGumpColorBox(0.9, "#FFD700")
    ssep.SetRect(8, 30, SW - 16, 2)
    sg.Add(ssep)

    # intestazioni colonne
    col = [("Data / ora", 0, 95), ("Durata", 97, 58), ("PX totali", 157, 80), ("Kill", 240, 38), ("PX / ora", 281, 80), ("in pausa", 363, 55)]
    for txt, x, w in col:
        lh = API.Gumps.CreateGumpTTFLabel(txt, 10, "#777777")
        lh.SetRect(x, 34, w, 16)
        sg.Add(lh)

    scroll = API.Gumps.CreateGumpScrollArea(8, header_y, SW - 16, scroll_h)
    sg.Add(scroll)

    for i, s in enumerate(reversed(sessions)):
        y = i * row_h
        try:
            start_dt  = datetime.strptime(s["start"], "%Y-%m-%dT%H:%M:%S")
            end_dt    = datetime.strptime(s["end"],   "%Y-%m-%dT%H:%M:%S")
            t_paused  = s.get("paused_sec", 0)
            raw_dur   = (end_dt - start_dt).total_seconds()
            active    = max(raw_dur - t_paused, 0)
            hours     = active / 3600.0 if active > 0 else 0.0001
            t_exp     = s.get("total_exp", 0)
            k_count   = s.get("kill_count", 0)

            date_str  = start_dt.strftime("%d/%m/%y %H:%M")
            dur_str   = fmt_time(active)
            exp_str   = fmt_num(t_exp)
            pxh_str   = fmt_num(t_exp / hours)
            pau_str   = fmt_time(t_paused)

            # riga alternata
            if i % 2 == 0:
                row_bg = API.Gumps.CreateGumpColorBox(0.12, "#FFFFFF")
                row_bg.SetRect(0, y, SW - 16, row_h - 1)
                scroll.Add(row_bg)

            c = "#CCCCCC" if i % 2 == 0 else "#999999"

            def add(txt, x, w, color=c):
                lb = API.Gumps.CreateGumpTTFLabel(txt, 10, color)
                lb.SetRect(x, y + 3, w, 16)
                scroll.Add(lb)

            add(date_str, 0,   95)
            add(dur_str,  97,  58)
            add(exp_str,  157, 80,  "#00FF99")
            add(str(k_count), 240, 38, "#00CFFF")
            add(pxh_str,  281, 80,  "#FF6688")
            add(pau_str,  363, 55,  "#888888")

        except Exception:
            pass

    API.Gumps.AddGump(sg)

# -----------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------
API.ClearJournal("px")
API.SysMsg("ExpCounter avviato. Chiudi il gump per fermare.")

while True:
    # leggi journal solo se non in pausa
    if not paused:
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
    API.ProcessCallbacks()
    API.Pause(0.5)
