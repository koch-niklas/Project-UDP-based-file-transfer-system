#Usage: python client.py --File path/to/file --WindowSize 5 --PacketLoss 1 --Timeout 0.5

import socket
import os
import argparse
import random #to simulate packet loss
import zlib #to let python handle checksum (crc32) calculation
import time #to calculate transmision duration
import logging #to let python handle logging to file

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5959
BUFFER_SIZE = 4096

def ImprovedLogging(port):
    LogFilename = f"client_{port}.log"
    logging.basicConfig(  #moving the log config into here, so each client has is its own log
        filename = LogFilename,
        level=logging.INFO,
        format = "%(asctime)s [Client] %(levelname)s: %(message)s"
)


def WriteProgress(base, total): #new function to display progress
    progress = base / total
    length = 30 #chars on screen
    done = int(progress * length)
    bar = "#" * done + "-" * (length - done) # the hashtag represents full bar, the line empty space
    percent = int(progress *100)
    print(f"\r{bar} {percent}% ", end = "", flush = True)


def LogConsole(message): #replace any print command with this one, so we have console output + the same line in the logfile
    print(message)
    logging.info(message)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--WindowSize", type=int, required=True)
    parser.add_argument("--File", required=True)
    parser.add_argument("--PacketLoss", type=int, required=True)
    parser.add_argument("--Timeout" , type=float, required=True)
    return parser.parse_args()


def setup_socket(timeout):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(timeout) #needed to break the loop below. without, we would get stuck on an infinite loop
    client_socket.bind(("", 0)) # without this, python will only assign a port when we send the first message. Bind to 0 so python assigns a dynamic port
    return client_socket


def prepare_packets(file_path):
    packets = [] #array to store ALL packets in. we will fill it before transmission
    try: #moving process into this try expression in order to catch and log any error
        with open(file_path, "rb") as f: #same technique to read the chunks as before
            seq = 0
            while chunk := f.read(BUFFER_SIZE):
                packets.append((seq, chunk)) #instead of transmitting the chunks, we are storing them in this array with the respective SEQ number
                seq += 1
    except Exception as exception:
        LogConsole(f"Failed to read {file_path}: {exception}")
        raise

    return packets


def perform_handshake(sock, filename, filesize, total_packets):
    handshake = f"HELO|{filename}|{filesize}|{total_packets}" #create handshake package

    while True:
        sock.sendto(handshake.encode(), (SERVER_IP, SERVER_PORT))
        try:
            response, _ = sock.recvfrom(1000) #wait for the handshake response from server
            if response.decode() == "HELO OK":
                LogConsole("Handshake successful, starting file transfer!")
                return #break from the loop
        except socket.timeout:
            LogConsole("Handshake timed out, resending...")
            raise
            

def send_window(sock, packets, base, next_seq, window_size, packetloss):
    packets_set = 0 #during this windows
    packets_lost = 0 #during this window

    while next_seq < base + window_size and next_seq < len(packets): #while we still have unACKed packet in this window AND in the file
        seq, chunk = packets[next_seq] #reading the current packet from the packets array
        checksum = zlib.crc32(chunk) #letting zlib library handle the checksum creation
        packet = f"{seq}|{checksum}|".encode() + chunk #building our packets the same way as before, now with checksum between sequence number and data chunk
        if random.uniform(0, 100) >= packetloss:
            sock.sendto(packet, (SERVER_IP, SERVER_PORT))
            packets_set += 1
        else:
            logging.info(f"Simulated loss of packet {seq}") #just log this info instead of printing it (interferes with progress bar)
            packets_lost += 1
        next_seq += 1 #we move on to the next packet, regardless if the server acknowledged the packet or not! (or in this case, if we sent the packet or not)

    return next_seq, packets_set, packets_lost


def receive_ack(sock, base):
    try:
        data, _ = sock.recvfrom(1024)
        ack = int(data.decode())
        if ack >= base:
            return ack #we move the window forward
        return base #we move the window backward
    except socket.timeout:
        return None


def send_file(sock, packets, window_size, filesize, packetloss):
    # some useful metrics:
    total_packets_sent = 0
    total_packets_lost = 0
    total_retransmissions = 0

    base = 0 #this is the start of the sliding window. it will hold the last ACKed packet during transmission
    next_seq = 0 #used as the index of our packets[] array
    start_time = time.time() #to calculate the duration

    while base < len(packets): #while we still have an unACKed packet
        next_seq, sent, lost = send_window(sock, packets, base, next_seq, window_size, packetloss) #send the window of packets
        total_packets_sent += sent #for metrics
        total_packets_lost += lost #for metrics

        ack = receive_ack(sock, base) #determines if we can move the window forward

        if ack is None:
            next_seq = base # Reset next_seq to base to resend unacknowledged packets. this means we are sliding the window BACK to the unacknowledged packet and start again from there. base is the last ACKed packet
            total_retransmissions += 1
        else:
            base = ack + 1
        #print progress bar
        WriteProgress(base, len(packets))
    #at this point, we transfered the file, so send EOF marker
    WriteProgress(len(packets), len(packets)) #fill the progress bar completely
    print() #print a new line
    sock.sendto(b"EOF", (SERVER_IP, SERVER_PORT))
    duration = time.time() - start_time
    throughput = filesize / duration
    LogConsole(f"\nFile sent successfully.")
    LogConsole(f"Packets sent: {total_packets_sent}")
    LogConsole(f"Packets lost (simulated): {total_packets_lost}")
    LogConsole(f"Window Size: {window_size}")
    LogConsole(f"Retransmissions: {total_retransmissions}")
    LogConsole(f"Transfer time: {duration:.2f}s")
    LogConsole(f"Throughput: {throughput/1024:.2f} KB/s")


def main():
    args = parse_args()

    timeout = args.Timeout
    PacketLoss = args.PacketLoss
    file_path = os.path.abspath(args.File)    
    filename = os.path.basename(file_path)
    filesize = os.path.getsize(file_path)

    sock = setup_socket(timeout) #setup socket first as we need to know the dynamic port for the logfile name
    AssignedPort = sock.getsockname()[1] #get dynamically assigned port
    ImprovedLogging(AssignedPort) #create the logfile with port number
    LogConsole(f"Starting transfer of {filename}. Size: {filesize} bytes")

    packets = prepare_packets(file_path) #packets holds all packets incl. sequence number

    try: #moving process into this try expression in order to catch and log any error
        perform_handshake(sock, filename, filesize, len(packets))
        send_file(sock, packets, args.WindowSize, filesize, PacketLoss)
        sock.sendto(b"BYE", (SERVER_IP, SERVER_PORT)) #closing handshake
    except Exception as exception:
        LogConsole(f"Error, closing! {exception}")
    finally:
        sock.close()
        LogConsole("Client socket closed")


if __name__ == "__main__":
    main()
