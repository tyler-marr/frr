#!/usr/bin/env python

#
# <template>.py
# Part of NetDEF Topology Tests
#
# Copyright (c) 2017 by
# Network Device Education Foundation, Inc. ("NetDEF")
#
# Permission to use, copy, modify, and/or distribute this software
# for any purpose with or without fee is hereby granted, provided
# that the above copyright notice and this permission notice appear
# in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NETDEF DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NETDEF BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
#

"""
<template>.py: Test <template>.
"""

import os
import sys
import pytest
import subprocess

# Save the Current Working Directory to find configuration files.
CWD = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(CWD, "../"))

# pylint: disable=C0413
# Import topogen and topotest helpers
from lib import topotest
from lib.topogen import Topogen, TopoRouter, get_topogen
from lib.topolog import logger


# Required to instantiate the topology builder class.
from mininet.topo import Topo

# Used for templating config files
from jinja2 import Template, StrictUndefined
from pathlib import Path

from datetime import datetime


# TODO: select markers based on daemons used during test
# pytest module level markers
"""
pytestmark = pytest.mark.bfdd # single marker
pytestmark = [
	pytest.mark.bgpd,
	pytest.mark.ospfd,
	pytest.mark.ospf6d
] # multiple markers
"""



networks = {}        # used to check if first or 2nd link to a network

network_dict = {}          # list of all rtr-rtr links
routers_list = []       # list of all rtrs
hosts_list = []       # list of all rtrs
intf_dict = {} # intf_network_lookup["r1-eth0"] = 1

class Router():

    class Interface():
        "contains links and interfaces"
        dev_n = 0
        network = 0
        subnet = 0

        def __init__(self, dev_n, network, subnet):
            self.dev_n = dev_n
            self.network = network
            self.subnet = subnet
    
    name = ''
    router_number = 0
    interfaces = []
    isRouter = 1

    def __init__(self, rtr):
        
        self.router_number = rtr.name[1:]
        self.name = rtr.name
        self.interfaces = []
        self.isRouter = 1 if rtr.name[0] == 'r' else 0

        # print("router {} has {} interfaces".format(self.name, len(rtr.links)))
        for link in rtr.links:
            dev_n = link.split('eth')[1]
            # network = rtr.links[link][1][1:].split('-eth')[0]
            

            # if network not in networks:
            #     networks[network] = 1
            # else:
            #     networks[network] = networks[network] + 1 
            # subnet = networks[network]

            self.interfaces.append(self.Interface(
                    dev_n, 
                    intf_dict[link]["network_id"], 
                    intf_dict[link]["subnet"]))
            # print("\t {} - {}".format(link, intf_dict[link]["network_id"]))
        

    def toDict(self):
        data ={
            "name":self.name,
            "rtr_n":self.router_number,
            "interfaces":[],
            "isRouter":self.isRouter,
        }
        if self.isRouter:
            data["gsrl"] = int(self.router_number)+4000
        # print(data)

        for interface in self.interfaces:
            data["interfaces"].append({
                "dev_n":interface.dev_n,
                "network":interface.network, 
                "subnet":interface.subnet,
            })

        return data

    class link():
        src_rtr = 0
        dst_rtr = 0
        network = 0

        def __init__(self, src, dst, network):
            self.src_rtr = src
            self.dst_rtr = dst
            self.network = network
    



