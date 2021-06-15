import json
import sys
import subprocess
from jinja2 import Template, StrictUndefined
from pathlib import Path
import ipaddress
import pprint

from datetime import datetime

topology = {
    "routers":{},
    "networks":{},
}

bgp_ls_db = {
    "nodes":{},
    "links":{},
    "prefixes":{},
}



## Network OSPF json data
with open(sys.argv[3]) as network_json:
    network_data = json.load(network_json)


for area in network_data["networkLinkStates"]["areas"]:
    for entry in network_data["networkLinkStates"]["areas"][area]:
        

        curr_net = {
            "networkID":entry["linkStateId"],
            "network":ipaddress.ip_interface("{}/{}".format(
                entry["linkStateId"], 
                entry["networkMask"])).network,
            "rtrs":{},
        }

       

        for i,link_a in enumerate(sorted(entry["attchedRouters"].keys())):
            for j, link_b in enumerate( sorted(entry["attchedRouters"].keys()) ):
                if (i != j):
                    link_id  = "{}-{}".format(link_a, link_b)
                    bgp_ls_db["links"][link_id] = {}
                    bgp_ls_db["links"][link_id]["localRouter"] = link_a
                    bgp_ls_db["links"][link_id]["neighborRouterId"] = link_b
                    bgp_ls_db["links"][link_id]["routerLocalAddress"] = "UNKNOWN"
                    bgp_ls_db["links"][link_id]["Adjacency SID"] = "UNKNOWN"
                    bgp_ls_db["links"][link_id]["routerNeighborAddress"] = "UNKNOWN"




# dotTemplate = Path('templates/dot.temp').read_text()
# j2_dot = Template(dotTemplate, undefined=StrictUndefined)
# topology["time"] = datetime.now().strftime("%c")
# dotFile = j2_dot.render(topology)
# # run dot with bash here
# subprocess.call(
#     "echo '{}' | sfdp -T jpg -o graph2.jpg".format(dotFile),
#     shell=True
# )

## router OSPF json data
with open(sys.argv[4]) as router_json:
    router_data = json.load(router_json)


for area in router_data["routerLinkStates"]["areas"]:
    for router in router_data["routerLinkStates"]["areas"][area]:

        bgp_ls_db["nodes"][router["linkStateId"]] = {
            "rtr_ID":router["linkStateId"],
            "OSPF_area":area,
            "links":[]
        }

        for link in router["routerLinks"]:
            if router["routerLinks"][link]["linkType"] == "another Router (point-to-point)":
                # print(router["routerLinks"][link])

                # links name from local and remote
                link_id_l = "{}-{}".format(router["linkStateId"], router["routerLinks"][link]["neighborRouterId"])
                link_id_r = "{}-{}".format(router["routerLinks"][link]["neighborRouterId"], router["linkStateId"])

                # if this link from local exists before, its because it was defined as a remote
                # therefore we know the remotes interface address
                if link_id_l not in bgp_ls_db["links"].keys():
                    # print("adding new local {}".format(link_id_l))
                    bgp_ls_db["links"][link_id_l] = {}
                    bgp_ls_db["links"][link_id_l]["routerNeighborAddress"] = "GARBAGE"
                # else:
                #     print("referencing old local {}".format(link_id_l))
                
                bgp_ls_db["links"][link_id_l]["localRouter"] = router["linkStateId"]
                bgp_ls_db["links"][link_id_l]["neighborRouterId"] = router["routerLinks"][link]["neighborRouterId"]
                bgp_ls_db["links"][link_id_l]["routerLocalAddress"] = router["routerLinks"][link]["routerInterfaceAddress"]
                bgp_ls_db["links"][link_id_l]["Adjacency SID"] = "UNKNOWN"

                if link_id_r not in bgp_ls_db["links"].keys():
                    # print("adding new remote {}".format(link_id_r))
                    bgp_ls_db["links"][link_id_r] = {}
                # else:
                #     print("referencing old remote {}".format(link_id_r))

                bgp_ls_db["links"][link_id_r]["routerNeighborAddress"] = router["routerLinks"][link]["routerInterfaceAddress"]
                    
                
                # not sure if should be listed as remote name or combined name
                bgp_ls_db["nodes"][router["linkStateId"]]["links"].append(link_id_l)
            elif router["routerLinks"][link]["linkType"] == "a Transit Network":
                print(router["routerLinks"][link])
                # bgp_ls_db["links"][link_id_l]["routerLocalAddress"] = router["routerLinks"][link]["routerInterfaceAddress"]

                # routerInterfaceAddress



