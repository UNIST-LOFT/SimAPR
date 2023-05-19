import os
import sys
import json
from typing import List, Tuple, Dict


def get_plausible(sim: List[dict]) -> List[str]:
  plau_list = list()
  for loc in sim:
    res = sim[loc]
    if res["plausible"]:
      plau_list.append(loc)
  return plau_list

def get_info_tbar(sw: dict, correct_patches: List[str], plau_list: List[str]) -> Dict[str, dict]:
  import shutil
  for project in os.listdir("tbar_plausible/"):
      project_name = project.split("-")[0]
      candidates = json.load(open(f"tbar_plausible/{project}"))
      
      if project_name not in os.listdir(f"/root/project/TBarCopy/results/"):
          continue
      
      if not os.path.exists(f"/root/project/TBarCopy/script/plausible_patches/{project_name}"):
          os.makedirs(f"/root/project/TBarCopy/script/plausible_patches/{project_name}")
      
      for candidate in candidates:
          path = next(iter(candidate.keys()))
          path = path.split("/")[1]
          
          for patch in os.listdir(f"/root/project/TBarCopy/results/{project_name}"):
              if patch != path:
                  continue
              shutil.copyfile(f"/root/project/TBarCopy/results/{project_name}/{patch}", 
                        f"/root/project/TBarCopy/script/plausible_patches/{project_name}/{patch}")

  for project in os.listdir("plausible_patches/"):
      for idx in os.listdir(f"plausible_patches/{project}"):
          diff_folder = project + "-" + idx[:idx.rfind("_")].replace("_", "-")
          
          file = os.listdir(f"plausible_patches/{project}/{idx}")[0]
          modif_file = os.listdir(f"plausible_patches/{project}/{idx}")[0].split(".")[0]
          
          if not os.path.exists(f"coming_rep/{diff_folder}/{modif_file}"):
              os.makedirs(f"coming_rep/{diff_folder}/{modif_file}")
              
          shutil.copyfile(f"plausible_patches/{project}/{idx}/{file}", 
                          f"coming_rep/{diff_folder}/{modif_file}/{diff_folder}_{modif_file}_t.java")

def get_info_recoder(sw: dict, correct_patches: List[str], plau_list: List[str]) -> Dict[str, dict]:
  result = dict()
  result["bugid"] = sw["project_name"]
  result["tool"] = "recoder"
  result["correct_patch"] = dict()
  plau_patches = list()
  result["plausible_patches"] = plau_patches
  for file_info in sw["rules"]:
    file_name = file_info["file"]
    for line_info in file_info["lines"]:
      for case_info in line_info["cases"]:
        loc = case_info["location"]
        tokens = loc.split("/")
        id = tokens[0] + "-" + tokens[1]
        patch_info = {"id": id, "location": loc, "file": file_name}
        if id in correct_patches:
          result["correct_patch"] = patch_info
          continue
        if loc in plau_list:
          plau_patches.append(patch_info)
  return result

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

def get_correct_patch_recoder(correct_patch_file: str) -> List[str]:
  with open(correct_patch_file, "r") as cf:
    result = dict()
    for line in cf.readlines():
      line = line.strip()
      if line.startswith('#') or len(line) == 0:
        continue
      tokens = line.split(",")
      bid = tokens[0]
      correct_patches = tokens[1:]
      result[bid] = correct_patches
    return result

