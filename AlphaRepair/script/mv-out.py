import os
import sys

def mv(dir1, dir2) -> None:
  if os.path.exists(dir1):
    os.system(f"{dir1} {dir2}")

def main(args) -> None:
  outdir = args[1]
  id = args[2]
  for dir in os.listdir(outdir):
    new = dir.replace("-" + id, "")
    if new != dir:
      mv(dir, new)

main(sys.argv)

