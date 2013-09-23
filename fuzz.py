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

class Spawner:
    """Wrap subprocess.Popen calls, store objects, allow .wait() on all"""
    def __init__(self):
        self.procs = []
        # Python subprocess.DEVNULL only in Python 3.3
        self.devnull = open(os.devnull)

    def reset(self):
        self.procs.clear()

    def spawn(self, cmd, *args, env={}, quiet=False, reset=False):
        if reset:
            self.reset()

        self.procs.append(
            subprocess.Popen(
                shlex.split(cmd.format(*args)),
                stdout=self.devnull if quiet else None,
                stderr=self.devnull if quiet else None,
                env=env, universal_newlines=True))

    def wait(self):
        codes = [proc.wait() for proc in self.procs]
        self.reset()
        return codes


class Credentials:
    """Parse environment file and sanitize without using a shell"""
    def __init__(self, path="~/openrc", env={}):
        # Read file and parse key=value into key:value
        # Strip whitespace, "export", ignore past ;, remove quotes
        with open(self._makepath(path)) as file:
            env.update = {k: v.strip("\"")
                          for (k, v) in file.readlines()
                          .strip().split(";")[0].lstrip("export ").split("=")
                          if "=" in x and not x.startswith("#")}

        # Fixup env by resolving bash variables ($var, ${var})
        self.env = {k: v if not v.startswith("$") else env[v[1:]]
                    if not v.startswith("${") else env[v[2:-1]]
                    for (k, v) in env.items()}

    def _makepath(self, path):
        return os.path.abspath(
            os.path.realpath(
                os.path.expandvars(
                    os.path.expanduser(path))))

    def get(self):
        return self.env


class Agents:
    """Handle DHCP agent scheduling"""
    def __init__(self, node=None, uuid=None, multi=False, creds={}):
        # Build sort key
        self.key = "--node {}".format(node) if node else \
                   "--id {}".format(uuid) if uuid else \
                   "" if multi else None

        if self.key:
            # Get agents
            self.agents = dict(line.split(",") for line in
                          subprocess.check_output(
                              shlex.split(
                                  "quantum agent-list -f csv -c id -c host \
                                  --quote none --agent_type='DHCP agent' {}"
                                  .format(key)),
                              env=creds,
                              universal_newlines=True).splitlines()[1:])

            # No matching agents?
            if not self.agents:
                raise SystemExit("Couldn't find any DHCP agents!")

    def schedule(self, nets):
        """Schedule networks to agents"""
        # TODO
        pass


class Networks:
    """
    Create networks and subnets via quantum client
    If keep is True, don't delete after creation
    Will
    """
    def __init__(self, num=0, encap="vlan", cidr="10.0.%.0/24",
                 creds=None, quiet=True, keep=False):
        # Args
        self.num = int(num)
        self.encap = encap
        self.creds = creds
        self.quiet = quiet
        self.keep = keep

        # Status
        self.nets = False
        self.subs = False

        # Spawner
        self.spawner = Spawner()

    def __enter__(self):
        return self

    def _create_nets(self, wait=True):
        pass

    def _create_subs(self, wait=True):
        pass

    def _delete_nets(self, wait=True):
        pass

    def _delete_subs(self, wait=True):
        pass

    def create(self):
        for i in range(1, num + 1):
            pass

    def delete(self):
        pass

    def __iter__(self):
        return self

    def __next__(self):
        return

    def __exit__(self, *args):
        # Keeping what we created?
        if not self.keep:
            print("Running cleanup handlers...")
            # Delete/wait on subnets, then networks
            print("Deleting {} subnets...".format(opts["<nets>"]))
            delsubs()
            print("Deleting {} networks...".format(opts["<nets>"]))
            delnets(opts["<nets>"], creds)

                # TODO: Delete VMs

                # TODO: Unschedule agents/clean namespaces

        # Don't re-raise exception if we're in one
        return true


def docalls(cmd, *args, num=0, env={}, quiet=True):
    # Lulz
    devnull = open(os.devnull)

    return [proc.wait() for proc in
            [subprocess.Popen(
                shlex.split(cmd.format(*args)),
                stdout=devnull if quiet else None,
                stderr=devnull if quiet else None,
                env=env, universal_newlines=True)]
            for index in range(1, num + 1)]


def makenets(*args, **kwargs):
    """Create networks in parallel and map wait() across them"""
    return docall(
        "quantum net-create --provider:network_type={1} \
        --provider:segmentation_id={0} \
        --provider:physical_network={2} net{0}"
        , args)


def makesubs(nets, mask, *args, **kwargs):
    """Create subnets in parallel and map wait() across them"""
    return [proc.wait() for proc in
            [docall(
                "quantum subnet-create --name sub{0} net{0} {1}"
                .format(index, mask.replace("%", str(index))), *args, **kwargs)
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
    time.sleep(5)
    stats = list(zip(*[line.split(",") for line in subprocess.check_output(
        shlex.split(
            "quantum net-list -f csv --quote none -c name -c subnets"),
        env=env,
        universal_newlines=True).splitlines()[1:]
#                       if line.split(",")[0].startswith("net")
                   ]))
    print(stats)

    # Success, so cancel watchdog
    timer.cancel()




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
        print(opts)

        # TODO: Check option values

        creds = Credentials("~/openrc", os.environ)
        agents = Agents(opts["--node"], opts["--uuid"], opts["--all"], creds.get())




        ### Happy Fuzz Times! ###
        try:
            # Make/wait on networks, then subnets
            print("Making {} networks...".format(opts["<nets>"]))
            makenets(opts["<nets>"], opts["--encap"], opts["--dev"], creds, quiet=False)
            print("Making {} subnets...".format(opts["<nets>"]))
            makesubs(opts["<nets>"], opts["--mask"], creds, quiet=False)

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
    # Catchall
    except Exception as e:
        print("Caught exception:", e)
        exit(1)
    else:
        exit(0)
