# Autore:      Alessio Spina
# Descrizione: Entra in war mode, lancia il buff Bless del mago (.castmago 5)
#              e poi due spell necromante (21 e 27) in sequenza,
#              aspettando la fine di ogni recitazione prima di procedere.

import API

if not API.Player.InWarMode:
    API.SetWarMode(True)
    API.Pause(0.5)

API.ClearJournal("RECITAZIONE TERMINATA")
API.Msg(".castmago 5")

while not API.InJournal("RECITAZIONE TERMINATA"):
    API.Pause(0.1)
API.ClearJournal("RECITAZIONE TERMINATA")
API.Pause(1.5)

API.Msg(".castnecromante 21")

while not API.InJournal("RECITAZIONE TERMINATA"):
    API.Pause(0.1)
API.ClearJournal("RECITAZIONE TERMINATA")
API.Pause(1.5)

API.Msg(".castnecromante 27")
