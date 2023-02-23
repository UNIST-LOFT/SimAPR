import os
from typing import List, Dict, Set, Tuple
import json


def main(args: List[str]) -> None:
  for bugid in os.listdir("d4j"):
    print(bugid)
    if not os.path.exists(f"d4j/{bugid}/tests.trig"):
      print(f"{bugid}!! error!!! tests.trig not found")
      continue
    failing_tests = list()
    with open(f"d4j/{bugid}/tests.trig") as f:
      lines = f.readlines()
      for line in lines:
        failing_tests.append(line.strip())
    print(f"{bugid} {failing_tests}")
    info = None
    with open(f"d4j-220531/{bugid}/switch-info.json", "r") as f:
      info = json.load(f)
    for file in info["func_locations"]:
      filename = file["file"]
      filename = filename.replace(f"buggy/{bugid}/", "", 1)
      file["file"] = filename
    info["failing_test_cases"] = failing_tests
    info["failed_passing_tests"] = []
    rules = info["rules"]
    for file in rules:
      filename = file["file"]
      filename = filename.replace(f"buggy/{bugid}/", "", 1)
      file["file"] = filename
    info["rules"] = rules
    # os.makedirs(f"d4j-new/{bugid}", exist_ok=True)
    with open(f"d4j/{bugid}/switch-info.json", "w") as f:
      json.dump(info, f, indent=2)

main([])