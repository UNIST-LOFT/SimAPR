import os

with open("/root/project/Recoder/out/result.csv", "r") as f:
  pmap = dict()
  modes = ["recoder", "guided", "seaprpp"]
  for line in f.readlines():
    tokens = line.split(",")
    pt = tokens[0].split("-")
    p = pt[0]
    id = int(pt[1])
    proj = f"{pt[0]}-{pt[1]}"
    mode = pt[2]
    ans = tokens[1]
    ci = tokens[2]
    ct = tokens[3]
    pi = tokens[4]
    pt = tokens[5]
    if proj not in pmap:
      pmap[proj] = dict()
    pmap[proj][mode] = (ans, int(ci), float(ct), int(pi), float(pt))
  with open("/root/project/Recoder/out/table.csv", "w") as table:
    table.write("project,")
    for m in modes:
      table.write(m + ",,,,")
    table.write("\n,")
    for m in modes:
      table.write("correct impv,plau impv,correct iter,plau iter,")
    table.write("\n")
    for proj in pmap:
      table.write(f"{proj},")
      for m in modes:
        data = pmap[proj][m]
        rp = pmap[proj]["recoder"]
        corr = rp[1]
        plau = rp[3]
        if data[1] == 0:
          correct_impv = "-"
          ci = "-"
        else:
          ci = data[1]
          if corr != 0:
            correct_impv = 100 * (corr - data[1]) / corr
            correct_impv = str(correct_impv) + "%"
          else:
            correct_impv = data[1]
        if data[3] == 0:
          plau_impv = "-"
          pi = "-"
        else:
          pi = data[3]
          if plau != 0:
            plau_impv = 100 * (plau - data[3]) / plau
            plau_impv = str(plau_impv) + "%"
          else:
            plau_impv = data[3]
        table.write(f"{correct_impv},{plau_impv},{ci},{pi},")
      table.write("\n")