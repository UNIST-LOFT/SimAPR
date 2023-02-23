import os
import sys
from typing import List, Set, Dict, Tuple

def main(args: List[str]) -> None:
  # Check all sub directories
  root_dir = os.path.abspath(args[1])
  dest_root = os.path.abspath(args[2])
  for dir in os.listdir(root_dir):
    if os.path.isdir(os.path.join(root_dir, dir)):
      print(f"Processing {dir}")
      proj, ver = dir.split('_')
      dest_dir = os.path.join(dest_root, proj.lower())
      os.makedirs(dest_dir, exist_ok=True)
      dest_file = os.path.join(dest_dir, f"{ver}.txt")
      fl_file = os.path.join(root_dir, dir, 'opt.txt')
      if not os.path.exists(fl_file):
        print('File not found:', fl_file)
      new_lines = list()
      with open(fl_file, 'r') as f:
        lines = f.readlines()
        print(len(lines))
        for line in lines:
          if "#" in line or "$" in line:
            print("Skipping line:", line)
          cl, ln, sc = line.strip().split("@")
          new_line = f"{cl}#{ln},{sc},(1,67)\n"
          new_lines.append(new_line)
      with open(dest_file, 'w') as f:
        f.writelines(new_lines)
main(sys.argv)