class SegTopo(Topo):
    "Test topology builder"

    
    networkCount = 0        # used to number next network

    

    def produceRouterConfig(self, data, zebraTemplate, ospfdTemplate):

        for router in data["routers"]:
            # print (router["name"])
            for interface in router["interfaces"]:
                # print(interface)
                # print ("\t{}".format(interface["network"]))
                interface["network"] = {
                    "id":interface["network"],
                    "type":network_dict[interface["network"]]["type"],
                }
                



            j2_zebra = Template(zebraTemplate, undefined=StrictUndefined)
            zebraConf = j2_zebra.render(router)


            rtr_folder = 'config/{}'.format(router["name"])
            if not os.path.exists(rtr_folder):
                os.makedirs(rtr_folder)

            file='{}/zebra.conf'.format(rtr_folder) 
            with open(file, 'w') as filetowrite:
                filetowrite.write(zebraConf)

            if router["name"][0] != 'h':
                j2_ospfd = Template(ospfdTemplate, undefined=StrictUndefined)       
                ospfdConf = j2_ospfd.render(router)

                file='{}/ospfd.conf'.format(rtr_folder) 
                with open(file, 'w') as filetowrite:
                    filetowrite.write(ospfdConf)

    # def produceHostsConfig(self, hosts, zebraTemplate):

    #     for i, host in enumerate(hosts):
    #         data ={
    #             "name":host.name,
    #             "rtr_n":i,
    #             "interfaces":[]
    #         }
    #         for interface in host.interfaces:
    #             data["interfaces"].append({
    #                 "dev_n":interface.dev_n,
    #                 "network":interface.network, 
    #                 "subnet":interface.subnet,
    #             })
    #         j2_zebra = Template(zebraTemplate, undefined=StrictUndefined)
    #         zebraConf = j2_zebra.render(host)            

    #         rtr_folder = 'config/{}'.format(host["name"])
    #         if not os.path.exists(rtr_folder):
    #             os.makedirs(rtr_folder)

    #         file='{}/zebra.conf'.format(rtr_folder) 
    #         with open(file, 'w') as filetowrite:
    #             filetowrite.write(zebraConf)

    def produceGraph(self, data, dotTemplate):

        j2_dot = Template(dotTemplate, undefined=StrictUndefined)
        data["time"] = datetime.now().strftime("%c")
        dotFile = j2_dot.render(data)
        print(dotFile)
        # run dot with bash here
        subprocess.call(
            "echo '{}' | sfdp -T jpg -o graph.jpg".format(dotFile),
            shell=True
        )
        for link in data["links"]:
            print(link)
            print("{}".format(data["links"][link]))



    def connect_via_switch(self, router_list):
        tgen = get_topogen(self)
        self.networkCount = self.networkCount  + 1

        # only if addding switch
        switch = tgen.add_switch("s{}".format(self.networkCount))

        network_dict[self.networkCount] = {
            "routers":router_list,
            "network_id":self.networkCount,
            "type":"broadcast",
            }

        subnet = 1

        for router in network_dict[self.networkCount]["routers"]:

            numLinks = len(tgen.gears[router].links)

            # only if adding switch
            switch.add_link(tgen.gears[router])

            src_lnk = "{}-eth{}".format(router,numLinks)
            dst_lnk = tgen.gears[router].links[src_lnk][1]


            intf_dict[src_lnk] = { 
                    "network_id":self.networkCount,
                    "subnet":subnet,
            }
            subnet = subnet + 1
            # intf_dict[dst_lnk] = network_dict[self.networkCount]
            print ("Connecting {} to {} via network {}:{}".format(
                    src_lnk, 
                    dst_lnk,
                    network_dict[self.networkCount]["network_id"],
                    network_dict[self.networkCount]["type"],
                    ))

    def ptp_connect(self, r1, r2):
        tgen = get_topogen(self)

        self.networkCount = self.networkCount + 1

        network_dict[self.networkCount] = {
            "routers":[r1,r2],
            "network_id":self.networkCount,
            "type":"point-to-point",
            }

        numLinks = len(tgen.gears[r1].links)
        tgen.gears[r1].add_link(tgen.gears[r2])

        src_lnk = "{}-eth{}".format(r1,numLinks)
        dst_lnk = tgen.gears[r1].links[src_lnk][1]

        intf_dict[src_lnk] = { 
            "network_id":self.networkCount,
            "subnet":1,
        }
        intf_dict[dst_lnk] = { 
            "network_id":self.networkCount,
            "subnet":2,
        }

        print ("Connecting {} to {} via network {}:{}".format(
                    src_lnk, 
                    dst_lnk,
                    network_dict[self.networkCount]["network_id"],
                    network_dict[self.networkCount]["type"],
                    ))


    def attach_host(self, rtr, host):
        tgen = get_topogen(self)

        self.networkCount = self.networkCount + 1

        network_dict[self.networkCount] = {
            "routers":[rtr, host],
            "network_id":self.networkCount,
            "type":"broadcast",
            }

        tgen.add_router(host)
        numLinks = len(tgen.gears[rtr].links)
        tgen.gears[rtr].add_link(tgen.gears[host])

        src_lnk = "{}-eth{}".format(rtr,numLinks)
        dst_lnk = tgen.gears[rtr].links[src_lnk][1]
        intf_dict[src_lnk] = { 
            "network_id":self.networkCount,
            "subnet":1,
        }
        intf_dict[dst_lnk] = { 
            "network_id":self.networkCount,
            "subnet":2,
        }

        print ("Connecting {} to {} via network {}:{}".format(
                src_lnk, 
                dst_lnk,
                network_dict[self.networkCount]["network_id"],
                network_dict[self.networkCount]["type"],
                ))



    def build(self, *_args, **_opts):
        "Build function"
        tgen = get_topogen(self)

        for routern in range(1, 13):
            tgen.add_router("r{}".format(routern))

        self.attach_host("r1", "h1")
        self.attach_host("r12", "h2")
        # self.attach_host("r11", "h3")

        tgen.add_router("r13")
        self.connect_via_switch(["r1", "r2", "r13"])
        # self.ptp_connect("r1", "r2")

        self.ptp_connect("r1", "r4")
        self.ptp_connect("r2",   "r3")
        self.ptp_connect("r2",   "r4")
        self.ptp_connect("r2",   "r6")
        self.ptp_connect("r3",   "r4")
        self.ptp_connect("r3",   "r5")
        self.ptp_connect("r5",   "r6")
        self.ptp_connect("r5",   "r8")

        self.ptp_connect("r5", "r7")
        self.ptp_connect("r6", "r8")

        self.ptp_connect("r6",   "r7")
        
        self.ptp_connect("r7",   "r8")
        self.ptp_connect("r7",  "r10")
        self.ptp_connect("r8",   "r9")
        self.ptp_connect("r9",  "r10")
        self.ptp_connect("r9",  "r12")

        tgen.add_router("r14")
        self.connect_via_switch(["r10", "r11", "r14"])
        # self.ptp_connect("r10", "r11")

        self.ptp_connect("r10", "r12")
        self.ptp_connect("r11", "r12")



        zebraTemplate = Path('templates/zebra.temp').read_text()
        ospfdTemplate = Path('templates/ospfd.temp').read_text()
        dotTemplate = Path('templates/dot.temp').read_text()

        # For all registred routers, load the zebra configuration file
        for rname, router in tgen.routers().items():
            router_dict = Router(get_topogen(self).gears[rname]).toDict()
            routers_list.append(router_dict)


        data = {
            "hosts":hosts_list,
            "routers":routers_list,
            "links":network_dict,
        }

        self.produceRouterConfig(data, zebraTemplate, ospfdTemplate)

        self.produceGraph(data, dotTemplate)
        print("Finished producing graph for topology")


