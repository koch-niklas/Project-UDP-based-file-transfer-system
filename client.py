#Usage: python udp_file_transfer.py --file path/to/file

import socket
import os
import argparse

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5959
BUFFER_SIZE = 4096
TIMEOUT = 0.5  # 500 milliseconds

def GetFile():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True)
    arg = parser.parse_args()   #get --file argument from caller
    file_path = arg.file
    file_path = os.path.abspath(os.path.expanduser(file_path))
    if not os.path.isfile(file_path):
        print("File not found.")
    return os.path.basename(file_path), file_path  #format filepath so that python that read it

def main():
    filename, file_path = GetFile()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #open socket at hardcoded port
    client_socket.settimeout(TIMEOUT) #needed to break the loop below. without, we would get stuck on an infinite loop
    # Send filename first
    client_socket.sendto(filename.encode(), (SERVER_IP, SERVER_PORT))
    # Send file data , now more reliable
    seq_num = 0 #used to keep track. ofc we start with 0 :)
    with open(file_path, "rb") as f: #rb = read binary mode, f is the file object
        while True: #repeat indefinetely until break
            chunk = f.read(BUFFER_SIZE) #same thing as before
            if not chunk:
                break
            packet = f"{seq_num}|".encode() + chunk #the new packet not only includes the chunk(raw data) but starts with the sequence number. f234 for example, followed by the | which indicates the start of the chunk
            while True: #repeat indefinetely until the server acknowledges the receipt of the sequence packet
                client_socket.sendto(packet, (SERVER_IP, SERVER_PORT))
                try:
                    ack, _ = client_socket.recvfrom(BUFFER_SIZE) #wait for acknowledgement from server. recvfrom will wait maximum TIMEOUT seconds (what set set before)
                    if int(ack.decode()) == seq_num:
                        break  # ACK received, go to next packet. if not true, we will resend the chunk
                except socket.timeout:
                    print(f"Timeout, resending seq {seq_num}") #if the socket timeout triggers, we will resend the chunk
            seq_num += 1
    # Send EOF marker
    client_socket.sendto(b"EOF", (SERVER_IP, SERVER_PORT))
    print(f"File '{filename}' sent successfully.")
    client_socket.close()

if __name__ == "__main__":
    main()
