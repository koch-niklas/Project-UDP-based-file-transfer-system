#Usage: python udp_file_transfer.py --file path/to/file --WindowSize 5

import socket
import os
import argparse
import random #to simulate packet loss

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
    parser = argparse.ArgumentParser()
    parser.add_argument('--WindowSize', type=int, required=True)
    parser.add_argument('--file', required=True)
    arg = parser.parse_args()
    window_size = arg.WindowSize
    file_path = arg.file
    filename = GetFile(file_path)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #open socket at hardcoded port
    client_socket.settimeout(TIMEOUT) #needed to break the loop below. without, we would get stuck on an infinite loop
    # Send filename first
    client_socket.sendto(filename.encode(), (SERVER_IP, SERVER_PORT))
    # Prepare packets
    packets = [] #array to store ALL packets in. we will fill it before transmission
    with open(file_path, "rb") as f: #same technique to read the chunks as before
        seq = 0
        while chunk := f.read(BUFFER_SIZE):
            packets.append((seq, chunk)) #instead of transmitting the chunks, we are storing them in this array with the respective SEQ number
            seq += 1
    base = 0 #this is the start of the sliding window. it will hold the last ACKed packet during transmission
    next_seq = 0 #used as the index of our packets[] array

    while base < len(packets): #while we still have an unACKed packet
        while next_seq < base + window_size and next_seq < len(packets): #we are sending as many packets as the window size indicates AND as long as we didnt reach the last index. IF we reached the end of the sliding window (or the last packet index), we wait for ACKs
            seq, chunk = packets[next_seq] #reading the current packet from the packets array
            packet = f"{seq}|".encode() + chunk #building our packets the same way as before

            if random.uniform(0, 100) >= LOSS_PERCENT:
                client_socket.sendto(packet, (SERVER_IP, SERVER_PORT))
            else:
                print(f"Simulated loss of packet {seq}")
            next_seq += 1 #we move on to the next packet, regardless if the server acknowledged the packet or not! (or in this case, if we sent the packet or not)
        #at this point, all packets from the window have been transmitted, so now we wait for the ACKs
        try:
            ack_data, _ = client_socket.recvfrom(1024)
            ack = int(ack_data.decode())
            if ack >= base:
                base = ack #+ 1  #we are now moving the window forward
        except socket.timeout:
            print("Timeout, resending unacknowlegded Packets")
            # Reset next_seq to base to resend unacknowledged packets. this means we are sliding the window BACK to the unacknowledged packet and start again from there. base is the last ACKed packet
            next_seq = base
    #at this point, we transfered the file, so send EOF marker
    client_socket.sendto(b"EOF", (SERVER_IP, SERVER_PORT))
    print(f"File '{filename}' sent successfully.")
    client_socket.close()

if __name__ == "__main__":
    main()
