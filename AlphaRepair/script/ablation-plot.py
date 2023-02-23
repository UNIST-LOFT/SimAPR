import json
import statistics
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import pandas
import seaborn as sns
import os
import sys
sns.set()

def get_correct_impv(outdir: str, index: int) -> Dict[str, Tuple[float, float, float]]:
  result = dict()
  with open(f"{outdir}/tmp/result-{index}.csv", "r") as f:
    for line in f.readlines():
      ln = line.strip()
      tokens = ln.split(",")
      bugid = tokens[0]
      impv = tokens[1]
      iter = tokens[2]
      original_iter = tokens[3]
      result[bugid] = (float(impv), float(iter), float(original_iter))
  return result

def generate_impv_boxplot_option(root_dir: str, outid: str, abid: str):
  final_list = []
  outdir = os.path.join(root_dir, f"out-{outid}")
  ngdir = os.path.join(root_dir, f"out-{abid}-ng")
  nedir = os.path.join(root_dir, f"out-{abid}-ne")
  groups = get_groups(outdir + f"/tmp-recoder-result-{outid}.csv")
  
  pos_group = list()
  neg_group = list()
  neut_group = list()
  for bugid in groups:
    if groups[bugid] >= 1:
      pos_group.append(bugid)
    elif groups[bugid] <= -1:
      neg_group.append(bugid)
    else:
      neut_group.append(bugid)
  
  for index in range(50):
    casino_impv = get_correct_impv(outdir, index)
    ng_impv = get_correct_impv(ngdir, index)
    ne_impv = get_correct_impv(nedir, index)
    total_casino = 0
    total_ng = 0
    total_ne = 0
    baseline = 0
    for bugid in pos_group:
      total_casino += casino_impv[bugid][1]
      baseline += casino_impv[bugid][2]
      total_ne += ne_impv[bugid][1]
      total_ng += ng_impv[bugid][1]
    final_list.append(
        {'option': "w/o-guide", 'group': 'Positive', 'impv': (baseline - total_ng)/baseline*100})
    final_list.append(
        {'option': "w/o-epsilon", 'group': 'Positive', 'impv': (baseline - total_ne)/baseline*100})
    final_list.append(
        {'option': "CASINO", 'group': 'Positive', 'impv': (baseline - total_casino)/baseline*100})
    total_casino = 0
    total_ng = 0
    total_ne = 0
    baseline = 0
    for bugid in neut_group:
      total_casino += casino_impv[bugid][1]
      baseline += casino_impv[bugid][2]
      total_ne += ne_impv[bugid][1]
      total_ng += ng_impv[bugid][1]
    final_list.append(
        {'option': "w/o-guide", 'group': 'Neutral', 'impv': (baseline - total_ng)/baseline*100})
    final_list.append(
        {'option': "w/o-epsilon", 'group': 'Neutral', 'impv': (baseline - total_ne)/baseline*100})
    final_list.append(
        {'option': "CASINO", 'group': 'Neutral', 'impv': (baseline - total_casino)/baseline*100})
    total_casino = 0
    total_ng = 0
    total_ne = 0
    baseline = 0
    for bugid in neg_group:
      total_casino += casino_impv[bugid][1]
      baseline += casino_impv[bugid][2]
      total_ne += ne_impv[bugid][1]
      total_ng += ng_impv[bugid][1]
    final_list.append(
        {'option': "w/o-guide", 'group': 'Negative', 'impv': (baseline - total_ng)/baseline*100})
    final_list.append(
        {'option': "w/o-epsilon", 'group': 'Negative', 'impv': (baseline - total_ne)/baseline*100})
    final_list.append(
        {'option': "CASINO", 'group': 'Negative', 'impv': (baseline - total_casino)/baseline*100})
  plt.clf()
  fig = plt.figure(figsize=(4, 3))
  _, sx = plt.subplots()
  plt.subplots_adjust(top=1)
  # plt.boxplot(final_pos[0],final_pos[1],final_pos[2],labels='Positive',showfliers=True,positions=(0.25,0.5,0.75),vert=True)
  df = pandas.DataFrame(final_list)
  sns.boxplot(x='group', y='impv', hue='option', data=df,
              orient='v', palette=['#00B000', '#0000FF', '#FF1F00'])
  handles, labels = sx.get_legend_handles_labels()
  sx.legend(handles=handles, labels=labels, fontsize=20)
  # plt.xlim((0.1,0.9))
  plt.xticks(fontsize=20)
  plt.yticks(fontsize=20)
  plt.xlabel('')
  plt.ylabel('')
  # plt.margins(x=0.1)
  plt.grid()
  # plt.xlabel('Improvement',fontsize=16)
  # plt.title('Improvement of each group',fontsize=16)
  plt.savefig(f'{outdir}/improvement-ablation.pdf', bbox_inches='tight')
  plt.savefig(f'{outdir}/improvement-ablation.png', bbox_inches='tight')


def get_correct_patch(correct_patch_csv: str) -> Dict[str, List[str]]:
    result = dict()
    with open(correct_patch_csv, "r") as f:
        for line in f.readlines():
            ln = line.strip()
            if len(ln) < 1 or ln.startswith("#"):
                continue
            tokens = ln.split(",")
            # print(tokens)
            # print(f"{len(bugid)} == {len(tokens[0])}")
            bugid = tokens[0]
            patches = tokens[1:]
            result[bugid] = patches
    return result


def sort_bugids(bugids: List[str]) -> List[str]:
    proj_dict = dict()
    for bugid in bugids:
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
            result.append(f"{proj}-{id}")
    return result

def get_groups(groups_csv: str) -> Dict[str, int]:
  groups = dict()
  groups_seapr = dict()
  with open(groups_csv) as f:
    lines = f.readlines()
    for line in lines:
      tokens = line.strip().split(",")
      print(tokens)
      bugid = tokens[0]
      corr_impv = float(tokens[2])
      corr_iter = tokens[4]
      org_iter = tokens[14]
      seapr_impv = float(tokens[7])
      if corr_impv > 1:
          groups[bugid] = 1
      elif corr_impv < -1:
          groups[bugid] = -1
      else:
          groups[bugid] = 0
      if seapr_impv > 1:
          groups_seapr[bugid] = 1
      elif seapr_impv < -1:
          groups_seapr[bugid] = -1
      else:
          groups_seapr[bugid] = 0
  return groups

root_dir = sys.argv[1]
out_id = sys.argv[2]
ab_id = sys.argv[3]
generate_impv_boxplot_option(root_dir, out_id, ab_id)
