# Autore:      Alessio Spina
# Descrizione: Invia .segui_tracce 1 ogni 6 secondi.
#              Se trova un gump con la scritta "Seguire Tracce" invia .c TRACCO GENTE e termina.

import API

def has_tracking_gump():
    gumps = API.GetAllGumps()
    if not gumps:
        return False
    for gump in gumps:
        text = gump.PacketGumpText
        if text and "Seguire Tracce" in text:
            return True
    return False

def main():
    API.SysMsg(f"[{API.ScriptName}] Avviato.")
    while True:
        API.Msg(".segui_tracce 1")
        API.Pause(1)
        if has_tracking_gump():
            API.SysMsg(f"[{API.ScriptName}] Player Individuati")
            API.Msg(".c TRACCO GENTE")
            API.SetWarMode(False)
            API.ReplyGump(1)
            return        
        API.Pause(7)

main()
