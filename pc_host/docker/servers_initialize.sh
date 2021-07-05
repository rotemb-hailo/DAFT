#!/bin/bash
set -e

if [ "$#" -ne 2 ]; then
    echo "Using default values"
fi

nfs_workspace=${1:-/home/tester/daft}
network_interface=${1:-eno1}

# DNS
echo "Initializing DNS"
sudo sh -c "echo "interface=$network_interface" >> /etc/dnsmasq.conf"
sudo sh -c 'echo "dhcp-range=192.168.30.2,192.168.30.254,10m" >> /etc/dnsmasq.conf'

# TFTP
echo "Initializing TFTP"
touch /etc/xinetd.d/tftp
echo "service tftp
{
protocol        = udp
port            = 69
socket_type     = dgram
wait            = yes
user            = nobody
server          = /usr/sbin/in.tftpd
server_args     = /daft
disable         = no
}" >/etc/xinetd.d/tftp

# NFS
echo "Initializing NFS"
echo "$nfs_workspace 192.168.30.0/24(crossmnt,rw,root_squash,anonuid=1001,anongid=100,sync,no_subtree_check)
/daft/support_img 192.168.30.0/24(crossmnt,rw,root_squash,anonuid=1001,anongid=100,sync,no_subtree_check)
/daft/bbb_fs 192.168.30.0/24(crossmnt,ro,root_squash,anonuid=1001,anongid=100,sync,no_subtree_check)
" >/etc/exports
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server
sudo systemctl enable nfs-kernel-server
