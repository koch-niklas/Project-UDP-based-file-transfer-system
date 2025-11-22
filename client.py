#Usage: python udp_file_transfer.py --file path/to/file --WindowSize 5

import socket
import os
import argparse
import random #to simulate packet loss
import zlib #to let python handle checksum (crc32) calculation
import time #to calculate transmission duration

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5959
BUFFER_SIZE = 4096
TIMEOUT = 0.5  # 500 milliseconds
LOSS_PERCENT = 1 #1-5 for file transfer?

def GetFile(file_path):
    file_path = os.path.abspath(os.path.expanduser(file_path))
    if not os.path.isfile(file_path):
        print("File not found.")
    return os.path.basename(file_path)  #format filepath so that python that read it

def main():
    #some useful metrics:
    total_packets_sent = 0
    total_packets_lost = 0
    total_retransmissions = 0

    parser = argparse.ArgumentParser()
    parser.add_argument('--WindowSize', type=int, required=True)
    parser.add_argument('--file', required=True)
    arg = parser.parse_args()
    window_size = arg.WindowSize
    file_path = arg.file
    filename = GetFile(file_path)
    filesize = os.path.getsize(file_path) #to send in the handshake

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(TIMEOUT) #needed to break the loop below. without, we would get stuck on an infinite loop

    # Prepare packets
    packets = [] #array to store ALL packets in. we will fill it before transmission
    with open(file_path, "rb") as f: #same technique to read the chunks as before
        seq = 0
        while chunk := f.read(BUFFER_SIZE):
            packets.append((seq, chunk)) #instead of transmitting the chunks, we are storing them in this array with the respective SEQ number
            seq += 1
    
    base = 0 #this is the start of the sliding window. it will hold the last ACKed packet during transmission
    next_seq = 0 #used as the index of our packets[] array

    handshake = f"HELO|{filename}|{filesize}|{len(packets)}" #create handshake package
    client_socket.sendto(handshake.encode(), (SERVER_IP, SERVER_PORT)) #send handshake package to server

    while True: #wait for the handshake response from server
        try:
            response, _ = client_socket.recvfrom(1000)
            handshake = response.decode()
            if handshake == "HELO OK":
                print ("Handshake successful, starting file tranfer!")
                break #break from the loop, go to the next one
            else:
                print("Handshake unsuccessful")
                return #try loop until handshake is successful
        except socket.timeout:
            print("Handshake timed out, resending...")
            client_socket.sendto(handshake.encode(), (SERVER_IP, SERVER_PORT)) #resending same handshake until server accepts

    #handshake done, transmission starts
    start_time = time.time()      
    while base < len(packets): #while we still have an unACKed packet
        while next_seq < base + window_size and next_seq < len(packets): #we are sending as many packets as the window size indicates AND as long as we didnt reach the last index. IF we reached the end of the sliding window (or the last packet index), we wait for ACKs
            seq, chunk = packets[next_seq] #reading the current packet from the packets array
            checksum = zlib.crc32(chunk) #letting zlib library handle the checksum creation
            packet = f"{seq}|{checksum}|".encode() + chunk #building our packets the same way as before, now with checksum between sequence number and data chunk
            if random.uniform(0, 100) >= LOSS_PERCENT:
                client_socket.sendto(packet, (SERVER_IP, SERVER_PORT))
                total_packets_sent += 1
            else:
                print(f"Simulated loss of packet {seq}")
                total_packets_lost += 1
            next_seq += 1 #we move on to the next packet, regardless if the server acknowledged the packet or not! (or in this case, if we sent the packet or not)
        #at this point, all packets from the window have been transmitted, so now we wait for the ACKs
        try:
            ack_data, _ = client_socket.recvfrom(1024)
            ack = int(ack_data.decode())
            if ack >= base:
                base = ack #+ 1  #we are now moving the window forward
        except socket.timeout:
            # Reset next_seq to base to resend unacknowledged packets. this means we are sliding the window BACK to the unacknowledged packet and start again from there. base is the last ACKed packet
            next_seq = base
            total_retransmissions += 1
    #at this point, we transfered the file, so send EOF marker
    client_socket.sendto(b"EOF", (SERVER_IP, SERVER_PORT))
    total_duration = time.time() - start_time
    troughput = filesize / total_duration
    print(f"File '{filename}' sent successfully.")
    print(f"File size in bytes: {filesize}")
    print(f"Packets generated: {len(packets)}")
    print(f"Packets sent: {total_packets_sent}")
    print(f"Packets lost: {total_packets_lost}")
    print(f"Retransmitted Packets: {total_retransmissions}")
    print(f"Total transmission time: {total_duration:.2f} seconds")
    print(f"Throughput: {troughput/1024:.2f} KB/s")
    
    #send final handshake:
    client_socket.sendto(b"BYE", (SERVER_IP, SERVER_PORT)) #send final handshake package to server to close the connection
    client_socket.close()

if __name__ == "__main__":
    main()
