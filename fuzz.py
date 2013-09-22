#!/usr/bin/env python3
"""
An OpenStack Neutron network API/RPC/namespace fuzzer

Usage: fuzz.py [-cpo] [-w <delay>] [-a | -u <uuid> | -n <host>]
               [-d <dev>] [-e <type>] [-m <cidr>] [-b <vms>] [<nets>]
       fuzz.py -h | --help
       fuzz.py -v | --version


This tool primarily tests network/subnet creation and makes sure they come up.
Tests are run in a loop (unless --oneshot) with a --wait between each round.

You can also ping namespace gateways with --ping, spawn instances with --boot,
and explicitly schedule networks to DHCP agents with --all|--uuid|--node.

SIGINT (^C) or SIGTERM will exit but still cleanup, unless --keep is passed.


Options:
  -h, --help                  This help message
  -v, --version               Show version

Tests:
  -k, --keep                  Don't cleanup after ourselves when exiting
  -p, --ping                  Ping namespace gateways
  -o, --oneshot               Test once and exit
  -w <delay>, --wait=<delay>  Delay between tests [default: 0]
  -b <vms>, --boot=<vms>      Number of VMs to boot on networks

Agents:
  -a, --all                   Schedule networks to all DHCP agents
  -u <uuid>, --uuid=<uuid>    Schedule networks to DHCP agent <uuid>
  -n <host>, --node=<host>    Schedule networks to DHCP agent on <host>

Networks:
  <nets>                      Number of networks to create [default: 5]
  -d <dev>, --dev=<dev>       Bridge device for vlan net [default: ph-eth1]
  -e <type>, --encap=<type>   Encapsulation type (vlan, gre) [default: vlan]
  -m <cidr>, --mask=<cidr>    CIDR template (% for octet to increment)
                              [default: 10.0.%.0/24]

"""

import os
import time
import shlex
import docopt
import subprocess

# Lulz
devnull = open(os.devnull)


def makenets(nets, encap, bridge, env={}):
    """Create networks in parallel and map wait() across them"""
    return [proc.wait() for proc in
            [subprocess.Popen(
                shlex.split(
                    "quantum net-create --provider:network_type={1} \
                    --provider:segmentation_id={0} \
                    --provider:physical_network={2} net{0}"
                    .format(index, encap, bridge)),
                stdout=devnull,
                stderr=devnull,
                env=env, universal_newlines=True)
             for index in range(1, nets + 1)]]


def makesubs(nets, mask, env={}):
    """Create subnets in parallel and map wait() across them"""
    return [proc.wait() for proc in
            [subprocess.Popen(
                shlex.split(
                    "quantum subnet-create --name sub{0} net{0} {1}"
                    .format(index, mask.replace("%", str(index)))),
                stdout=devnull,
                stderr=devnull,
                env=env, universal_newlines=True)
             for index in range(1, nets + 1)]]


def delnets(nets, env={}):
    """Delete networks in parallel and map wait() across them"""
    return [proc.wait() for proc in
            [subprocess.Popen(
                shlex.split("quantum net-delete net{0}".format(index)),
                stdout=devnull,
                stderr=devnull,
                env=env, universal_newlines=True)
             for index in range(1, nets + 1)]]


def delsubs(nets, env={}):
    """Delete subnets in parallel and map wait() across them"""
    return [proc.wait() for proc in
            [subprocess.Popen(
                shlex.split("quantum subnet-delete net{0}".format(index)),
                stdout=devnull,
                stderr=devnull,
                env=env, universal_newlines=True)
             for index in range(1, nets + 1)]]


def coalesce(nets, env={}, timeout=30):
    """Wait for nets/subnets to show up, bail if timeout reached"""
    #step = 0
    #while step < timeout:
    stats = list(zip(*[line.split(",") for line in subprocess.check_output(
        shlex.split(
            "quantum net-list -f csv --quote none -c name -c subnets"),
        env=env,
        universal_newlines=True).splitlines()[1:]]))
    print(stats)


# Entry point
if __name__ == "__main__":
    try:
        # Snag options
        opts = docopt.docopt(__doc__, version="v1.0.0", options_first=True)

        # TODO: Check option values

        # Read openrc and parse key=value into key:value
        with open("openrc") as file:
            creds = dict(x.strip().lstrip("export ").split("=")
                         for x in file.readlines() if "=" in x)

        # Fixup creds by resolving bash variables
        creds = {k: v if not v.startswith("$") else creds[v[1:]]
                 if not v.startswith("${") else creds[v[2:-1]]
                 for (k, v) in creds.items()}

        # Build sort key
        key = "--node {}".format(opts["--node"]) if opts["--node"] else \
              "--id {}".format(opts["--uuid"]) if opts["--uuid"] else ""

        # Get agents
        agents = dict(line.split(",") for line in
                      subprocess.check_output(
                          shlex.split(
                              "quantum agent-list -f csv -c id -c host \
                              --quote none --agent_type='DHCP agent' {}"
                              .format(key)),
                          env=creds,
                          universal_newlines=True).splitlines()[1:])

        # No matching agents?
        if key and not agents:
            raise SystemExit("Couldn't find any DHCP agents!")

        ### Happy Fuzz Times! ###

        # Make/wait on networks, then subnets
        print("Making {} networks...".format(opts["<nets>"]))
        makenets(opts["<nets>"], opts["--encap"], opts["--dev"], creds)
        print("Making {} subnets...".format(opts["<nets>"]))
        makesubs(opts["<nets>"], opts["--mask"], creds)

        # Make sure it worked
        print("Waiting for resources...")
        coalesce(opts["<nets>"], creds)

        # TODO: Tests

        # Pause if requested
        # TODO: Moar better
        if opts["--wait"]:
            print("Sleeping {} seconds...".format(opts["--wait"]))
            time.sleep(float(opts["--wait"]))

        if not opts["--keep"]:
            # Delete/wait on subnets, then networks
            delsubs(opts["<nets>"], creds)
            delnets(opts["<nets>"], creds)

    # Catchall
    except Exception as e:
        print("Caught exception:", e)
        raise
    # Cleanup?
    finally:
        pass
