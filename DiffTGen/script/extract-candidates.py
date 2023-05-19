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

def collect_plausible_recoder(rootdir: str, outdir: str) -> None:
  bugids = get_bugids(f"{rootdir}/data/bugid2.txt")
  for bugid in bugids:
    # os.makedirs(f"{outdir}/{bugid}", exist_ok=True)
    switch_info_file = os.path.join(rootdir, "d4j", bugid, "switch-info.json")
    sim_file = os.path.join(rootdir, "sim", bugid, f"{bugid}-sim.json")
    if os.path.exists(sim_file) == False:
      continue
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
        original = os.path.join(rootdir, "d4j", bugid, plau)
        target = os.path.join(outdir, bugid, plau)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        os.system(f"cp {original} {target}")
        
def main_recoder(args: List[str]) -> None:
  rootdir = args[1]
  outdir = args[2]
  correct_map = get_correct_patch_recoder(
      os.path.join(rootdir, "data", "correct_patch.csv"))
  for bugid in correct_map:
    os.makedirs(f"{outdir}/{bugid}", exist_ok=True)
    switch_info_file = os.path.join(rootdir, "d4j", bugid, "switch-info.json")
    sim_file = os.path.join(rootdir, "sim", bugid, f"{bugid}-sim.json")
    correct_patches = correct_map[bugid]
    with open(switch_info_file, "r") as swf, open(sim_file, "r") as sf:
      sw = json.load(swf)
      sim = json.load(sf)
      plau_list = get_plausible(sim)
      result = get_info_recoder(sw, correct_patches, plau_list)
      with open(f"{outdir}/{bugid}/{bugid}.json", "w") as f:
        json.dump(result, f, indent=2)
    for plau in plau_list:
      original = os.path.join(rootdir, "d4j", bugid, plau)
      target = os.path.join(outdir, bugid, plau)
      os.makedirs(os.path.dirname(target), exist_ok=True)
      os.system(f"cp {original} {target}")

def main_tbar(rootdir,outdir,tool):
  for bugid in os.listdir(os.path.join(rootdir, "d4j")):
    print(bugid)
    bugid_recoder = bugid.replace("_", "-")
    os.makedirs(f"{outdir}/{bugid_recoder}", exist_ok=True)
    if tool=='fixminer':
      switch_info_file = os.path.join(rootdir, "d4j", bugid, "0","switch-info.json")
    else:
      switch_info_file = os.path.join(rootdir, "d4j", bugid, "switch-info.json")
    sim_file = os.path.join(rootdir, "../experiment", f".cache-{tool}", f"{bugid}-cache.json")
    if not os.path.exists(sim_file):
      print(f"SKIP {bugid} - {sim_file} not exists")
      continue
    with open(switch_info_file, "r") as swf, open(sim_file, "r") as sf:
      sw = json.load(swf)
      sim = json.load(sf)
      plau_list = get_plausible(sim)
      result = dict()
      result["bugid"] = bugid_recoder
      result["tool"] = tool
      result["correct_patch"] = dict()
      plau_patches = list()
      result["plausible_patches"] = plau_patches
      for file_info in sw["rules"]:
        file_name = file_info["file_name"]
        for line_info in file_info["lines"]:
          if "switches" in line_info:
            patches=line_info['switches']
          else:
            patches=line_info['cases']
          for case_info in patches:
            loc = case_info["location"]
            tokens = loc.split("/")
            id = loc.replace(tokens[-1], "")
            id = id.replace("/", "_")
            patch_info = {"id": id, "location": loc, "file": file_name, "line": line_info["line"]}
            if loc in plau_list:
              plau_patches.append(patch_info)
      with open(f"{outdir}/{bugid_recoder}/{bugid_recoder}.json", "w") as f:
        json.dump(result, f, indent=2)
      if len(plau_patches) > 0:
        print(f"{bugid}: found {len(plau_patches)} plausible patches")
      for plau in plau_list:
        original = os.path.join(rootdir, "d4j", bugid) + "/" + plau
        target = os.path.join(outdir, bugid_recoder) + "/" + plau
        os.makedirs(os.path.dirname(target), exist_ok=True)
        os.system(f"cp {original} {target}")



if __name__ == "__main__":
  # main_tbar(sys.argv)
  # main_recoder(sys.argv)
  if len(sys.argv) < 4:
    print("Usage: python3 extract-candidates.py <tool> <rootdir> <outdir>")
    print("ex) python3 script/extract-candidates.py recoder /root/Recoder ./patches/recoder")
    exit(1)
  cmd = sys.argv[1]
  if cmd in ["recoder", "alpharepair"]:
    collect_plausible_recoder(sys.argv[2], sys.argv[3])
  elif cmd in ["tbar", "avatar", "kpar", "fixminer"]:
    main_tbar(sys.argv[2], sys.argv[3],cmd)
