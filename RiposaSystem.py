# Autore:      Alessio Spina
# Descrizione: Automatizza il ciclo di riposo per il bonus EXP.
#              Entra in riposo (.riposa), attende la maturazione del bonus
#              con una barra di countdown grafica, poi esce dal riposo
#              e si disconnette non appena il bonus diventa disponibile.

import API
import re

def countdown(secondi):
    gump = API.CreateGump(True, True, True)
    gump.SetRect(0, 0, 360, 90)
    gump.CenterXInViewPort()
    gump.CenterYInViewPort()

    bg = API.CreateGumpColorBox(0.85, "#0D1B2A")
    bg.SetRect(0, 0, 360, 90)
    gump.Add(bg)

    titolo = API.CreateGumpTTFLabel("RiposaSystem - Bonus EXP", 13, "#7EC8E3", "alagard")
    titolo.SetRect(10, 6, 340, 18)
    gump.Add(titolo)

    label = API.CreateGumpTTFLabel(f"Attesa: {secondi}s", 13, "#FFFFFF", "alagard")
    label.SetRect(10, 30, 340, 18)
    gump.Add(label)

    pb = API.CreateGumpSimpleProgressBar(330, 18, "#2E4057", "#1B998B", secondi, secondi)
    pb.SetRect(10, 62, 330, 18)
    gump.Add(pb)

    API.AddGump(gump)

    remaining = secondi
    while remaining > 0:
        label.SetText(f"Attesa: {remaining}s")
        pb.SetProgress(remaining, secondi)
        API.Pause(1)
        remaining -= 1

    gump.Dispose()


def main():
    API.SysMsg("RiposaSystem avviato.")
    API.ClearJournal()

    if not API.Player.IsYellowHits:
        API.Msg(".riposa")
        API.SysMsg("Comando .riposa inviato, attendo conferma dal journal...")

        while not API.InJournal("Invulnerabilita' ON"):
            API.Pause(1)

        API.SysMsg("Riposo iniziato, attendo 1 minuto...")
        countdown(60)
    else:
        API.SysMsg("Gia' stonato, salto al controllo bonus...")

    while True:
        API.Msg(".bonus_exp")
        API.Pause(2)

        if API.InJournal("Il bonus e' attivo. Scrivi .attiva_bonus_exp per attivarlo!"):
            API.SysMsg("Bonus ottenuto! Esco dal riposo...")
            API.Msg(".riposa")
            while not API.InJournal("Invulnerabilita' OFF"):
                API.Pause(1)
            API.Pause(4)
            API.Msg("Ahhhh che bella riposata")
            API.Pause(2)
            API.Msg("Ora sono pronto per uccidere tanti mostri")
            API.Pause(2)
            API.EmoteMsg("Sviene...")
            API.Pause(2)
            API.Logout()
            API.Stop()
            break

        entries = API.GetJournalEntries(10)
        wait_seconds = None

        if entries:
            for entry in entries[::-1]:
                match = re.search(r"Devi riposare altri (\d+) minut", entry.Text, re.IGNORECASE)
                if match:
                    minuti_str = match.group(1)
                    minuti = 0
                    for c in minuti_str:
                        minuti = minuti * 10 + "0123456789".index(c)
                    wait_seconds = minuti * 60
                    API.SysMsg(f"Aspetto ancora {minuti} min ({wait_seconds}s).")
                    break

        countdown(wait_seconds if wait_seconds else 60)


main()
