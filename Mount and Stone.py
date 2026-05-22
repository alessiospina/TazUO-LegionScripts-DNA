# Autore:      Alessio Spina
# Descrizione: Gestisce mount/dismount della cavalcatura salvata per personaggio
#              su mount_config.json. Se non montato monta la cavalcatura;
#              se già montato smonta e invia "All Stop".
#              Se la mount non è visibile nelle vicinanze, cerca automaticamente
#              tra i mobile vicini ordinati per distanza e aggiorna il serial salvato.

import API
import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(API.ScriptPath), "mount_config.json")

# -----------------------------------------------------------------------
# Config per-personaggio
# -----------------------------------------------------------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(cfg):
    try:
        data = json.dumps(cfg, ensure_ascii=False, indent=2)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(data)
    except Exception as e:
        API.SysMsg(f"[Mount] Errore salvataggio config: {e}")

# -----------------------------------------------------------------------
# Ricerca automatica della mount tra i mobile vicini
# -----------------------------------------------------------------------
def find_nearest_mount(char_name, cfg):
    API.SysMsg("[Mount] Mount non visibile. Ricerca automatica in corso...")
    mobiles = API.GetAllMobiles(distance=10)
    if not mobiles:
        API.SysMsg("[Mount] Nessun mobile trovato nelle vicinanze. Script terminato.")
        return False
    mobiles_sorted = sorted(mobiles, key=lambda m: m.Distance)
    for mob in mobiles_sorted:
        if mob.Serial == API.Player.Serial:
            continue
        API.UseObject(mob.Serial)
        API.Pause(1.5 * 1.0)
        if API.Player.IsMounted:
            cfg[char_name] = int(mob.Serial)
            save_config(cfg)
            API.SysMsg(f"[Mount] Mount trovata e salvata: {hex(int(mob.Serial))}")
            return True
    API.SysMsg("[Mount] Nessuna mount trovata tra i mobile vicini. Script terminato.")
    return False

# -----------------------------------------------------------------------
# Avvio
# -----------------------------------------------------------------------
char_name = API.Player.Name
cfg = load_config()

if char_name not in cfg:
    API.SysMsg(f"[Mount] Nessuna mount per '{char_name}'. Clicca sulla tua mount per salvarla.")
    serial = API.RequestTarget()
    if serial:
        cfg[char_name] = int(serial)
        save_config(cfg)
        API.SysMsg(f"[Mount] Mount salvata per {char_name}: {hex(serial)}")
    else:
        API.SysMsg("[Mount] Nessun target selezionato. Script terminato.")

if char_name in cfg:
    MOUNT_SERIAL = cfg[char_name]
    API.SysMsg(f"[Mount] {char_name} → mount {hex(MOUNT_SERIAL)}")

    # -----------------------------------------------------------------------
    # Logica mount / dismount
    # -----------------------------------------------------------------------
    if not API.Player.IsMounted:
        mount_mob = API.FindMobile(MOUNT_SERIAL)
        if mount_mob is None:
            # Mount non visibile → cerca automaticamente tra i mobile vicini
            find_nearest_mount(char_name, cfg)
        else:
            # Mount visibile → usa la pietra se disponibile, poi monta
            items = API.GetItemsOnGround(3, 0x14E7)
            if items:
                nearest = min(items, key=lambda i: i.Distance)
                API.UseObject(nearest.Serial)
                API.WaitForTarget()
                API.Target(MOUNT_SERIAL)
            API.UseObject(MOUNT_SERIAL)
    else:
        API.Dismount()
        API.Msg("All Stop")

        items = API.GetItemsOnGround(3, 0x14E7)
        if not items:
            API.SysMsg("[Mount] Nessun oggetto trovato nel raggio")
        else:
            nearest = min(items, key=lambda i: i.Distance)
            API.UseObject(nearest.Serial)
            API.WaitForTarget()
            API.Target(MOUNT_SERIAL)
