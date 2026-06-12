# Autore:      Alessio Spina
# Descrizione: Pannello comandi per AutoFollow.py.
#              Invia ordini al gruppo via .c (follow me, stop follow,
#              mangia in borsa, use item on the ground, slog) e offre
#              controlli locali per il proprio follow.

import API

W = 240
H = 390

gump = API.CreateGump(True, True)
gump.SetRect(100, 100, W, H)

bg = API.CreateGumpColorBox(0.85, "#12122A")
bg.SetRect(0, 0, W, H)
gump.Add(bg)

title = API.CreateGumpTTFLabel("AutoFollow Commands", 14, "#FFD700")
title.SetRect(10, 8, W - 20, 20)
gump.Add(title)

# ── Sezione BROADCAST ──────────────────────────────────────────────────────
lbl_broadcast = API.CreateGumpTTFLabel("[ Ordini al gruppo ]", 11, "#AAAAFF")
lbl_broadcast.SetRect(10, 32, W - 20, 16)
gump.Add(lbl_broadcast)

sep1 = API.CreateGumpColorBox(1.0, "#555577")
sep1.SetRect(10, 50, W - 20, 1)
gump.Add(sep1)

btn_follow_me = API.CreateSimpleButton("Follow Me", W - 20, 28)
btn_follow_me.SetPos(10, 56)
gump.Add(btn_follow_me)

btn_follow_target = API.CreateSimpleButton("Follow Target", W - 20, 28)
btn_follow_target.SetPos(10, 90)
gump.Add(btn_follow_target)

btn_stop = API.CreateSimpleButton("Stop Follow", W - 20, 28)
btn_stop.SetPos(10, 124)
gump.Add(btn_stop)

btn_mangia = API.CreateSimpleButton("Mangia in borsa", W - 20, 28)
btn_mangia.SetPos(10, 158)
gump.Add(btn_mangia)

btn_use_item = API.CreateSimpleButton("Use Item a terra", W - 20, 28)
btn_use_item.SetPos(10, 192)
gump.Add(btn_use_item)

# SlogOut: input password + bottone
lbl_pwd = API.CreateGumpTTFLabel("Password SlogOut:", 11, "#CCCCCC")
lbl_pwd.SetRect(10, 230, W - 20, 16)
gump.Add(lbl_pwd)

txt_pwd = API.CreateGumpTextBox("", W - 80, 24)
txt_pwd.SetRect(10, 248, W - 80, 24)
gump.Add(txt_pwd)

btn_slog = API.CreateSimpleButton("SlogOut", 60, 24)
btn_slog.SetRect(W - 68, 248, 60, 24)
gump.Add(btn_slog)

# ── Sezione LOCALE ─────────────────────────────────────────────────────────
lbl_local = API.CreateGumpTTFLabel("[ Controllo locale ]", 11, "#AAFFAA")
lbl_local.SetRect(10, 285, W - 20, 16)
gump.Add(lbl_local)

sep2 = API.CreateGumpColorBox(1.0, "#557755")
sep2.SetRect(10, 303, W - 20, 1)
gump.Add(sep2)

btn_local_follow = API.CreateSimpleButton("Segui Target (locale)", W - 20, 28)
btn_local_follow.SetPos(10, 309)
gump.Add(btn_local_follow)

btn_cancel_local = API.CreateSimpleButton("Annulla Follow (locale)", W - 20, 28)
btn_cancel_local.SetPos(10, 343)
gump.Add(btn_cancel_local)

API.AddGump(gump)


# ── Callbacks broadcast ─────────────────────────────────────────────────────

def on_follow_me():
    serial = API.Player.Serial
    API.Msg(".c follow me " + hex(serial))
    API.SysMsg(">> [gruppo] follow me " + hex(serial))


def on_follow_target():
    API.SysMsg("Seleziona il target che il gruppo deve seguire...")
    target = API.RequestTarget(10)
    if target:
        serial = int(target)
        API.Msg(".c follow me " + hex(serial))
        API.SysMsg(">> [gruppo] follow me " + hex(serial))
    else:
        API.SysMsg("Nessun target selezionato.")


def on_stop():
    API.Msg(".c stop follow")
    API.SysMsg(">> [gruppo] stop follow")


def on_mangia():
    API.Msg(".c mangia in borsa")
    API.SysMsg(">> [gruppo] mangia in borsa")


def on_use_item():
    API.SysMsg("Seleziona l'oggetto a terra...")
    target = API.RequestTarget(10)
    if target:
        serial = int(target)
        API.Msg(".c use item on the ground " + hex(serial))
        API.SysMsg(">> [gruppo] use item on the ground " + hex(serial))
    else:
        API.SysMsg("Nessun oggetto selezionato.")


def on_slog():
    pwd = txt_pwd.Text if txt_pwd.Text else ""
    if not pwd:
        API.SysMsg("Inserisci la password prima di fare SlogOut.")
        return
    API.Msg(".c slog " + pwd)
    API.SysMsg(">> [gruppo] slog ***")


# ── Callbacks locali ────────────────────────────────────────────────────────

def on_local_follow():
    API.SysMsg("Seleziona il target da seguire localmente...")
    target = API.RequestTarget(10)
    if target:
        serial = int(target)
        API.CancelAutoFollow()
        API.AutoFollow(serial)
        API.SysMsg("Follow locale avviato: " + hex(serial))
    else:
        API.SysMsg("Nessun target selezionato.")


def on_cancel_local():
    API.CancelAutoFollow()
    API.SysMsg("Follow locale annullato.")


API.AddControlOnClick(btn_follow_me, on_follow_me)
API.AddControlOnClick(btn_follow_target, on_follow_target)
API.AddControlOnClick(btn_stop, on_stop)
API.AddControlOnClick(btn_mangia, on_mangia)
API.AddControlOnClick(btn_use_item, on_use_item)
API.AddControlOnClick(btn_slog, on_slog)
API.AddControlOnClick(btn_local_follow, on_local_follow)
API.AddControlOnClick(btn_cancel_local, on_cancel_local)

API.AddControlOnDisposed(gump, API.Stop)

while True:
    API.ProcessCallbacks()
    API.Pause(0.1)
