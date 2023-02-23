import json
import os
import sys

filename = sys.argv[1]
switch = None
with open(filename) as f:
  # switch = json.load(f)
  lines = f.readlines()
  lists = list()
  for line in lines:
    obj = json.loads(line)
    new_obj = dict()
    new_obj['iter'] = obj['iteration']
    # new_obj['result'] = obj['result']
    if not obj['compilable']:
      continue
    if not obj['result']:
      continue
    new_obj['pass_result'] = obj['pass_result']
    new_obj["config"] = obj["config"]
    lists.append(new_obj)
  with open(filename + ".new", "w") as f:
    for obj in lists:
      f.write(json.dumps(obj) + "\n")

exit(0)

func_locs = switch["func_locations"]
file_map = dict()
for fl in func_locs:
  file_map[fl["file"]] = fl["functions"]

priority = switch["priority"]
print(file_map)

func_name = dict()
func_id = 0

for rule in switch["rules"]:
  file_name = rule["file_name"]
  fncs = file_map[file_name]
  for line in rule["lines"]:
    line_num = line["line"]
    for fn in fncs:
      if fn["begin"] <= line_num and fn["end"] >= line_num:
        fn_name = fn["function"] + ":" + str(fn["begin"]) + "-" + str(fn["end"])
        if fn_name not in func_name:
          func_name[fn_name] = func_id
          func_id += 1
        print(f'{line["switches"][0]["location"]}: {func_name[fn_name]}')
exit(0)

rank = 0
for p in priority:
  try:
    fncs = file_map["src/main/java/" + p["file"].replace(".", "/") + ".java"]
  except:
    continue
  index = 0
  for fn in fncs:
    index += 1
    if fn["begin"] <= p["line"] and fn["end"] >= p["line"]:
      try:
        print("rank: %d, file: %s - %d" % (rank, p["file"], index))
        break
      except:
        pass
  rank += 1
