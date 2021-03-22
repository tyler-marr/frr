import json



with open('ospf-sr.json') as sr:
  data = json.load(sr)

print("Advertising node: " +data["srdbID"])
for node in data["srNodes"]:
	print(node["routerID"])
	for entry in node["extendedLink"]:
		print(entry)