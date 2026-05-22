import API
import re

FOLLOW_RE = re.compile(r'follow\s+me[\s:]+\(?(?:0x)?([0-9a-fA-F]+)\)?', re.IGNORECASE)
STOP_RE   = re.compile(r'stop\s+follow', re.IGNORECASE)

ARRIVE_DISTANCE = 5  # tile per considerarsi "arrivati"

API.ClientCommand("alwaysrun")
API.ClearJournal()
API.SysMsg("AutoFollow avviato. Attendo 'follow me <serial>' dai membri del gruppo.")


def party_names():
    names = []
    for s in API.GetPartyMemberSerials():
        mob = API.FindMobile(s)
        if mob is not None and mob.Name:
            names.append(mob.Name.lower())
    return names

def mob_distance(serial):
    distance = None
    mob = API.FindMobile(serial)
    if mob:
        distance = mob.Distance
    return distance


def main():
    last_time        = None
    following_serial = None
    has_hidden       = False  # evita di mandare .nasconditi piu' volte per lo stesso target

    while True:
        API.SysMsg("Intero")

        if API.Pathfinding():
            API.SysMsg("PathFinding...")
            if following_serial:
                follower_dist = mob_distance(following_serial)
                if follower_dist and follower_dist <= ARRIVE_DISTANCE and not API.Player.IsHidden:
                    API.Msg(".nasconditi")
                    API.CancelAutoFollow()
                elif follower_dist is None:
                    API.SysMsg("Non Vedo il Follower")

        else:
            API.SysMsg(f"sono fermo, non vedo: {following_serial}")


            # --- Legge journal ---
            entries = API.GetJournalEntries(3)
            if entries:
                for entry in entries:
                    if last_time is not None and entry.Time <= last_time:
                        continue
                    last_time = entry.Time

                    text        = entry.Text  if entry.Text  else ""

                    # follow me <serial>
                    m = FOLLOW_RE.search(text)
                    if not m:
                        continue
                    try:
                        following_serial = int(m.group(1), 16)
                    except Exception:
                        continue

                    API.AutoFollow(following_serial)
                    API.SysMsg("AutoFollow: seguo " + (entry.Name or "?") + " (" + hex(following_serial) + ")")       
        API.Pause(1.0)


main()
