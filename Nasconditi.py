# Autore:      Alessio Spina
# Descrizione: Esce dalla war mode (se attiva) e invia il comando .nasconditi.

import API

API.SetWarMode(False)
API.Msg(".nasconditi")