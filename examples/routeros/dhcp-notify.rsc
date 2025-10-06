# RouterOS DHCP Event Notification Script
# This script sends DHCP lease events to the router-events service with hostname and interface lookup
# Replace 'your-server' with your actual server IP address

/system script add name=dhcp-notify source=":local mac \$leaseActMAC; :local ip \$leaseActIP; :local dhcpServer \$leaseServerName; :local interface \"\"; :local eventType \"dhcp\"; :local host \"\"; :do {:set interface [/ip dhcp-server get [find name=\$dhcpServer] interface]} on-error={:set interface \"\"}; :do {:local leaseId [/ip dhcp-server lease find mac-address=\$mac]; :if ([:len \$leaseId] > 0) do={:set host [/ip dhcp-server lease get \$leaseId host-name]}} on-error={:set host \"\"}; /tool fetch url=\"http://your-server:13959/api/events\" http-method=post http-data=\"{\\\"type\\\":\\\"\$eventType\\\",\\\"dhcpServer\\\":\\\"\$dhcpServer\\\",\\\"interface\\\":\\\"\$interface\\\",\\\"mac\\\":\\\"\$mac\\\",\\\"ip\\\":\\\"\$ip\\\",\\\"host\\\":\\\"\$host\\\"}\" http-header-field=\"Content-Type: application/json\" keep-result=no"

# To trigger this script on DHCP lease events, add it to your DHCP server configuration:
# /ip dhcp-server set [find name="your-dhcp-server"] lease-script=dhcp-notify
