import socket
import zlib #for checksum implementation

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5959
BUFFER_SIZE = 4096

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #create UDP socket, AF_INET = ipv4, SOCK_DGRAM: UDP socket
server_socket.bind((SERVER_IP, SERVER_PORT)) #send all UDP traffic arriving at this ip+port to my socket
print(f"Server 3.0 listening on {SERVER_IP}:{SERVER_PORT}")

while True: #endless loop, always listening
    # Receive filename as first packet
    data, addr = server_socket.recvfrom(BUFFER_SIZE) #recvfrom() waits for the first UDP packet. we specified buffer size
    filename = data.decode()
    print(f"Receiving file '{filename}' from {addr}")

    expected_seq = 0 #used to keep track. ofc we start with 0 :)
    with open(filename, "wb") as f:
        while True:
            packet, addr = server_socket.recvfrom(BUFFER_SIZE + 30)  # we need extra space for seq number + Checksum. We also have to store who sent the message in order to send the ACK back. It does not change the actual chunk as we know where it starts (at the |) and at the end, we have some empty bytes
            if packet == b"EOF": #if the EOF string is received, we stop the writing of the file
                break
            try:
                seq, checksum, content = packet.split(b"|", 2) #we split the packet twice (!) at the two delimiting "|"
                seq_num = int(seq.decode())
                received_checksum = int(checksum.decode())
                actual_checksum = zlib.crc32(content) #calculate the checksum in the same way the server does
            except Exception: #if either split, or the decoding of the packet fails
                print("Malformed packet, ignoring")
                continue
            if seq_num == expected_seq and actual_checksum == received_checksum: #sequence matches, checksum matches, all good
                f.write(content)
                ack = str(expected_seq).encode()
                expected_seq += 1 # and now we expect the next seq
            else: #the received packet is not what we need/expect (packet loss) OR checksum is incorrect (corrupted packet)
                print(f"Expected {expected_seq}, but received {seq_num}")
                ack = str(expected_seq).encode()
            # send ACK
            server_socket.sendto(ack, addr)

    print(f"File '{filename}' received successfully.")
