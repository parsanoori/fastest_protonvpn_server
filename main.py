#!/usr/bin/env python3

import os

from proton_lib import api
import sys

username = "yourusername"
password = "yourpassword"


def print_server(server):
    print(f'Name: {server.name}')
    print(f'Domain: {server.data["Domain"]}')
    print(f'Score: {server.score}')
    print(f'Load: {server.load}')


if __name__ == "__main__":
    # get the arguments
    args = sys.argv
    # check if the arguments are valid
    if len(args) > 4:
        print('Usage: python3 main.py [n] [country] [proxy]')
        exit(1)
    # if -h or --help is passed
    if len(args) == 2 and (args[1] == '-h' or args[1] == '--help'):
        print('Usage: python3 main.py [n] [country] [proxy]')
        exit(0)
    # get the length of the list
    n = int(args[1]) if len(args) >= 2 else 3
    # get the country
    country = args[2] if len(args) >= 3 else 'NL'
    # get the proxy
    proxy = args[3] if len(args) == 4 else 'socks5://127.0.0.1:1090'
    # change the environment proxy
    os.environ['ALL_PROXY'] = proxy
    # find library
    protonvpn = api.protonvpn
    # login
    if not protonvpn.check_session_exists():
        protonvpn.login(username, password)
    # get servers
    fastest_servers = protonvpn.config_for_fastest_servers_in_country(country, n)
    # print all the properties
    for i in range(len(fastest_servers)):
        print_server(fastest_servers[i])
        if i != len(fastest_servers) - 1:
            print('---------------------')
