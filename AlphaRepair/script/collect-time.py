import os
import psutil

# for bugid in os.listdir("d4j"):
#   src = os.path.join("d4j", bugid, "time.csv")
#   target = os.path.join("time", bugid + ".csv")
#   os.system(f"cp {src} {target}")
def get_fl_score(arg) -> float:
  return arg[1]

for proj in os.listdir("location/ochiai"):
  for ver in os.listdir(f"location/ochiai/{proj}"):
    filename = f"location/ochiai/{proj}/{ver}"
    locs = list()
    with open(filename, "r") as f:
      lines = f.readlines()
      for line in lines:
        tokens = line.split(",")  
        fl_score = float(tokens[1])
        locs.append((line, fl_score))
    locs.sort(key=get_fl_score, reverse=True)
    # dir = os.path.join("new", "ochiai", proj)
    # os.makedirs(dir, exist_ok=True)
    with open(filename, "w") as f:
      for line, fl_score in locs:
        f.write(line)
