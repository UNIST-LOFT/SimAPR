import os

d4j1 = {"Chart", "Closure", "Lang", "Math", "Mockito", "Time"}

for bugid in os.listdir("d4j"):
  proj, bid = bugid.split("-")
  if proj not in d4j1:
    continue
  if proj == "Closure":
    if int(bid) > 132:
      continue
  if not os.path.exists(f"d4j/{bugid}/switch-info.json"):
    continue
  print("Remove", bugid)
  for tmps in os.listdir(f"d4j/{bugid}"):
    if tmps.startswith("temp-"):
      os.system(f"rm d4j/{bugid}/{tmps}")
    if tmps == f"{bugid}.json":
      os.system(f"rm d4j/{bugid}/{tmps}")
      print("Remove", bugid, tmps)