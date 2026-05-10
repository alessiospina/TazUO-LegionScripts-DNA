import API
import re


def crea_gump(total_seconds):
    gump = API.CreateGump(True, True, True)
    gump.SetRect(0, 0, 210, 52)
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
        if i <= 20:
            if i == 1:
                API.SysMsg(f"[Invis] Manca {i} secondo")
            else:
                API.SysMsg(f"[Invis] Mancano {i} secondi")
        API.Pause(1.1)

    gump.Dispose()


main()
