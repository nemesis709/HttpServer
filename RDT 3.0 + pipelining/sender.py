import socket
from PASender import *
from logHandler import *
import sys
import struct
import time

BUF_SIZE = 1024

def rdt_1_0(SERVER_IP, source_file, log_file):
    logger = logHandler()
    logger.startLogging(log_file)
    seq = 0

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sender = PASender(soc=client_socket,config_file="config.txt")

        with open(source_file, 'rb') as f:
            filecontent = f.read(BUF_SIZE)
            while filecontent:
                sender.sendto_bytes(filecontent, (SERVER_IP, 10090))
                logger.writePkt(seq,logHandler.SEND_DATA)
                seq = seq + 1
                filecontent = f.read(BUF_SIZE)
        
        sender.sendto_bytes(b'', (SERVER_IP, 10090))
        logger.writeEnd()

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

def rdt_2_2(SERVER_IP, source_file, log_file):
    logger = logHandler()
    logger.startLogging(log_file)
    seq = 0
    ack = 0

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sender = PASender(soc=client_socket,config_file="config.txt")

        with open(source_file, 'rb') as f:
            filecontent = f.read(BUF_SIZE)

            while filecontent:
                #create header
                header = struct.Struct('I I %ds'%(BUF_SIZE))
                packet = header.pack(seq,checksum(filecontent),filecontent)
                sender.sendto_bytes(packet, (SERVER_IP, 10090))
                if(ack!=seq):
                    logger.writePkt(seq,logHandler.SEND_DATA)

                #recv data
                data, addr = client_socket.recvfrom(BUF_SIZE)
                reply = struct.Struct('i i')
                packet = reply.unpack(data)

                #SUCCESS_ACK
                if(packet[0]==seq):
                    logger.writePkt(seq,logHandler.SUCCESS_ACK)
                    ack=seq
                    seq = seq + 1
                    filecontent = f.read(BUF_SIZE)
                else:
                    ack=seq
                    logger.writePkt(seq,logHandler.WRONG_SEQ_NUM)
                    logger.writePkt(seq,logHandler.SEND_DATA_AGAIN)
        
        
        while True:
            client_socket.sendto(b'fin', (SERVER_IP, 10090))
            data, addr = client_socket.recvfrom(BUF_SIZE)
            if(data==b'fin'):
                break

        logger.writeEnd()

def rdt_3_0(SERVER_IP, source_file, log_file):
    logger = logHandler()
    logger.startLogging(log_file)
    seq = 0
    ack = 0

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_socket.settimeout(0.01)
        sender = PASender(soc=client_socket,config_file="config.txt")

        with open(source_file, 'rb') as f:
            filecontent = f.read(BUF_SIZE)

            while filecontent:
                #create header
                header = struct.Struct('I I %ds'%(BUF_SIZE))
                packet = header.pack(seq,checksum(filecontent),filecontent)
                sender.sendto_bytes(packet, (SERVER_IP, 10090))
                if(ack!=seq):
                    logger.writePkt(seq,logHandler.SEND_DATA)

                try:
                    #recv data
                    data, addr = client_socket.recvfrom(BUF_SIZE)
                    reply = struct.Struct('i i')
                    packet = reply.unpack(data)

                    #SUCCESS_ACK
                    if(packet[0]==seq):
                        logger.writePkt(seq,logHandler.SUCCESS_ACK)
                        ack=seq
                        seq = seq + 1
                        filecontent = f.read(BUF_SIZE)
                    else:
                        ack=seq
                        logger.writePkt(seq,logHandler.WRONG_SEQ_NUM)
                        logger.writePkt(seq,logHandler.SEND_DATA_AGAIN)

                except socket.timeout:
                    ack=seq
                    logger.writeTimeout(seq)
                    logger.writePkt(seq,logHandler.SEND_DATA_AGAIN)

        
        while True:
            client_socket.sendto(b'fin', (SERVER_IP, 10090))
            data, addr = client_socket.recvfrom(BUF_SIZE)
            if(data==b'fin'):
                break

        logger.writeEnd()

def packet_window(sender,filelist,SERVER_IP,client_socket,logger,window_size,seq,send):
    ack = seq
    #send
    for i in range(0,window_size):
        header = struct.Struct('I I %ds'%(BUF_SIZE))
        packet = header.pack(seq+i,checksum(filelist[seq+i]),filelist[seq+i])
        sender.sendto_bytes(packet, (SERVER_IP, 10090))
        if((seq+i==ack)and(send==False)):
            logger.writePkt(seq+i,logHandler.SEND_DATA_AGAIN)
            send = True
        else:
            logger.writePkt(seq+i,logHandler.SEND_DATA)

    time.sleep(0.001)

    #recv
    for i in range(0,window_size):
        try:
            #recv data
            data, addr = client_socket.recvfrom(BUF_SIZE)
            reply = struct.Struct('i i')
            packet = reply.unpack(data)

            #SUCCESS_ACK
            if(packet[0]==ack):
                logger.writePkt(ack,logHandler.SUCCESS_ACK)
                send=True
                ack+= 1
            else:
                logger.writePkt(ack,logHandler.WRONG_SEQ_NUM)
                send=False
                pass

        except socket.timeout:
            logger.writeTimeout(ack)
            send=False
            pass
        
    return (ack,send)

def rdt_3_P(SERVER_IP, window_size,source_file, log_file):
    window_size = int(window_size)
    logger = logHandler()
    logger.startLogging(log_file)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_socket.settimeout(0.01)
        sender = PASender(soc=client_socket,config_file="config.txt")

        filelist=[]
        with open(source_file, 'rb') as f:
            filecontent = f.read(BUF_SIZE)
            while filecontent:
                filelist.append(filecontent)
                filecontent = f.read(BUF_SIZE)

        seq = 0 
        ack = 0
        send = True

        while(1):
            if(window_size<len(filelist)-seq):
                for i in range(0,(len(filelist)-seq)//window_size):
                    ack,send = packet_window(sender,filelist,SERVER_IP,client_socket,logger,window_size,seq,send)
                    seq = ack
                    if not send:
                        break

            else:
                left = (len(filelist)-seq)%window_size
                ack,send = packet_window(sender,filelist,SERVER_IP,client_socket,logger,left,seq,send)
                seq=ack

            if((ack==len(filelist))and(send==True)):
                break

        while True:
            client_socket.sendto(b'fin', (SERVER_IP, 10090))
            data, addr = client_socket.recvfrom(BUF_SIZE)
            if(data==b'fin'):
                break
        logger.writeEnd()

def main():
    if len(sys.argv) ==5:
        # rdt_1_0(sys.argv[1],sys.argv[3],sys.argv[4])
        # rdt_2_2(sys.argv[1],sys.argv[3],sys.argv[4])
        # rdt_3_0(sys.argv[1],sys.argv[3],sys.argv[4])
        rdt_3_P(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4])

    else:
        print("Usage: python sender.py <receiver'sIPaddress> <windowsize> <sourcefilename> <logfilename>")
if __name__ == "__main__":
	main()