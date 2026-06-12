# Autore:      Alessio Spina
# Descrizione: Attiva war mode, lancia l'incantesimo necromante 35 (evocazione)
#              e seleziona la prima opzione dal gump delle evocazioni.

import API

API.CloseGumps()
API.SetWarMode(True)
API.Msg(".castnecromante  35")
API.Pause(0.2)
gump_id = API.HasGump()
if not gump_id or not API.GumpContains("Evocazioni", gump_id):
    API.SysMsg("gump evocazioni non trovato")
else:
    API.ReplyGump(3, gump_id)
