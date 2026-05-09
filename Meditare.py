# Autore:      Alessio Spina
# Descrizione: Esce dalla war mode (se attiva) e invia il comando .medita.

import API

if API.Player.InWarMode:
    API.SetWarMode(False)

API.Msg(".medita")