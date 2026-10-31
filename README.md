# Conky-System

A transparent desktop monitor for SysLinuxOS and Debian, with a tree layout
inspired by [MX-BBQdigital](https://github.com/MX-Linux/mx-conky-data/tree/master/themes/MX-BBQdigital).
MX Linux credits an earlier BBQLinux theme for the original layout.

Conky-System uses the blue, light blue and pale text colors of the SysLinuxOS
Conky themes. It displays the operating system, kernel, memory and swap,
CPU load, disk activity, free storage, busiest processes and network traffic.
The network section follows the default route automatically.

## Install

With the SysLinuxOS APT repository configured:

```sh
sudo apt update
sudo apt install syslinuxos-conky-system
```

Or download the package and install it with APT:

```sh
sudo apt install ./syslinuxos-conky-system_0.1.0_all.deb
```

The shared `syslinuxos-conky-menu` dependency supplies the Conky submenu and
icon. It must also be available when installing a downloaded package.

## Use

Open **System Tools > Conky > Start Conky-System** or **Stop Conky-System**.
Italian menu entries are **Avvia Conky-System** and **Ferma Conky-System**.

The same controls are available in a terminal:

```sh
conky-system start
conky-system stop
conky-system status
```

Font size, width, spacing and position scale automatically to the active
primary monitor. Restart Conky-System after changing the monitor resolution.
Its top-right position is the same as Conky Window. Use the two themes as alternatives.

Set a scale manually or select a network interface:

```sh
CONKY_SYSTEM_SCALE=1.2 conky-system start
CONKY_NET_INTERFACE=enp3s0 conky-system start
```

Stop an existing instance before changing these options. Values are inherited
by the network helper. With no fixed interface, route changes are detected
within five seconds. No external IP or location service is contacted.

The editable template is `/etc/conky/conky-system.conf`; edits are preserved
across package upgrades. A compositor is recommended for full transparency.

## Build

```sh
bash build-deb.sh
```

The package is produced in `dist/`. Dependencies are listed in its metadata.

## License

Copyright 2026 Franco Conidi. GPL-3.0-or-later; see [LICENSE](LICENSE).
