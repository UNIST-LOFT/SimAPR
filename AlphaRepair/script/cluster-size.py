import os
import sys

args = sys.argv
outdir = args[1]

bugs = dict()

for bugid in os.listdir(outdir):
  if os.path.isdir(os.path.join(outdir, bugid)):
    tokens = bugid.split("-")
    if len(tokens) <= 2:
      continue
    proj = tokens[0]
    bid = tokens[1]
    bug_id = f"{proj}-{bid}"
    if bug_id in bugs:
      continue
    res_file = os.path.join(outdir, bugid, "msv-search.log")
    if not os.path.exists(res_file):
      continue
    with open(res_file, "r") as res:
      for line in res.readlines():
        if "Correct patch group size:" in line:
          bugs[bug_id] = int(line.split("Correct patch group size:")[1].strip())
          break

for bugid in bugs:
  print(f"{bugid},{bugs[bugid]}")
