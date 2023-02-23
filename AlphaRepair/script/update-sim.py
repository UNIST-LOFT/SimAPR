import os
import json
from typing import List, Set, Dict, Tuple

def get_correct_patch(correct_patch_csv: str) -> Dict[str, List[str]]:
    result = dict()
    with open(correct_patch_csv, "r") as f:
        for line in f.readlines():
            ln = line.strip()
            if len(ln) < 1 or ln.startswith("#"):
                continue
            tokens = ln.split(",")
            # print(tokens)
            # print(f"{len(bugid)} == {len(tokens[0])}")
            bugid = tokens[0]
            patches = tokens[1:]
            result[bugid] = patches
    return result


bugids = get_correct_patch("/root/project/AlphaRepair/data/correct_patch.csv")
sim_corr = "/root/project/AlphaRepair/sim-corr"
sim = "/root/project/AlphaRepair/sim"
for bugid in bugids:
  sim_file = os.path.join(sim, bugid, bugid + "-sim.json")
  sim_corr_file = os.path.join(sim_corr, bugid, bugid + "-sim.json")
  original = dict()
  new = dict()
  with open(sim_file, "r") as s:
    original = json.load(s)
  with open(sim_corr_file, "r") as sc:
    new = json.load(sc)
  for loc in original:
    if original[loc]["fail_time"] > 60:
      if loc in new:
        if new[loc]["fail_time"] < original[loc]["fail_time"]:
          original[loc] = new[loc]
          print(f"Update {bugid} - {loc} - {new[loc]}")
      else:
        print(f"No {bugid} - {loc} -  - {original[loc]}")
    elif original[loc]["pass_time"] > 180:
      if loc in new:
        if new[loc]["pass_time"] < original[loc]["pass_time"]:
          original[loc] = new[loc]
          print(f"Update {bugid} - {loc} - {new[loc]}")
      else:
        print(f"No {bugid} - {loc} - {original[loc]}")
  with open(sim_file, "w") as f:
    json.dump(original, f, indent=2)
