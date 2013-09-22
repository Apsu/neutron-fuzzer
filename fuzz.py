#!/usr/bin/env python3
"""
An OpenStack Neutron network API/RPC/namespace fuzzer/tester

Usage: fuzz.py [-kpo] [-c <file>] [-w <delay>] [-b <vms>]
               [-a | -u <uuid> | -n <host>]
               [-d <dev>] [-e <type>] [-m <cidr>] <nets>
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
  -c, --creds=<file>          Credentials file to parse [default: ~/openrc]

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
  -d <dev>, --dev=<dev>       Bridge device for vlan net [default: ph-eth1]
  -e <type>, --encap=<type>   Encapsulation type (vlan, gre) [default: vlan]
  -m <cidr>, --mask=<cidr>    CIDR template (% for octet to increment)
                              [default: 10.0.%.0/24]
  <nets>                      Number of networks to create

"""

import os
import time
import shlex
import docopt
import signal
import subprocess

from threading import Timer

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
    # Diaf
    def bail(*msg):
        raise SystemExit(msg[0])

    # Watchdog
    timer = Timer(timeout, bail, "Timeout reached waiting for networks/subnets!")
    timer.start()

    # TODO: Loop until coalesced
    stats = list(zip(*[line.split(",") for line in subprocess.check_output(
        shlex.split(
            "quantum net-list -f csv --quote none -c name -c subnets"),
        env=env,
        universal_newlines=True).splitlines()[1:]
                       if line.split(",")[0].startswith("net")]))
    print(stats)

    # Success, so cancel watchdog
    timer.cancel()


def makepath(path):
    return os.path.abspath(os.path.realpath(os.path.expandvars(os.path.expanduser(path))))


# Entry point
if __name__ == "__main__":
    try:
        print("Initializing...")

        # Catch SIGTERM/SIGINT
        def abort(*args):
            print("Abort requested! Aborting!")
            raise SystemExit
        signal.signal(signal.SIGTERM, abort)
        signal.signal(signal.SIGINT, abort)

        # Snag options
        opts = docopt.docopt(__doc__, version="v1.0.0", options_first=True)

        # Fix to make life easier
        opts["<nets>"] = int(opts["<nets>"])

        # TODO: Check option values

        # Read openrc and parse key=value into key:value
        with open(makepath(opts["--creds"])) as file:
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
        try:
            # Make/wait on networks, then subnets
            print("Making {} networks...".format(opts["<nets>"]))
            makenets(opts["<nets>"], opts["--encap"], opts["--dev"], creds)
            print("Making {} subnets...".format(opts["<nets>"]))
            makesubs(opts["<nets>"], opts["--mask"], creds)

            # Make sure it worked
            print("Waiting for resources...")
            coalesce(opts["<nets>"], creds)

            # TODO: Manually schedule to agents

            # TODO: Boot VMs

            # TODO: Tests
            print("Starting test loop...")

            # Pause if requested
            # TODO: Moar better
            if opts["--wait"]:
                print("Sleeping {} seconds...".format(opts["--wait"]))
                time.sleep(float(opts["--wait"]))
        # Cleanup?
        finally:
            # Keeping what we created?
            if not opts["--keep"]:
                print("Running cleanup handlers...")
                # Delete/wait on subnets, then networks
                print("Deleting {} subnets...".format(opts["<nets>"]))
                delsubs(opts["<nets>"], creds)
                print("Deleting {} networks...".format(opts["<nets>"]))
                delnets(opts["<nets>"], creds)

                # TODO: Delete VMs

                # TODO: Unschedule agents/clean namespaces
    # Catchall
    except Exception as e:
        print("Caught exception:", e)
        exit(1)
    else:
        exit(0)
