#!/usr/bin/python3
"""Conky-System launcher and local network information."""

import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import platform
import re
import shlex
import signal
import subprocess
import time

PROC = Path('/proc')
TEMPLATE = Path('/etc/conky/conky-system.conf')
HELPER = '/usr/bin/conky-system'


def output(command):
    try:
        return subprocess.check_output(command, stderr=subprocess.DEVNULL, timeout=3, text=True)
    except (OSError, subprocess.SubprocessError):
        return ''


def resolution():
    text = output(['xrandr', '--current'])
    for pattern in [r' connected primary (\d+)x(\d+)\+', r' connected (\d+)x(\d+)\+',
                    r'^\s+(\d+)x(\d+)\s+.*\*']:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            return int(match[1]), int(match[2])
    match = re.search(r'dimensions:\s+(\d+)x(\d+)', output(['xdpyinfo']))
    if match:
        return int(match[1]), int(match[2])
    return 1920, 1080


def layout(width, height, override=None):
    scale = min(width / 1920, height / 1080)
    try:
        value = float(override)
        if math.isfinite(value) and value > 0:
            scale = value
    except (TypeError, ValueError):
        pass
    scale = max(0.5, min(scale, 3.0))
    return {'font': max(6.0, round(10 * scale, 2)), 'width': max(216, round(360 * scale)),
            'gap_x': round(360 * scale), 'gap_y': round(30 * scale)}


def network_text():
    interface = os.environ.get('CONKY_NET_INTERFACE', '')
    if not interface or interface == 'auto':
        try:
            routes = json.loads(output(['ip', '-j', 'route', 'get', '1.1.1.1']))
            interface = routes[0].get('dev', '') if routes else ''
        except (ValueError, TypeError, IndexError, AttributeError, KeyError):
            interface = ''
    title = '${color1}+-- Network${color}'
    if not isinstance(interface, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,15}', interface) or interface == 'lo':
        return title + '\n|   +-- ${color2}Offline${color}'
    return '\n'.join([
        title,
        '|   +-- Interface ${color2}${alignr}' + interface + '${color}',
        '|   +-- Address ${color2}${alignr}${addr ' + interface + '}${color}',
        '|   +-- Download ${color2}${alignr}${downspeed ' + interface + '}/s${color}',
        '|   |   +-- Total ${color2}${alignr}${totaldown ' + interface + '}${color}',
        '|   +-- Upload ${color2}${alignr}${upspeed ' + interface + '}/s${color}',
        '|       +-- Total ${color2}${alignr}${totalup ' + interface + '}${color}',
    ])


def owned_process(pid, config):
    try:
        process = PROC / str(pid)
        arguments = (process / 'cmdline').read_bytes().split(b'\0')
        return (process.stat().st_uid == os.getuid()
                and Path(os.fsdecode(arguments[0])).name == 'conky'
                and os.fsencode(config) in arguments)
    except (OSError, ValueError, IndexError):
        return False


def render_config(width, height):
    values = layout(width, height, os.environ.get('CONKY_SYSTEM_SCALE'))
    try:
        name = platform.freedesktop_os_release().get('PRETTY_NAME', 'Linux')
    except OSError:
        name = 'Linux'
    name = ''.join(char for char in name if char.isprintable() and char not in '$\\{}')[:36]
    replacements = {**values, 'os_name': name, 'helper': shlex.quote(HELPER)}
    text = TEMPLATE.read_text()
    for key, value in replacements.items():
        text = text.replace('@' + key.upper() + '@', str(value))
    return text


def runtime_dir():
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    base = Path(runtime) if runtime else Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))
    directory = base / 'syslinuxos-conky-system'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_uid != os.getuid():
        raise RuntimeError('The runtime directory must belong to the current user.')
    directory.chmod(0o700)
    return directory


def read_pid(path):
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return 0


def control(action):
    directory = runtime_dir()
    config = directory / 'conkyrc-system.conf'
    pidfile = directory / 'conky.pid'
    with (directory / 'control.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        pid = read_pid(pidfile)
        running = owned_process(pid, config)
        if action == 'status':
            print('Conky-System is running.' if running else 'Conky-System is stopped.')
            return 0 if running else 1
        if action == 'stop':
            if running:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                for _ in range(20):
                    if not owned_process(pid, config):
                        break
                    time.sleep(0.05)
                if owned_process(pid, config):
                    raise RuntimeError('Conky-System has not stopped yet; try again.')
            pidfile.unlink(missing_ok=True)
            print('Conky-System stopped.')
            return 0
        if running:
            print('Conky-System is already running.')
            return 0
        config.write_text(render_config(*resolution()))
        with (directory / 'conky.log').open('w') as log:
            process = subprocess.Popen(['conky', '--config', str(config)], stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        time.sleep(0.4)
        if process.poll() is not None:
            raise RuntimeError('Conky could not start. See ' + str(directory / 'conky.log'))
        pidfile.write_text(str(process.pid))
        print('Conky-System started.')
        return 0


def main():
    parser = argparse.ArgumentParser(description='Start or stop the Conky-System desktop monitor.')
    parser.add_argument('action', choices=['start', 'stop', 'status', 'network'])
    arguments = parser.parse_args()
    try:
        if arguments.action == 'network':
            print(network_text())
            return 0
        return control(arguments.action)
    except (OSError, RuntimeError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
