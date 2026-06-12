# Autore:      Alessio Spina
# Descrizione: Cerca una sfera del mana nello zaino e la usa; se non presente
#              lancia l'incantesimo necromante 51 per crearne una.

import API

sfera = API.FindType(0x0E2D, API.Backpack)

if sfera is None:
    API.Msg(".castnecromante 51")
else:
    API.UseObject(sfera)
