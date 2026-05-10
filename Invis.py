import API
import re

if not API.Player.InWarMode:
    API.SetWarMode(True)

# Leggi il livello da .pxcap per calcolare la durata dell'invis
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
API.SysMsg(f"[Invis.py] Livello {livello}, Durata Invis: {total_seconds}s")

# Lancia invis
API.ClearJournal()
API.Msg(".castmago 17")

# Aspetta che la recitazione termini prima di far partire il timer
while not API.InJournal("RECITAZIONE TERMINATA"):
    API.Pause(0.1)

API.SysMsg("[Invis.py] Timer Partito")

# Gump countdown
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

for i in range(total_seconds, 0, -1):
    label.SetText(f"{i}s")
    pb.SetProgress(i, total_seconds)
    if i <= 20:
        if i == 1:
            API.SysMsg(f"[Invis.py] Manca {i} Secondo")
        else:
            API.SysMsg(f"[Invis.py] Mancano {i} Secondi")
    API.Pause(1.1)

gump.Dispose()
