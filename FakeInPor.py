# Autore:      Alessio Spina
# Descrizione: Loop infinito che invia il comando ".parla_runico IN POR" ogni 5 secondi.

import API

while True:
    API.Pause(5.0)
    API.Msg(".parla_runico IN POR")