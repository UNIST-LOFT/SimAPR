import json

file = open("/root/project/TBarCopy/D4J/projects/Time_7/switch-info.json", "r")
x = json.loads(file.read())
file.close()
for mut in x["rules"][4]["lines"][0]["switches"]:
    location = mut["location"]
    print(f"\"{location}\",")