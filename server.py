import socket

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5959
BUFFER_SIZE = 4096

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #create UDP socket, AF_INET = ipv4, SOCK_DGRAM: UDP socket
server_socket.bind((SERVER_IP, SERVER_PORT)) #send all UDP traffic arriving at this ip+port to my socket
print(f"Server listening on {SERVER_IP}:{SERVER_PORT}")

while True: #endless loop, always listening
    # Receive filename as first packet
    data, _ = server_socket.recvfrom(BUFFER_SIZE) #recvfrom() waits for the first UDP packet. we specified buffer size
    filename = data.decode()
    print(f"Receiving file '{filename}'")

    with open(filename, "wb") as file: #creates file with the received name. "with " automatically handles opening, closing. wb -> w means write, b means binary. seems to be necessary for windows 
        while True:
            packet, _ = server_socket.recvfrom(BUFFER_SIZE) #write data into packet, we dont care about the adress
            if packet == b"EOF": #if the EOF string is received, we stop the writing of the file
                break
            file.write(packet)

    print(f"File '{filename}' received successfully.")