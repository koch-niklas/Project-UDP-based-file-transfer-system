import socket
import zlib #for checksum implementation
import os
import logging #to let python handle logging to file

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5959
BUFFER_SIZE = 4096

#use this object to store all clients with their state: port, packet sequence status, file etc. the client will be used as index
clients = {}


logging.basicConfig(
    filename = "server.log",
    level=logging.INFO,
    format = "%(asctime)s [Server] %(levelname)s: %(message)s"
)


def LogConsole(message): #replace any print command with this one, so we have console output + the same line in the logfile
    print(message)
    logging.info(message)


def SetupServer():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #create UDP socket, AF_INET = ipv4, SOCK_DGRAM: UDP socket
    server_socket.bind((SERVER_IP, SERVER_PORT)) #send all UDP traffic arriving at this ip+port to my socket
    LogConsole(f"Server 7.3 listening on {SERVER_IP}:{SERVER_PORT}")
    return server_socket


def HandleHandshake(data, addr, server_socket):
    handshake = data.decode()
    if not handshake.startswith("HELO"):
        LogConsole(f"[{addr[1]}] Not a handshake")
        return
    try:
        _, filename, filesize, total_packets = data.decode().split("|") #split message at the | 
        filesize = int(filesize)  #need to specify that its an integer
        total_packets = int(total_packets)
    except Exception as exception:
        LogConsole(f"Error during handshake with [{addr[1]}]: {exception}") #addr[1] holds the port. address at index 0 will always be localhost, so not interesting
        return

    # Create a new, unique filename as we cannot overwrite the same file
    base_name = os.path.basename(filename)
    unique_FileName = f"{addr[1]}_{base_name}"

    f = open(unique_FileName, "wb")

    clients[addr] = {   #fill the clients array with these specific informations, index is the IP+Port
        "filename": unique_FileName,
        "filesize": filesize,
        "total_packets": total_packets,
        "expected_seq": 0,
        "file": f, #we put the file writing operation into the array
        "finished": False
    }

    server_socket.sendto(b"HELO OK", addr)
    LogConsole(f"[{addr[1]}] Handshake accepted for file '{unique_FileName}'")


def HandlePacket(packet, addr, server_socket):
    if addr not in clients: #should not happen
        LogConsole(f"[{addr[1]}] Packet from unknown client, ignoring")
        return

    client = clients[addr] #look up the specific information about the client who sent this packet

    if packet == b"EOF": #if the EOF string is received, we stop the writing of the file
        client["file"].close() #this holds f, our file writing operation
        client["finished"] = True #update this boolean
        LogConsole(f"[{addr[1]}] File '{client['filename']}' transfer complete")
        return

    try:
        seq, checksum, content = packet.split(b"|", 2) #we split the packet twice (!) at the two delimiting "|"
        seq_num = int(seq.decode())
        received_checksum = int(checksum.decode())
        actual_checksum = zlib.crc32(content) #calculate the checksum in the same way the client does
    except Exception:
        LogConsole(f"[{addr[1]}] Malformed packet ignored")
        last_in_order = client["expected_seq"] - 1 #ACK last correctly received packet
        ack = str(last_in_order).encode()
        server_socket.sendto(ack, addr) #speed up the re-sending
        return

    last_in_order = client["expected_seq"] - 1 #last correctly received packet at this point

    if seq_num == client["expected_seq"] and received_checksum == actual_checksum:
        try: #moving process into this try expression in order to catch and log any error
            client["file"].write(content) #this holds f, our file writing operation
        except Exception as exception:
            LogConsole(f"Error during file writing: {exception}")
            return
        client["expected_seq"] += 1 # and now we expect the next seq
        last_in_order = seq_num  # update last correctly received packet

    ack = str(last_in_order).encode() #the received packet is not what we need/expect (packet loss) OR checksum is incorrect (corrupted packet)
    server_socket.sendto(ack, addr)


def HandleGoodbye(data, addr):
    if addr in clients and data.decode() == "BYE":
        LogConsole(f"[{addr[0]}] Client disconnected cleanly")
        del clients[addr]


def main():
    server_socket = SetupServer()

    while True:
        try:
            data, addr = server_socket.recvfrom(BUFFER_SIZE + 100) #packet arrives into this main loop. we will then decide what to do with it
        except KeyboardInterrupt:
            LogConsole("Shutting down server...")
            break

        #determine in main loop what needs to be done with the packet. scenarios: Client is unknown -> answer handshake and start filetransfer OR client is known -> file transfer either sti8ll needs handling, or is finished
        if addr not in clients: #client is unknown to us, do the handshake
            HandleHandshake(data, addr, server_socket)
        else: #client IS known to us, is the connection finished?
            if data == b"BYE":
                HandleGoodbye(data, addr)
            else: #connection is not finished
                HandlePacket(data, addr, server_socket)


if __name__ == "__main__":
    main()
