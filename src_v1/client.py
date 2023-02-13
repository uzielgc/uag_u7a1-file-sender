"""
    Assigment for U7 A1: Envío de archivos

    Author: Eloy Uziel García Cisneros (eloy.garcia@edu.uag.mx)

    usage: import network
           from network import <class>

    repo: https://github.com/uzielgc/uag_u7a1-file-sender
"""

import socket
import os
import rsa
import pickle
from cryptography.fernet import Fernet
import logging
from tqdm import tqdm



logging.basicConfig(level='INFO')
LOGGER = logging.getLogger(__name__)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

LOGGER.info('Setting up socket')
# Create a TCP socket for communication
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to the server
server_address = ('localhost', 20002)
sock.connect(server_address)

LOGGER.info("Connected to the server.")

key_pub, key_priv = rsa.newkeys(1024)

sock.sendall(pickle.dumps(key_pub))


FILE_KEY = sock.recv(1024)
FILE_KEY = rsa.decrypt(FILE_KEY, key_priv)


FILE_KEY = Fernet(FILE_KEY)

def recv_all(sock, chunk_size):
    c_size = chunk_size
    chunk = bytes()
    while chunk_size > 0:
        print('reading mini chunc %d', chunk_size)
        tmp_c = sock.recv(c_size)
        chunk_size -= len(tmp_c)
        chunk += tmp_c
    return chunk



def get_file():
    # Get the file name to receive
    chunk_size = 4096 # match server conf
    f_size, file_name = sock.recv(1024).decode('utf-8').split(',')
    f_size = int(f_size)
    file_name = os.path.join(PROJECT_DIR, 'to', file_name)

    data = []
    data = bytes()
    #for id_ in range(int(chunks)):

    bar = tqdm(range(f_size), f"Getting {file_name}", unit="B", unit_scale=True, unit_divisor=chunk_size)
    data = []
    rec_count = 0
    while f_size > rec_count:
        chunk = sock.recv(chunk_size)
        sock.send(b'ack')

        rec_count += len(chunk)
        data.append(chunk)
        #data.append(chunk)

        #LOGGER.info('Chunk %d received. %d', id_, len(chunk))
        #LOGGER.info('Total data received %d', len(data))
        bar.update(len(chunk))


    LOGGER.info("first_chunk size: %d, last_chuck size: %d", len(data[0]), len(data[-1]))
    data = b''.join(data)
    LOGGER.info("Total data received: %d", len(data))
    LOGGER.info("Decrypt data.")
    data = FILE_KEY.decrypt(data)
    LOGGER.info("File size after decrypt: %d", len(data))

    LOGGER.info('Writing data to file.')
    with open(file_name, 'wb') as f:
        # Receive the chunks one by one and write them to the file
        f.write(data)

    LOGGER.info('%s: transfer completed!', file_name)

while True:
    print('Ready to receive.')
    get_file()
