# Autore:      Alessio Spina
# Descrizione: Segue automaticamente un giocatore che invia "follow me <serial>" in chat.
#              Supporta comandi da chiunque: follow, stop follow, slog <password>,
#              mangia in borsa, use item on the ground <serial>.
#              Se il target è entro arrive_distance si nasconde invece di seguire.

import API
import re

FOOD_SERIALS = [
    # inserisci qui i seriali del cibo, es: 0x12345678
    0x09EA, # pomodori
    0x0C66, # patate
    0x0EEF, # piselli
]


class Command:
    name    = ""
    persist = True

    def detect(self, text):
        raise NotImplementedError

    def action(self, match, entry):
        raise NotImplementedError


class FollowCommand(Command):
    name   = "Follow"
    _regex = re.compile(r'follow\s+me[\s:]+\(?(?:0x)?([0-9a-fA-F]+)\)?', re.IGNORECASE)

    def __init__(self, arrive_distance=5):
        self.arrive_distance = arrive_distance

    def detect(self, text):
        return self._regex.search(text)

    def action(self, match, entry):
        serial = int(match.group(1), 16)
        mob    = API.FindMobile(serial)
        if mob and mob.Distance <= self.arrive_distance:
            if not API.Player.IsHidden:
                API.SetWarMode(False)
                API.Msg(".nasconditi")
        else:
            API.AutoFollow(serial)
            API.SysMsg("[AutoFollow] Seguo " + (entry.Name or "?") + " (" + hex(serial) + ")")


class StopCommand(Command):
    name    = "Stop"
    persist = False
    _regex  = re.compile(r'stop follow', re.IGNORECASE)

    def detect(self, text):
        return self._regex.search(text)

    def action(self, match, entry):
        API.AutoFollow(0)
        API.SysMsg("[AutoFollow] Follow fermato.")


class SlogOutCommand(Command):
    name    = "SlogOut"
    persist = False
    _regex  = re.compile(r'slog\s+(\S+)', re.IGNORECASE)

    def __init__(self, password):
        self.password = password

    def detect(self, text):
        return self._regex.search(text)

    def action(self, match, entry):
        if match.group(1) == self.password:
            API.SysMsg("[AutoFollow] Password corretta. Logout in corso.")
            API.Logout()
        else:
            API.SysMsg("[AutoFollow] Password errata.")
            API.Msg(".c Password errata.")


class EatFromBagCommand(Command):
    name    = "EatFromBag"
    persist = False
    _regex  = re.compile(r'mangia in borsa', re.IGNORECASE)

    def __init__(self, food_serials):
        self.food_serials = food_serials

    def detect(self, text):
        return self._regex.search(text)

    def action(self, match, entry):
        for serial in self.food_serials:
            items = API.FindTypeAll(serial, API.Backpack)
            for item in items:
                API.ClickObject(item)
                API.Pause(0.5)
                API.UseObject(item.Serial)
                API.SysMsg("[AutoFollow] Sto mangiando.")
                API.Msg(".c Sto mangiando.")
                return
        API.SysMsg("[AutoFollow] Nessun cibo trovato in borsa.")
        API.Msg(".c Nessun cibo trovato in borsa.")


class UseItemOnGroundCommand(Command):
    name    = "UseItemOnGround"
    persist = False
    _regex  = re.compile(r'use item on the ground\s+\(?(?:0x)?([0-9a-fA-F]+)\)?', re.IGNORECASE)

    def detect(self, text):
        return self._regex.search(text)

    def action(self, match, entry):
        serial = int(match.group(1), 16)
        item   = API.FindItem(serial)
        if item:
            API.UseObject(serial)
            API.SysMsg("[AutoFollow] Uso oggetto a terra: " + hex(serial))
        else:
            API.SysMsg("[AutoFollow] Oggetto non trovato a terra: " + hex(serial))


class AutoFollow:

    def __init__(self):
        self.arrive_distance = 5
        self.commands        = [FollowCommand(self.arrive_distance), StopCommand(), EatFromBagCommand(FOOD_SERIALS), UseItemOnGroundCommand()]
        self.last_command    = None

    def party_names(self):
        names = []
        for s in API.GetPartyMemberSerials():
            mob = API.FindMobile(s)
            if mob is not None and mob.Name:
                names.append(mob.Name.lower())
        return names

    def mob_distance(self, serial):
        mob = API.FindMobile(serial)
        return mob.Distance if mob else None

    def setup_password(self):
        W, H = 260, 72
        confirmed = [False]
        password  = [""]

        gump = API.Gumps.CreateModernGump(200, 200, W, H, resizable=False)

        bg = API.Gumps.CreateGumpColorBox(0.88, "#0D0D0D")
        bg.SetRect(0, 0, W, H)
        gump.Add(bg)

        lbl = API.Gumps.CreateGumpTTFLabel("Password SlogOut:", 12, "#FFFFFF")
        lbl.SetRect(8, 8, W - 16, 20)
        gump.Add(lbl)

        txt = API.Gumps.CreateGumpTextBox("", 190, 24)
        txt.SetRect(8, 32, 190, 24)
        txt.SetFocus()
        gump.Add(txt)

        btn = API.Gumps.CreateSimpleButton("OK", 48, 24)
        btn.SetRect(204, 32, 48, 24)
        gump.Add(btn)

        def on_confirm():
            password[0]  = txt.Text if txt.Text else ""
            confirmed[0] = True

        API.Gumps.AddControlOnClick(btn, on_confirm)
        API.Gumps.AddGump(gump)

        while not confirmed[0]:
            API.ProcessCallbacks()
            API.Pause(0.1)

        gump.Dispose()
        return password[0]

    def get_commands(self):
        entries = API.GetJournalEntries(1)
        found = {}
        if not entries:
            return found

        for entry in entries:
            text = entry.Text if entry.Text else ""

            for cmd in self.commands:
                m = cmd.detect(text)
                if m:
                    found[cmd] = (m, entry)

        return found

    def main(self):
        password = self.setup_password()
        self.commands.append(SlogOutCommand(password))

        API.ClearJournal()
        API.SysMsg("[AutoFollow] Avviato. Attendo comandi dai membri del gruppo.")

        while True:
            new_commands = self.get_commands()

            if new_commands:
                for cmd, (match, entry) in new_commands.items():
                    cmd.action(match, entry)
                    if cmd.persist:
                        self.last_command = (cmd, match, entry)
                    else:
                        self.last_command = None
            elif self.last_command:
                cmd, match, entry = self.last_command
                cmd.action(match, entry)

            API.ProcessCallbacks()
            API.Pause(1.0)


AutoFollow().main()
