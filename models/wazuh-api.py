#!/usr/bin/env python

# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is a free software; you can redistribute it and/or modify it under the terms of GPLv2


from sys import argv, exit, path
from getopt import getopt, GetoptError
import json
import signal

error_wazuh_package = 0
exception_error = None
try:
    path.append(path[0].replace('models','framework'))
    from wazuh import Wazuh
    from wazuh.agent import Agent
    from wazuh.rule import Rule
    from wazuh.decoder import Decoder
    from wazuh.exception import WazuhException
    import wazuh.configuration as configuration
    import wazuh.manager as manager
    import wazuh.stats as stats
    import wazuh.rootcheck as rootcheck
    import wazuh.syscheck as syscheck
except ImportError:
    error_wazuh_package = -1
except Exception as e:
    error_wazuh_package = -2
    exception_error = e

def print_json(data, error=0):
    output = {'error': error}

    if error == 0:
        key = 'data'
    else:
        key = 'message'

    output[key] = data

    if pretty:
        print(json.dumps(output, default=encode_json, indent=4))
    else:
        print(json.dumps(output, default=encode_json))


def encode_json(o):
    if isinstance(o, Rule):
        return o.to_dict()
    elif isinstance(o, Agent):
        return o.to_dict()
    elif isinstance(o, Decoder):
        return o.to_dict()

    print_json("Wazuh-Python Internal Error: data encoding unknown", 1000)
    exit(1)


def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except:
        return False

    return json_object


def get_stdin(msg):
    try:
        stdin = raw_input(msg)
    except:
        # Python 3
        stdin = input(msg)
    return stdin


def signal_handler(n_signal, frame):
    exit(1)


def usage():
    help_msg = '''
    Wazuh Control

    \t-p, --pretty       Pretty JSON
    \t-d, --debug        Debug mode
    \t-l, --list         List functions
    \t-h, --help         Help
    '''
    print(help_msg)
    exit(1)

if __name__ == "__main__":
    request = {}
    pretty = False
    debug = False
    list_f = False

    # Read and check arguments
    try:
        opts, args = getopt(argv[1:], "pdlh", ["pretty", "debug", "list", "help"])
        n_args = len(opts)
        if not (0 <= n_args <= 2):
            print("Incorrect number of arguments.\nTry '--help' for more information.")
            exit(1)
    except GetoptError as err_args:
        print(str(err_args))
        print("Try '--help' for more information.")
        exit(1)

    for o, a in opts:
        if o in ("-p", "--pretty"):
            pretty = True
        elif o in ("-d", "--debug"):
            debug = True
        elif o in ("-l", "--list"):
            list_f = True
        elif o in ("-h", "--help"):
            usage()
        else:
            print("Wrong argument combination.")
            print("Try '--help' for more information.")
            exit(1)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    if not list_f:
        stdin = get_stdin("")
        request = is_json(stdin)
        if not request:
            print_json("Wazuh-Python Internal Error: Bad JSON input", 1000)
            exit(1)

    if error_wazuh_package < 0:
        if error_wazuh_package == -1:
            print_json("Wazuh-Python Internal Error: wazuh-framework not found.", 1000)
        if error_wazuh_package == -2:
            print_json("Wazuh-Python Internal Error: uncaught exception: {0}".format(exception_error), 1000)
        exit(0)  # error code 0 shows the msg in the API response.

    if 'function' not in request:
        print_json("Wazuh-Python Internal Error: 'JSON input' must have the 'function' key", 1000)
        exit(1)

    if 'ossec_path' not in request:
        print_json("Wazuh-Python Internal Error: 'JSON input' must have the 'ossec_path' key", 1000)
        exit(1)

    # Main
    try:
        wazuh = Wazuh(ossec_path=request['ossec_path'])

        functions = {
            '/agents/:agent_id': Agent.get_agent,
            '/agents/:agent_id/key': Agent.get_agent_key,
            '/agents': Agent.get_agents_overview,
            '/agents/summary': Agent.get_agents_summary,
            'PUT/agents/:agent_id/restart': Agent.restart_agents,
            'PUT/agents/restart': Agent.restart_agents,
            'PUT/agents/:agent_name': Agent.add_agent,
            'POST/agents': Agent.add_agent,
            'DELETE/agents/:agent_id': Agent.remove_agent,

            '/decoders': Decoder.get_decoders,
            '/decoders/files': Decoder.get_decoders_files,

            '/manager/info': wazuh.get_ossec_init,
            '/manager/status': manager.status,
            '/manager/configuration': configuration.get_ossec_conf,
            '/manager/stats': stats.totals,
            '/manager/stats/hourly': stats.hourly,
            '/manager/stats/weekly': stats.weekly,
            '/manager/logs/summary': manager.ossec_log_summary,
            '/manager/logs': manager.ossec_log,

            '/rootcheck/:agent_id': rootcheck.print_db,
            '/rootcheck/:agent_id/pci': rootcheck.get_pci,
            '/rootcheck/:agent_id/cis': rootcheck.get_cis,
            '/rootcheck/:agent_id/last_scan': rootcheck.last_scan,
            'PUT/rootcheck': rootcheck.run,
            'DELETE/rootcheck': rootcheck.clear,

            '/rules': Rule.get_rules,
            '/rules/groups': Rule.get_groups,
            '/rules/pci': Rule.get_pci,
            '/rules/files': Rule.get_rules_files,

            '/syscheck/:agent_id': syscheck.files,
            '/syscheck/:agent_id/last_scan': syscheck.last_scan,
            'PUT/syscheck': syscheck.run,
            'DELETE/syscheck': syscheck.clear

        }

        if list_f:
            print_json(sorted(functions.keys()))
            exit(0)

        if 'arguments' in request and request['arguments']:
            data = functions[request['function']](**request['arguments'])
        else:
            data = functions[request['function']]()

        print_json(data)
    except WazuhException as e:
        print_json(e.message, e.code)
        if debug:
            raise
    except Exception as e:
        print_json("Wazuh-Python Internal Error: {0}".format(str(e)), 1000)
        if debug:
            raise
