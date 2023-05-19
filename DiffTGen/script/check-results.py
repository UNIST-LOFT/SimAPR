import os
import sys
import json

ROOTDIR = "/root/DiffTGen"

def sort_bugids(bugids):
    proj_dict = dict()
    for bugid in bugids:
        if '_' in bugid:
            proj, id = bugid.split("_")
        else:
            proj, id = bugid.split("-")
        if proj not in proj_dict:
            proj_dict[proj] = list()
        proj_dict[proj].append(int(id))
    projs = sorted(list(proj_dict.keys()))
    result = list()
    for proj in projs:
        ids = proj_dict[proj]
        ids.sort()
        for id in ids:
            if '_' in bugids[0]:
                result.append(f"{proj}_{id}")
            else:
                result.append(f"{proj}-{id}")
    return result

def main(args: list) -> None:
  if len(args) < 3:
    print("Usage: python3 check-results.py <tool> <patchdir>")
    print("Ex) python3 check-results.py recoder ./patches/recoder")
    return
  tot = 0
  filtered = 0
  done = 0
  tool = args[1]
  basedir = args[2]
  outdir = os.path.join(ROOTDIR, "out",tool)
  bugids = list()
  bugmap = dict()
  for bugid in sort_bugids(os.listdir(basedir)):
    dir = os.path.join(basedir, bugid)
    if os.path.isdir(dir):
      bugids.append(bugid)
      bugmap[bugid] = list()
      bug_json = os.path.join(dir, f"{bugid}.json")
      if not os.path.isfile(bug_json):
        print(f"Missing {bug_json}")
        continue
      with open(bug_json, "r") as f:
        bugj = json.load(f)
      for patch in bugj["plausible_patches"]:
        tot += 1
        patchid = patch["id"]
        if tool in ['tbar','avatar','kpar','fixminer']: patchid=patchid.lower()
        patchloc = patch["location"]
        out_id = f"{bugid}_{patchid}"
        out_id_dir = os.path.join(outdir, out_id)
        if not os.path.isdir(out_id_dir):
          bugmap[bugid].append({"id": patchid, "location": patchloc})
          print(f"Missing {out_id_dir}")
          continue
        done += 1
        result_file = os.path.join(out_id_dir, "result.csv")
        if not os.path.exists(result_file):
          # print(f"Empty {out_id_dir}")
          bugmap[bugid].append({"id": patchid, "location": patchloc})
        else:
          print(f"Incorrect {out_id_dir}")
          filtered += 1
        
  bugids = list(bugmap.keys())
  bugids = sort_bugids(bugids)
  csv_content = list()
  for bugid in bugids:
    line = f"{bugid},"
    for testcase in bugmap[bugid]:
      if tool in {'recoder', 'alpharepair'}:
        line += f"{testcase['id']},"
      else:
        line += f"{testcase['location']},"
    line = line[:-1]
    csv_content.append(line + "\n")
  with open(os.path.join(ROOTDIR, "out", f"{tool}.csv"), "w") as f:
    f.writelines(csv_content)
  print(f"Total: {tot}, Filtered: {filtered}, Done: {done}")

if __name__ == "__main__":
  main(sys.argv)
