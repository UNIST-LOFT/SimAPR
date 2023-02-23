import json
import subprocess
import sys
from typing import Dict, Tuple

if __name__ == '__main__':
    args = sys.argv
    patch_path = args[0]
    new_fl_path = args[1]

# Parse new FL result
new_fls: Dict[Tuple[str, int], float] = {}
with open(new_fl_path, 'r') as f:
        for line in f:
            element = line.strip().split('@')
            loc = (element[0], int(element[1]))
            new_fls[loc] = float(element[2])

# Load original info
with open(f'{patch_path}/switch-info.json', 'r') as f:
        root: dict = json.load(f)

# Update priority
new_info = root.copy()
new_locs = []
for loc in new_fls:
        new_locs.append(
            {'file': loc[0], 'line': loc[1], 'fl_score': new_fls[loc]})

# Get each line in rules, and generate new original ranks
new_ranking = []
for loc in new_fls:
        # Get file
        file_name = loc[0].replace('.', '/')
        for f in new_info['rules']:
            if file_name in f['file']:
                file = f
                break

# Find line
for l in file['lines']:
            if l['line'] == loc[1]:
                line = l

line['fl_score'] = new_fls[loc]
for i, patch in enumerate(line['cases']):
            new_ranking.append(f'{line["id"]}-{patch["case"]}')

new_info['ranking'] = new_ranking

# Backup original and save new info
subprocess.run(['cp', '-rf', f'{patch_path}/switch-info.json', f'{patch_path}/switch-info-bak.json'],
               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
with open(f'{patch_path}/switch-info.json', 'w') as f:
        json.dump(new_info, f)
