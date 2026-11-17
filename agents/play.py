"""Play the Orchard Lab game.

  python3 play.py status       show the rules, your notebook so far, and apples left (free)
  python3 play.py practice     practice on 1 apple
  python3 play.py review M     mock review of M apples
  python3 play.py demo         ask an expert for a demonstration
  python3 play.py defend       defend your thesis (cut all remaining apples)

Every command except `status` uses up one day and cannot be undone.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

conn = json.loads((Path(__file__).parent / ".game.json").read_text())
args = [a.lower() for a in sys.argv[1:]]
if not args or args[0] in ("-h", "--help", "help"):
    print(__doc__)
    sys.exit(0)
if args[0] == "status":
    body = {"cmd": "status"}
elif args[0] in ("practice", "demo", "defend") and len(args) == 1:
    body = {"action": {"type": args[0]}}
elif args[0] == "review" and len(args) == 2 and args[1].isdigit():
    body = {"action": {"type": "review", "m": int(args[1])}}
else:
    print("Unrecognized command.\n" + __doc__)
    sys.exit(2)
body["token"] = conn["token"]
req = urllib.request.Request(f"http://127.0.0.1:{conn['port']}/", data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"})
try:
    print(urllib.request.urlopen(req).read().decode())
except urllib.error.HTTPError as e:
    print(e.read().decode())
    sys.exit(1)
