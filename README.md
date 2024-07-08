# panos-versions

This repository contains a JSON file with information about the latest available PAN-OS versions for Palo Alto Networks firewalls.

Overview
A local script on a user's machine connects to the firewall using the PAN-OS XML API to check for new PAN-OS versions. If a new version is found, the script updates the JSON file with the latest version information and pushes the changes to this GitHub repository. 

Note that this repository only includes the JSON file; the script itself is not included.
