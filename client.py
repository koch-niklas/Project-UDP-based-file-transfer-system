#Usage: python udp_file_transfer.py --file path/to/file --WindowSize 5

import socket
import os
import argparse
import random #to simulate packet loss
import zlib #to let python handle checksum (crc32) calculation
import time #to calculate transmision duration

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5959
BUFFER_SIZE = 4096
TIMEOUT = 0.5 #500 milliseconds
LOSS_PERCENT = 1 #1-5 for file transfer?


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--WindowSize", type=int, required=True)
    parser.add_argument("--file", required=True)
    return parser.parse_args()


def setup_socket():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(TIMEOUT) #needed to break the loop below. without, we would get stuck on an infinite loop
    return client_socket


def prepare_packets(file_path):
    packets = [] #array to store ALL packets in. we will fill it before transmission
    with open(file_path, "rb") as f: #same technique to read the chunks as before
        seq = 0
        while chunk := f.read(BUFFER_SIZE):
            packets.append((seq, chunk)) #instead of transmitting the chunks, we are storing them in this array with the respective SEQ number
            seq += 1
    return packets


def perform_handshake(sock, filename, filesize, total_packets):
    handshake = f"HELO|{filename}|{filesize}|{total_packets}" #create handshake package

    while True:
        sock.sendto(handshake.encode(), (SERVER_IP, SERVER_PORT))
        try:
            response, _ = sock.recvfrom(1000) #wait for the handshake response from server
            if response.decode() == "HELO OK":
                print("Handshake successful, starting file transfer!")
                return #break from the loop
        except socket.timeout:
            print("Handshake timed out, resending...")


def send_window(sock, packets, base, next_seq, window_size):
    packets_set = 0
    packets_lost = 0

    while next_seq < base + window_size and next_seq < len(packets):
        seq, chunk = packets[next_seq] #reading the current packet from the packets array
        checksum = zlib.crc32(chunk) #letting zlib library handle the checksum creation
        packet = f"{seq}|{checksum}|".encode() + chunk #building our packets the same way as before, now with checksum between sequence number and data chunk
        if random.uniform(0, 100) >= LOSS_PERCENT:
            sock.sendto(packet, (SERVER_IP, SERVER_PORT))
            packets_set += 1
        else:
            print(f"Simulated loss of packet {seq}")
            packets_lost += 1
        next_seq += 1 #we move on to the next packet, regardless if the server acknowledged the packet or not! (or in this case, if we sent the packet or not)

    return next_seq, packets_set, packets_lost


def receive_ack(sock, base):
    try:
        data, _ = sock.recvfrom(1024)
        ack = int(data.decode())
        if ack >= base:
            return ack
        return base
    except socket.timeout:
        return None


def send_file(sock, packets, window_size, filesize):
    total_packets_sent = 0
    total_packets_lost = 0
    total_retransmissions = 0

    base = 0 #this is the start of the sliding window. it will hold the last ACKed packet during transmission
    next_seq = 0 #used as the index of our packets[] array
    start_time = time.time()

    while base < len(packets): #while we still have an unACKed packet
        next_seq, sent, lost = send_window(sock, packets, base, next_seq, window_size)
        total_packets_sent += sent
        total_packets_lost += lost

        ack = receive_ack(sock, base)

        if ack is None:
            next_seq = base # Reset next_seq to base to resend unacknowledged packets. this means we are sliding the window BACK to the unacknowledged packet and start again from there. base is the last ACKed packet
            total_retransmissions += 1
        else:
            base = ack

    #at this point, we transfered the file, so send EOF marker
    sock.sendto(b"EOF", (SERVER_IP, SERVER_PORT))
    duration = time.time() - start_time
    throughput = filesize / duration
    print(f"\nFile sent successfully.")
    print(f"Packets sent: {total_packets_sent}")
    print(f"Packets lost (simulated): {total_packets_lost}")
    print(f"Retransmissions: {total_retransmissions}")
    print(f"Transfer time: {duration:.2f}s")
    print(f"Throughput: {throughput/1024:.2f} KB/s")


def main():
    args = parse_args()
    file_path = os.path.abspath(args.file)

    filename = os.path.basename(file_path)
    filesize = os.path.getsize(file_path)

    packets = prepare_packets(file_path)
    sock = setup_socket()

    perform_handshake(sock, filename, filesize, len(packets))
    send_file(sock, packets, args.WindowSize, filesize)

    sock.sendto(b"BYE", (SERVER_IP, SERVER_PORT))
    sock.close()


if __name__ == "__main__":
    main()
