# Autore:      Alessio Spina
# Descrizione: Toggle arm/disarm di spada a una mano e scudo.
#              Al primo avvio chiede di puntare gli item e salva i seriali
#              con PersistentVar per personaggio. Ad ogni esecuzione successiva
#              arma o disarma a seconda dello stato corrente.

import API

SPADA_KEY = "ArmDisarm_spada"
SCUDO_KEY = "ArmDisarm_scudo"

def msg(text, hue=68):
    API.SysMsg("[" + API.ScriptName + "] " + text, hue)

def setup():
    msg("SETUP: punta la tua SPADA (1 mano)...", 53)
    spada = API.RequestTarget()
    if not spada:
        msg("Setup annullato.", 32)
        return False
    API.Pause(0.5)

    msg("SETUP: punta il tuo SCUDO...", 53)
    scudo = API.RequestTarget()
    if not scudo:
        msg("Setup annullato.", 32)
        return False

    API.SavePersistentVar(SPADA_KEY, str(int(spada)), API.PersistentVar.Char)
    API.SavePersistentVar(SCUDO_KEY, str(int(scudo)), API.PersistentVar.Char)
    msg("Spada e scudo salvati.", 68)
    return True

def main():
    spada_serial = int(API.GetPersistentVar(SPADA_KEY, "0", API.PersistentVar.Char))
    scudo_serial = int(API.GetPersistentVar(SCUDO_KEY, "0", API.PersistentVar.Char))

    if spada_serial == 0 or scudo_serial == 0:
        ok = setup()
        if not ok:
            return
        spada_serial = int(API.GetPersistentVar(SPADA_KEY, "0", API.PersistentVar.Char))
        scudo_serial = int(API.GetPersistentVar(SCUDO_KEY, "0", API.PersistentVar.Char))

    arma = API.FindLayer("OneHanded")
    armato = arma is not None

    if armato:
        scudo_in_mano = API.FindLayer("TwoHanded")
        aggiornato = False
        if arma.Serial != spada_serial:
            API.SavePersistentVar(SPADA_KEY, str(arma.Serial), API.PersistentVar.Char)
            aggiornato = True
        if scudo_in_mano and scudo_in_mano.Serial != scudo_serial:
            API.SavePersistentVar(SCUDO_KEY, str(scudo_in_mano.Serial), API.PersistentVar.Char)
            aggiornato = True
        if aggiornato:
            msg("Seriali aggiornati con gli item in mano.", 53)
        API.ClearRightHand()
        API.Pause(0.5)
        API.ClearLeftHand()
        msg("Disarmato.", 32)
    else:
        if spada_serial == 0 or scudo_serial == 0:
            msg("Seriali non trovati. Riesegui lo script per il setup.", 32)
            return
        items_borsa = [item.Serial for item in API.ItemsInContainer(API.Backpack, True)]

        if spada_serial in items_borsa:
           API.ClearRightHand()
           API.Pause(0.5)
           API.EquipItem(spada_serial)
           msg("Armato: spada.", 68)
        else: 
            msg("Spada non trovata nella borsa.", 32)

        if scudo_serial in items_borsa:
            API.ClearLeftHand()
            API.Pause(0.5)
            API.EquipItem(scudo_serial)
            msg("Armato: scudo.", 68)
        else:
            msg("Scudo non trovato nella borsa.", 32)

main()
