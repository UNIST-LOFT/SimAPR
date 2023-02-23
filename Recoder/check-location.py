import os
from typing import Dict, Set, List, Tuple
import re

lst = ['Chart-1', 'Chart-8', 'Chart-9', 'Chart-11', 'Chart-12', 'Chart-20', 'Chart-24', 'Chart-26', 'Closure-14', 'Closure-15', 'Closure-62', 'Closure-63', 'Closure-73', 'Closure-86', 'Closure-92', 'Closure-93', 'Closure-104', 'Closure-118', 'Closure-124', 'Lang-6', 'Lang-26', 'Lang-33', 'Lang-38', 'Lang-43', 'Lang-45', 'Lang-51', 'Lang-55', 'Lang-57', 'Lang-59', 'Math-5', 'Math-27', 'Math-30', 'Math-33', 'Math-34', 'Math-41', 'Math-50', 'Math-57', 'Math-59', 'Math-70', 'Math-75', 'Math-80', 'Math-94', 'Math-105', 'Time-4', 'Time-7']
real = ['Chart-1', 'Chart-3', 'Chart-8', 'Chart-9', 'Chart-11', 'Chart-20', 'Chart-24', 'Chart-26', 'Closure-2', 'Closure-7', 'Closure-14', 'Closure-21', 'Closure-33', 'Closure-46', 'Closure-57', 'Closure-62', 'Closure-63', 'Closure-73', 'Closure-86', 'Closure-92', 'Closure-93', 'Closure-104', 'Closure-109', 'Closure-115', 'Closure-118', 'Lang-6', 'Lang-26', 'Lang-29', 'Lang-33', 'Lang-38', 'Lang-51', 'Lang-55', 'Lang-57', 'Lang-59', 'Math-5', 'Math-27', 'Math-30', 'Math-33', 'Math-34', 'Math-41', 'Math-50', 'Math-57', 'Math-65', 'Math-70', 'Math-75', 'Math-94', 'Math-96', 'Math-98', 'Math-105', 'Time-4', 'Time-7', 'Mockito-29', 'Mockito-38']
lst = real
not_found = ['Closure-15', 'Closure-92', 'Closure-93', 'Closure-118']
result = list()
out_result = dict()
file_result = dict()
out_list = list()
with open("data/correct-patch.csv", "r") as f:
  for line in f.readlines():
    proj, line, filename = line.split(",")
    out_result[proj] = int(line)
    file_result[proj] = filename
    out_list.append(proj)
lst = out_list
# with open("data/correct_patch.loc", "r") as f:
#   for line in f.readlines():
#     line = line.strip()
#     proj, lineid = line.split(":")
#     out_result[proj] = int(lineid)
# with open("Result/out", "r") as f:
#   with open("data/correct-patch.csv", "w") as csv:
#     check = False
#     bid = ""
#     for line in f.readlines():
#       line = line.strip()
#       if check:
#         check = False
#         s = line[len(bid)-1:]
#         lid = re.findall("\\d+", s)[0]
#         filename = s[len(lid):]
#         filename = filename[::-1]
#         print(f"bugid: {bid}, lid: {lid}, filename: {filename}")
#         csv.write(f"{bid.capitalize()},{lid},{filename}\n")
#       if line.strip().capitalize() in out_result:
#         check = True
#         bid = line

# lst = out_list
for bugid in lst:
  check = True
  if bugid not in out_result:
    check = False
  proj, id = bugid.split("-")
  ground = os.path.join(".", "location", "groundtruth", proj.lower(), str(id))
  ochiai = os.path.join(".", "location", "ochiai", proj.lower(), f"{id}.txt")
  if not os.path.exists(ground):
    continue
  # ground truth
  location = list()
  loc_map: Dict[str, Set[int]] = dict()
  with open(ground, "r") as g:
    for locs in g.readlines():
      for loc in locs.split("||"):
        classname, lineid= loc.split(':')
        s = ".".join(classname.split(".")[:-1])
        location.append((s, eval(lineid)))
        if s not in loc_map:
          loc_map[s] = set()
        loc_map[s].add(int(lineid))
    if check:
      ssss = False
      for s in loc_map:
        if out_result[bugid] in loc_map[s]:
          print(f"YES! {s} {out_result[bugid]}")
          ssss = True
      if not ssss:
        print(f"NO! {bugid} {out_result[bugid]} NOT FOUND")
  with open(ochiai, "r") as o:
    i = 0
    for loc in o.readlines():
      i += 1
      tmp = loc.strip().split(',')
      prob = eval(tmp[1])
      classname, lineid= tmp[0].split('#')
      iden = classname.replace(".", "")
      location.append((classname, prob, eval(lineid)))
      if int(lineid) == out_result[bugid] and iden in file_result[bugid]:
        print("FOUND ACTUAL LINE!" + bugid)
        # result.append((i, bugid, classname, lineid))
      if classname in loc_map:
        if int(lineid) in loc_map[classname]:
          print(f"Found buggy location at ranking {i}: {bugid} {classname} {lineid}")
          result.append((i, bugid, classname, lineid))
print(result)
with open("out/save.csv", "w") as f:
  found = list()
  for res in result:
    f.write(f"{res[0]},{res[1]},{res[2]},{res[3]}\n")
    found.append(res[1])
  for li in lst:
    if li not in found:
      f.write(li + ",not found!!!\n")
