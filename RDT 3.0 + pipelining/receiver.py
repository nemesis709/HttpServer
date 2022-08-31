import socket
import sys
import struct
from logHandler import *

BUF_SIZE = 1024

def rdt_1_0(source_file):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', 10090))

    with open(source_file, 'wb+') as f:
        while True:
            data, addr = server_socket.recvfrom(BUF_SIZE)
            if not data:
                break
            
            data = data.rstrip(b'\x00')
            f.write(data)

    f.close()

def carry_around_add(a, b):
    c = a + b
    return (c & 0xffff) + (c >> 16)

def checksum(msg):
    list=[]
    for b in msg:
        list.append(chr(b))
    if(len(list)%2==1):
        list += "\x00"
    s = 0
    for i in range(0, len(list), 2):
        w = ord(list[i]) + (ord(list[i+1]) << 8)
        s = carry_around_add(s, w)
    return ~s & 0xffff

def rdt_2_2(source_file, log_file):
    logger = logHandler()
    logger.startLogging(log_file)
    seq = -1

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', 10090))

    with open(source_file, 'wb+') as f:
        while True:
            data, addr = server_socket.recvfrom(BUF_SIZE+8)
            if(data==b'fin'):
                server_socket.sendto(b'fin', addr)
                break

            header = struct.Struct('I I %ds'%(BUF_SIZE))
            packet = header.unpack(data)

            if(checksum(packet[2])==packet[1]):
                seq = int(packet[0])
                logger.writeAck(seq,logHandler.SEND_ACK)
                data = packet[2]
                f.write(data)

            else:
                logger.writeAck(seq+1,logHandler.CORRUPTED)
                logger.writeAck(seq,logHandler.SEND_ACK_AGAIN)
                
            reply = struct.Struct('i i')
            packet = reply.pack(seq,0)
            server_socket.sendto(packet, addr)

        f.close()
        logger.writeEnd()

def rdt_3_0(source_file, log_file):
    logger = logHandler()
    logger.startLogging(log_file)
    seq = -1

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', 10090))

    with open(source_file, 'wb+') as f:
        while True:
            data, addr = server_socket.recvfrom(BUF_SIZE+8)
            if(data==b'fin'):
                server_socket.sendto(b'fin', addr)
                break   

            header = struct.Struct('I I %ds'%(BUF_SIZE))
            packet = header.unpack(data)

            if(checksum(packet[2])==packet[1]):
                seq = int(packet[0])
                logger.writeAck(seq,logHandler.SEND_ACK)
                data = packet[2].rstrip(b'\x00')
                f.write(data)

            else:
                logger.writeAck(seq+1,logHandler.CORRUPTED)
                logger.writeAck(seq,logHandler.SEND_ACK_AGAIN)
                
            reply = struct.Struct('i i')
            packet = reply.pack(seq,0)
            server_socket.sendto(packet, addr)

    f.close()
    logger.writeEnd()

def rdt_3_P(source_file, log_file):
    logger = logHandler()
    logger.startLogging(log_file)
    seq = -1

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', 10090))

    with open(source_file, 'wb+') as f:
        while True:
            data, addr = server_socket.recvfrom(BUF_SIZE+8)
            if(data==b'fin'):
                server_socket.sendto(b'fin', addr)
                break

            header = struct.Struct('I I %ds'%(BUF_SIZE))
            packet = header.unpack(data)

            if((checksum(packet[2])==packet[1]) and (seq+1 == int(packet[0]))):
                seq += 1
                logger.writeAck(seq,logHandler.SEND_ACK)
                data = packet[2]
                f.write(data)

            else:
                logger.writeAck(seq+1,logHandler.CORRUPTED)
                logger.writeAck(seq,logHandler.SEND_ACK_AGAIN)
                

            reply = struct.Struct('i i')
            packet = reply.pack(seq,0)
            server_socket.sendto(packet, addr)

    f.close()
    logger.writeEnd()

def main():
    if len(sys.argv) ==3:
        # rdt_1_0(sys.argv[1])
        # rdt_2_2(sys.argv[1],sys.argv[2])
        # rdt_3_0(sys.argv[1],sys.argv[2])
        rdt_3_P(sys.argv[1],sys.argv[2])
    
    else:
        print("Usage: python receiver.py <resultfilename> <logfilename>")
if __name__ == "__main__":
	main()