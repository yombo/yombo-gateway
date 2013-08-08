import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
toaddr = ('localhost', 9999)
s.bind(('', 9998))
s.sendto("test", toaddr)

s.sendto("""xpl-cmnd
{
hop=1
source=xpl-xplhal.myhouse
target=acme-cm12.server
}
x10.basic
{
command=dim
device=a1
level=75
}
""", toaddr)

s.sendto("""xpl-cmnd
{
hop=1
source=xpl-xplhal.myhouse
target=acme-cm12.server
}
x10.basic
{
command=dim
device=a1
level=75
}
""", toaddr)
