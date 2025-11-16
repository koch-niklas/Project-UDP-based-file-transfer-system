#Usage: python udp_file_transfer.py --file path/to/file

import socket
import os
import argparse

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5959
BUFFER_SIZE = 4096

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True)
    arg = parser.parse_args()   #get "--file" argument

    file_path = arg.file
    file_path = os.path.abspath(os.path.expanduser(file_path))
    if not os.path.isfile(file_path):
        print("File not found.")
    filename = os.path.basename(file_path)  #format filepath so that python that read it

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #open socket at hardcoded port
    # Send filename first
    client_socket.sendto(filename.encode(), (SERVER_IP, SERVER_PORT))
    # Send file content
    with open(file_path, "rb") as file: #rb = read binary mode, f is the file object
        while chunk := file.read(BUFFER_SIZE):  #:= does all the magic. reads bytes up to the buffer size from file and writes it into "chunk". also uses chunk as condition for the while loop. when chunk empty, we have reaad the file
            client_socket.sendto(chunk, (SERVER_IP, SERVER_PORT)) #send the chunk to the server. each chunk is one UDP Packet

    # Send EOF marker
    client_socket.sendto(b"EOF", (SERVER_IP, SERVER_PORT)) #we are done with the loop, so we transfered the file
    print(f"File '{filename}' sent successfully.")
    client_socket.close()

if __name__ == "__main__":
    main()