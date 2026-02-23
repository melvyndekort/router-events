# RouterOS Syslog Configuration for DHCP Events
# This configuration sends DHCP events to Vector via syslog

# Configure syslog action to send to Vector
/system logging action
add name=remote remote=<vector-server-ip> remote-port=514 target=remote

# Enable DHCP server logging
/system logging
add action=remote topics=dhcp

# Replace <vector-server-ip> with your Vector server IP address
