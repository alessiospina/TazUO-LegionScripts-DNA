# Autore:      Alessio Spina
# Descrizione: Entra in war mode e lancia In Por (.castmago 20).
#              Se non ha le Perle Nere in borsa, cerca il sacchetto con
#              "Perle Nere" nel nome e lo apre. Se non lo trova, avvisa e termina.

import API


class InPor:

    G_SACCHETTO = 0x0E76
    G_SACCHETTO_NAME = "perle nere"
    G_PERLE_NERE = 0x0F7A
    CAST = ".castmago 20"

    @staticmethod
    def have_reagente(g_reag):
        reag = API.FindTypeAll(g_reag, API.Backpack)
        return len(reag) > 0

    @staticmethod
    def find_and_useobject(g_backpack, g_object, g_filter_name):
        objs = API.FindTypeAll(g_object, g_backpack)
        for obj in objs:
            #API.SysMsg(f"[{API.ScriptName}] OBJ: {obj}", 35)
            API.ClickObject(obj.Serial)
            API.Pause(0.5)           
            if g_filter_name in obj.Name:
                API.UseObject(obj.Serial)
                API.SysMsg(f"[{API.ScriptName}] Aperto Item: {g_filter_name}", 33)
                return True
        API.SysMsg(f"[{API.ScriptName}] Nessuna item: {g_filter_name} trovato!", 33)
        return False

    @staticmethod
    def launch():
        if not InPor.have_reagente(InPor.G_PERLE_NERE):
            API.SysMsg(f"[{API.ScriptName}] Nessun item trovato, controllo se ne hai altri...", 33)
            if not InPor.find_and_useobject(API.Backpack, InPor.G_SACCHETTO, InPor.G_SACCHETTO_NAME):               
                return
        if not API.Player.InWarMode:
            API.SetWarMode(True)
        API.ClearJournal()
        API.Msg(InPor.CAST)


InPor.launch()