def main_recoder(cmd: str, rootdir: str, outdir: str) -> None:
  tool_dir = ""
  sim_dir = os.path.join(rootdir, "experiments", cmd, "result", "cache")
  if cmd == "recoder":
    tool_dir = os.path.join(rootdir, "Recoder")
  elif cmd == "alpharepair":
    tool_dir = os.path.join(rootdir, "AlphaRepair")
  bugids = get_bugids(f"{tool_dir}/data/bugs.csv")
  for bugid in bugids:
    switch_info_file = os.path.join(tool_dir, "d4j", bugid, "switch-info.json")
    sim_file = os.path.join(sim_dir, f"{bugid}-cache.json")
    if not os.path.exists(sim_file):
      continue
    print(f"Processing {bugid}")
    with open(switch_info_file, "r") as swf, open(sim_file, "r") as sf:
      sw = json.load(swf)
      sim = json.load(sf)
      plau_list = get_plausible(sim)
      result = dict()
      result["bugid"] = sw["project_name"]
      result["tool"] = "recoder"
      result["correct_patch"] = dict()
      plau_patches = list()
      result["plausible_patches"] = plau_patches
      for file_info in sw["rules"]:
        file_name = file_info["file"]
        for line_info in file_info["lines"]:
          for case_info in line_info["cases"]:
            loc = case_info["location"]
            tokens = loc.split("/")
            id = tokens[0] + "-" + tokens[1]
            patch_info = {"id": id, "location": loc, "file": file_name, "line": line_info["line"]}
            if loc in plau_list:
              plau_patches.append(patch_info)
      if len(plau_list) == 0:
        continue
      print(bugid)
      os.makedirs(f"{outdir}/{bugid}", exist_ok=True)
      with open(f"{outdir}/{bugid}/{bugid}.json", "w") as f:
        json.dump(result, f, indent=2)
      for plau in plau_list:
        original = os.path.join(tool_dir, "d4j", bugid, plau)
        target = os.path.join(outdir, bugid, plau)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        os.system(f"cp {original} {target}")

def main_tbar(rootdir,outdir,cmd):
  tool_dir = ""
  sim_dir = os.path.join(rootdir, "experiments", cmd, "result", "cache")
  if cmd == "tbar":
    tool_dir = os.path.join(rootdir, "TBar")
  elif cmd == "avatar":
    tool_dir = os.path.join(rootdir, "Avatar")
  elif cmd == "kpar":
    tool_dir = os.path.join(rootdir, "kPar")
  elif cmd == "fixminer":
    tool_dir = os.path.join(rootdir, "FixMiner")

  bugids = get_bugids(f"{tool_dir}/data/bugs.csv")
  for bugid in bugids:
    switch_info_file = os.path.join(tool_dir, "d4j", bugid, "switch-info.json")
    sim_file = os.path.join(sim_dir, f"{bugid}-cache.json")
    if not os.path.exists(sim_file):
      continue
    print(f"Processing {bugid}")
    bid_formatted = bugid.replace("_", "-")
    
    with open(switch_info_file, "r") as swf, open(sim_file, "r") as sf:
      sw = json.load(swf)
      sim = json.load(sf)
      plau_list = get_plausible(sim)
      result = dict()
      result["bugid"] = bid_formatted
      result["tool"] = "tbar"
      result["correct_patch"] = dict()
      plau_patches = list()
      result["plausible_patches"] = plau_patches

      for file_info in sw["rules"]:
        file_name = file_info["file_name"]
        for line_info in file_info["lines"]:
          if 'cases' in line_info:
            cases=line_info["cases"]
          else:
            cases=line_info["switches"]

          for case_info in cases:
            loc = case_info["location"]
            patch_info = {"id": loc, "location": loc, "file": file_name, "line": line_info["line"]}
            if loc in plau_list:
              plau_patches.append(patch_info)
      if len(plau_list) == 0:
        continue
      print(bugid)
      os.makedirs(f"{outdir}/{bid_formatted}", exist_ok=True)
      with open(f"{outdir}/{bid_formatted}/{bid_formatted}.json", "w") as f:
        json.dump(result, f, indent=2)
      for plau in plau_list:
        original = os.path.join(tool_dir, "d4j", bugid, plau)
        target = os.path.join(outdir, bid_formatted, plau)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        os.system(f"cp {original} {target}")



if __name__ == "__main__":
  # main_tbar(sys.argv)
  # main_recoder(sys.argv)
  if len(sys.argv) < 4:
    print("Usage: python3 extract-candidates.py <tool> <rootdir> <outdir>")
    print("ex) python3 script/extract-candidates.py recoder /root/SimAPR ./patches/recoder")
    exit(1)
  cmd = sys.argv[1]
  if cmd in ["recoder", "alpharepair"]:
    main_recoder(cmd, sys.argv[2], sys.argv[3])
  elif cmd in ["tbar", "avatar", "kpar", "fixminer"]:
    main_tbar(sys.argv[2], sys.argv[3],cmd)