def setup_module(mod):
    "Sets up the pytest environment"
    # This function initiates the topology build with Topogen....
    if mod == None:
        tgen = Topogen(SegTopo, "standalone")
    else:
        tgen = Topogen(SegTopo, mod.__name__)
    # ... and here it calls Mininet initialization functions.
    tgen.start_topology()

    # This is a sample of configuration loading.
    router_list = tgen.routers()

    # For all registred routers, load the zebra configuration file
    print("Loading config for routers")
    for rname, router in router_list.items():
        router.load_config(
            TopoRouter.RD_ZEBRA,
            os.path.join(CWD, 'config/{}/zebra.conf'.format(rname))
        )
        router.load_config(
            TopoRouter.RD_OSPF, 
            os.path.join(CWD, "config/{}/ospfd.conf".format(rname))
        )

    # After loading the configurations, this function loads configured daemons.
    tgen.start_router()


def teardown_module(mod):
    "Teardown the pytest environment"
    tgen = get_topogen()

    # This function tears down the whole topology.
    tgen.stop_topology()


def test_call_mininet_cli():
    "Dummy test that just calls mininet CLI so we can interact with the build."
    tgen = get_topogen()
    # Don't run this test if we have any failure.
    if tgen.routers_have_failure():
        pytest.skip(tgen.errors)

    logger.info("calling mininet CLI")
    tgen.mininet_cli()


if __name__ == "__main__":
    args = ["-s"] + sys.argv[1:]
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        setup_module(None)
        teardown_module(None)
    else:
        sys.exit(pytest.main(args))