## SR json data
# with open(sys.argv[1]) as sr_json:
#     SR_data = json.load(sr_json)

# print("Advertising node: {}".format(SR_data["srdbID"]))
# for node in SR_data["srNodes"]:
#     SRGB_START = node["srgbLabel"]
#     print(node["routerID"])
#     # print (topology["routers"][node["routerID"]]["Transits"])
#     # print(node)
#     for entry in node["extendedPrefix"]:
#         print("\tGLOBAL: {1}:{0}".format(entry['prefix'], entry['sid']+SRGB_START))
#     for entry in node["extendedLink"]:
#         print("\tLOCAL:  {1}:{0}".format(entry['prefix'], entry['sid']))

#         remote_interface_address = str(ipaddress.ip_interface(entry['prefix']).ip)
#         # topology["routers"][node["routerID"]]["Transits"][remote_interface_address]["label"] = entry['sid']


# # print router information
# print("Advertising node: {}".format(router_data["routerId"]))
# for router_entry in topology["routers"]:
#     print("\t""Router {}".format(router_entry))
#     for interface in topology["routers"][router_entry]["Stubs"]:
#         print("\t\t""Stub: {}".format(interface))
#     for networkID in topology["routers"][router_entry]["Transits"]:
        
#         DR_address = topology["routers"][router_entry]["Transits"][networkID]["DR_address"]
        
#         print("\t\t""Transit: {}(local address)".format(
#             ipaddress.ip_interface("{}/{}".format(
#                 topology["routers"][router_entry]["Transits"][networkID]["address"],
#                 topology["networks"][DR_address]["network"].netmask
#             ))))
        
#         for router in topology["networks"][DR_address]["rtrs"]:
#             if router != router_entry:
#                 print("\t\t\t""Router: {}".format(router))
#                 print("\t\t\t\t""Interface: {}".format(
#                     topology["networks"][DR_address]["rtrs"][router]["interface"]
#                     ))
#                 print("\t\t\t\t""MPLS-Label: {}".format(
#                     topology["routers"][router_entry]["Transits"][networkID]["label"]
#                     ))
#     print()



# #print network information 
# for networkID in topology["networks"]:
#     print("\t""LinkID: {}".format(networkID))
#     print("\t\t""Network: {}".format(topology["networks"][networkID]["network"]))
#     for router in topology["networks"][networkID]["rtrs"]:
#         print("\t\t""Interface: {} Router: {}".format(
#                 topology["networks"][networkID]["rtrs"][router]["interface"], 
#                 router ))


#         # print("\t""Router {}".format(router))
#         for interface in topology["routers"][router]["Stubs"]:
#             print("\t\t\t""Stub: {}".format(interface))
#         # for address in topology["routers"][router]["Transits"]:
#         #     networkID = address
#         #     print("\t\t\t""Transit: {} -- {}".format(
#         #             topology["routers"][router]["Transits"][address]["address"],
#         #             address))
#         print()
        
#     print()


# print("Nodes:")
# for node in bgp_ls_db["nodes"]:
#     # for attri in bgp_ls_db["nodes"][node]:
#     #     print("\t\t{}: {}".format( attri, bgp_ls_db["nodes"][node][attri]))
#     print("\t{}\n\t\tArea:{}\n\t\tLinks:{}".format(
#         bgp_ls_db["nodes"][node]["rtr_ID"],
#         bgp_ls_db["nodes"][node]["OSPF_area"],
#         bgp_ls_db["nodes"][node]["links"],
#         ))


print("Links:")
for link  in sorted(bgp_ls_db["links"].keys()):
    print("\t{}\n\t\t{}|{} --> {}|{}\n\t\tSID:{}".format(
        link,
        bgp_ls_db["links"][link]["localRouter"],
        bgp_ls_db["links"][link]["routerLocalAddress"],
        bgp_ls_db["links"][link]["routerNeighborAddress"],
        bgp_ls_db["links"][link]["neighborRouterId"],
        bgp_ls_db["links"][link]["Adjacency SID"],
        ))
