import socket

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5959
BUFFER_SIZE = 4096

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #create UDP socket, AF_INET = ipv4, SOCK_DGRAM: UDP socket
server_socket.bind((SERVER_IP, SERVER_PORT)) #send all UDP traffic arriving at this ip+port to my socket
print(f"Server 2.1 listening on {SERVER_IP}:{SERVER_PORT}")

while True: #endless loop, always listening
    # Receive filename as first packet
    data, _ = server_socket.recvfrom(BUFFER_SIZE) #recvfrom() waits for the first UDP packet. we specified buffer size
    filename = data.decode()
    print(f"Receiving file '{filename}'")

    expected_seq = 0 #used to keep track. ofc we start with 0 :)
    with open(filename, "wb") as f:
        while True:
            packet, addr = server_socket.recvfrom(BUFFER_SIZE + 20)  # we need extra space for seq number. We also have to store who sent the message in order to send the ACK back. It does not change the actual chunk as we know where it starts (at the |) and at the end, we have some empty bytes
            if packet == b"EOF": #if the EOF string is received, we stop the writing of the file
                break
            try:
                header, content = packet.split(b"|", 1) #we split the packet at the delimiting "|"
                seq_num = int(header.decode())
            except Exception: #if either split, or the decoding of the packet fails
                print("Malformed packet, ignoring")
                continue
            if seq_num == expected_seq:
                f.write(content)
                ack = str(expected_seq).encode() #we construct the acknowledgement packet with the seq number
                expected_seq += 1 # and now we expect the next seq
            else: #the received packet is not what we need/expect (packet loss) 
                print(f"Expected {expected_seq}, but received {seq_num}")
                ack = str(expected_seq).encode()
            # send ACK
            server_socket.sendto(ack, addr)

    print(f"File '{filename}' received successfully.")
