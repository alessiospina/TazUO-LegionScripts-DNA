# Autore:      Alessio Spina
# Descrizione: Script one-shot per impostare o reimpostare la cavalcatura.
#              Apre un target cursor, salva il serial selezionato in
#              mount_config.json per il personaggio corrente.

import API
import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(API.ScriptPath), "mount_config.json")

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
        API.SysMsg(f"[SetMount] Errore salvataggio: {e}")

char_name = API.Player.Name
API.SysMsg(f"[SetMount] Clicca sulla nuova mount per {char_name}...")

serial = API.RequestTarget()
if serial:
    cfg = load_config()
    cfg[char_name] = int(serial)
    save_config(cfg)
    API.SysMsg(f"[SetMount] Mount aggiornata per {char_name}: {hex(int(serial))}")
else:
    API.SysMsg("[SetMount] Nessun target selezionato.")
