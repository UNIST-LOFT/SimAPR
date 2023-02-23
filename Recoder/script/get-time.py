import os

result = list()
for dir in os.listdir("out-time-log"):
  if dir.startswith("gen-"):
    bugid = dir.replace("gen-", "")
    bugid = bugid.replace(".log", "")
    time = 0.0
    print(bugid)
    with open(os.path.join("out-time-log", dir), "r") as tm:
      for line in tm.readlines():
        if "100%|█" in line:
          time_str = (line.split("[")[1]).split("<")[0]
          tokens = time_str.split(":")
          if len(tokens) == 3:
            time = int(tokens[0]) * 3600 + int(tokens[1]) * 60 + int(tokens[2])
          else:
            time = int(tokens[0]) * 60 + int(tokens[1])
          result.append(f"{bugid},{time}\n")
          print(result[-1])
          break
with open("data/time.csv", "w") as csv:
  csv.writelines(result)