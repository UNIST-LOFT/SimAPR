import os
import matplotlib.pyplot as plt
import sys

final_list_pos = list()
final_list_neut = list()
final_list_neg = list()

with open(sys.argv[1]) as f:
  print(sys.argv[1])
  lines = f.readlines()
  for line in lines:
    tokens = line.strip().split(",")
    print(tokens)
    bugid = tokens[0]
    corr_impv = float(tokens[2])
    corr_iter = tokens[4]
    org_iter = tokens[14]
    if corr_impv > 1:
      final_list_pos.append(corr_impv)
    elif corr_impv < -1:
      final_list_neg.append(corr_impv)
    else:
      final_list_neut.append(corr_impv)

fig = plt.figure(figsize=(3.5, 4))
plt.boxplot([final_list_pos, final_list_neut, final_list_neg], labels=[
            'Pos', 'Neut', 'Neg'], showfliers=True, positions=(0.25, 0.5, 0.75), vert=True)
plt.xlim((0.1, 0.9))
plt.xticks(fontsize=20)
plt.yticks(fontsize=20)
# plt.margins(x=0.1)
plt.grid()
plt.savefig(os.path.dirname(sys.argv[1]) + "/recoder-box-plot.pdf", bbox_inches='tight')

