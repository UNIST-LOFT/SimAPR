import os
import json
from typing import Dict, List, Set, Tuple


def get_bugids(filename: str) -> List[str]:
    l = list()
    if not os.path.exists(filename):
        return l
    with open(filename, "r") as f:
        for line in f.readlines():
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            l.append(line.split(",")[0])
    return l

def update_msv_result(dir: str, bugid, id) -> None:
  result: list = None
  sim: dict = None
  basedir = "out-alpha-plau"
  with open(os.path.join(dir, "msv-result.json"), "r") as f:
    result = json.load(f)
  sim_file = os.path.join("sim", bugid, f"{bugid}-sim.json")
  with open(sim_file, "r") as f:
    sim = json.load(f)
  time = 0.0
  for elem in result:
    loc = elem["config"][0]["location"]
    if loc in sim:
      sim_data = sim[loc]
      time += sim_data["fail_time"] + sim_data["pass_time"]
    elem["time"] = time
  save_dir = os.path.join(basedir, bugid, id)
  os.makedirs(save_dir, exist_ok=True)
  with open(os.path.join(save_dir, "msv-result.json"), "w") as f:
    json.dump(result, f, indent=2)

def batch_msv_result() -> None:
  lst = get_bugids("data/correct_patch.csv")
  id = "220824-full"
  for bugid in lst:
    recoder_dir = os.path.join(f"out-{id}", f"{bugid}-recoder-{id}")
    update_msv_result(recoder_dir, bugid, "recoder")
    seapr_dir = os.path.join(f"out-{id}", f"{bugid}-seapr-{id}")
    update_msv_result(seapr_dir, bugid, "seapr")
    for i in range(20):
      guided_dir = os.path.join(f"out-{id}", f"{bugid}-guided-{id}-{i}")
      update_msv_result(guided_dir, bugid, f"guided-{i}")

if __name__ == "__main__":
  batch_msv_result()
