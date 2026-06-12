# Autore:      Alessio Spina
# Descrizione: Segna la tile corrente del giocatore con hue verde (percorso confermato).

import API
HUE_GOOD = 68   # verde: percorso confermato

API.MarkTile(API.Player.X, API.Player.Y, HUE_GOOD)