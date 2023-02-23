#!/usr/bin/env python3

import sys
import json
import os

def main(args):
  for arg in args[1:]:
    print(f'"{arg}",')
    with open(arg, "r") as f:
      data = json.load(f)
      fn = os.path.basename(arg)
      dir = os.path.dirname(arg)
      fn = fn.replace(".json", "-pretty.json")
      print(f'{dir}//{fn}')
      with open(os.path.join(dir,fn), "w") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
  main(sys.argv)