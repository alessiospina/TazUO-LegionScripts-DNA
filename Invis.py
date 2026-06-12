# Autore:      Alessio Spina
# Descrizione: Lancia l'incantesimo invisibilita' (.castmago 17) e mostra un countdown
#              grafico con barra di progresso. La durata e' calcolata dal livello del
#              personaggio. Lo script si ferma se il personaggio torna visibile.

import API
import re
import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(API.ScriptPath), "invis_config.json")


def carica_pos():
    try:
        with open(CONFIG_FILE, "r") as f:
            d = json.load(f)
            return d.get("gump_x"), d.get("gump_y")
    except Exception:
        return None, None


def salva_pos(x, y):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"gump_x": x, "gump_y": y}, f)
    except Exception:
        pass


def crea_gump(total_seconds):
    gump_x, gump_y = carica_pos()

    gump = API.CreateGump(True, True, True)
    gump.SetRect(0, 0, 210, 52)

    if gump_x is not None and gump_y is not None:
        gump.SetPos(gump_x, gump_y)
    else:
        gump.CenterXInViewPort()
        gump.CenterYInViewPort()

    bg = API.CreateGumpColorBox(0.85, "#0D1B2A")
    bg.SetRect(0, 0, 210, 52)
    gump.Add(bg)

    titolo = API.CreateGumpTTFLabel("Invis", 12, "#7EC8E3", "alagard")
    titolo.SetRect(10, 5, 190, 15)
    gump.Add(titolo)

    label = API.CreateGumpTTFLabel(f"{total_seconds}s", 12, "#FFFFFF", "alagard")
    label.SetRect(10, 22, 190, 15)
    gump.Add(label)

    pb = API.CreateGumpSimpleProgressBar(180, 10, "#2E4057", "#1B998B", total_seconds, total_seconds)
    pb.SetRect(10, 38, 180, 10)
    gump.Add(pb)

    API.AddGump(gump)
    return gump, label, pb


def main():
    if not API.Player.InWarMode:
        API.SetWarMode(True)

    API.ClearJournal()
    API.Msg(".pxcap")
    API.Pause(1.5)

    livello = 0
    entries = API.GetJournalEntries(5)
    if entries:
        for entry in entries:
            match = re.search(r"Livello (\d+)", entry.Text)
            if match:
                livello = int(match.group(1))
                break

    total_seconds = livello * 2 + 1
    API.SysMsg(f"[Invis] Livello {livello}, Durata: {total_seconds}s")

    API.ClearJournal()
    API.Msg(".castmago 17")

    while not API.InJournal("RECITAZIONE TERMINATA"):
        API.Pause(0.1)

    API.SysMsg("[Invis] Timer partito")

    gump, label, pb = crea_gump(total_seconds)

    for i in range(total_seconds, 0, -1):
        label.SetText(f"{i}s")
        pb.SetProgress(i, total_seconds)
        salva_pos(gump.GetX(), gump.GetY())
        if i <= 20:
            if i == 1:
                API.SysMsg(f"[Invis] Manca {i} secondo")
            else:
                API.SysMsg(f"[Invis] Mancano {i} secondi")
        API.Pause(1.1)
        if not API.Player.IsHidden:
            API.SysMsg("[Invis] Personaggio visibile, script fermato")
            salva_pos(gump.GetX(), gump.GetY())
            gump.Dispose()
            API.Stop()
            return

    salva_pos(gump.GetX(), gump.GetY())
    gump.Dispose()


main()
