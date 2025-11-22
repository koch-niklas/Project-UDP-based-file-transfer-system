import socket
import zlib #for checksum implementation

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5959
BUFFER_SIZE = 4096


def SetupServer():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #create UDP socket, AF_INET = ipv4, SOCK_DGRAM: UDP socket
    server_socket.bind((SERVER_IP, SERVER_PORT)) #send all UDP traffic arriving at this ip+port to my socket
    print(f"Server 6.0 listening on {SERVER_IP}:{SERVER_PORT}")
    return server_socket


def ReceiveHandshake(server_socket):
    # Wait for handshake
    while True:
        data, addr = server_socket.recvfrom(BUFFER_SIZE)
        handshake = data.decode()

        if not handshake.startswith("HELO"):
            print("Not a handshake")
            continue
        try:
            _, filename, filesize, total_packets = handshake.split("|") #split message at the | 
            filesize = int(filesize) #need to specify that its an integer
            total_packets = int(total_packets)
        except Exception:
            print("Error during handshake!")
            continue

        if filesize <= 0 or total_packets <= 0: #validate handshake data, we could also check for free disk space on the server
            print("Invalid handshake")
            continue

        server_socket.sendto(b"HELO OK", addr)
        print(f"Handshake done with client {addr}, receiving '{filename}' now.")
        return filename, addr
        #handshake done


def ParsePacket(packet):
    seq, checksum, content = packet.split(b"|", 2) #we split the packet twice (!) at the two delimiting "|"
    seq_num = int(seq.decode())
    received_checksum = int(checksum.decode())
    actual_checksum = zlib.crc32(content) #calculate the checksum in the same way the client does
    return seq_num, received_checksum, actual_checksum, content


def ReceiveFile(server_socket, filename, client_addr):
    expected_seq = 0 #used to keep track. ofc we start with 0
    with open(filename, "wb") as f:
        while True:
            packet, _ = server_socket.recvfrom(BUFFER_SIZE + 30) # we need extra space for seq number + Checksum. It does not change the actual chunk as we know where it starts (at the |) and at the end, we have some empty bytes
            if packet == b"EOF": #if the EOF string is received, we stop the writing of the file
                break
            seq_num, received_checksum, actual_checksum, content = ParsePacket(packet)

            if seq_num is None:
                print("Malformed packet, ignoring")
                continue

            if seq_num == expected_seq and received_checksum == actual_checksum:
                f.write(content)
                ack = str(expected_seq).encode()
                expected_seq += 1  # and now we expect the next seq
            else: #the received packet is not what we need/expect (packet loss) OR checksum is incorrect (corrupted packet)
                ack = str(expected_seq).encode()
            # send ACK
            server_socket.sendto(ack, client_addr)

    print(f"File '{filename}' transfered.")


def ReceiveGoodbye(server_socket):
    data, _ = server_socket.recvfrom(BUFFER_SIZE)
    if data.decode() == "BYE":
        print("Client disconnected cleanly.")


def main():
    server_socket = SetupServer()

    while True:
        filename, addr = ReceiveHandshake(server_socket)
        ReceiveFile(server_socket, filename, addr)
        ReceiveGoodbye(server_socket)


if __name__ == "__main__":
    main()
