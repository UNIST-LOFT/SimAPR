import os

result = list()
for logfile in os.listdir("log"):
  if logfile.startswith("gen-"):
    gen_time = 0.0
    val_time = 0.0
    bugid = logfile.replace("gen-", "")
    bugid = bugid.replace(".log", "")
    with open(f"log/{logfile}", "r") as log:
      for line in log.readlines():
        if line.startswith("Patch Generation Time: "):
          gen_time = float(line.split(":")[1].strip())
        elif line.startswith("Patch Validation Time: "):
          val_time = float(line.split(":")[1].strip())
    total_time = gen_time + val_time
    result.append(f"{bugid},{total_time}\n")
with open("time.csv", "w") as csv:
  csv.writelines(result)
