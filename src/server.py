"""
    Assigment for U7 A1: Envío de archivos

    Author: Eloy Uziel García Cisneros (eloy.garcia@edu.uag.mx)

    usage: import network
           from network import <class>

    repo: https://github.com/uzielgc/uag_u7a1-file-sender
"""

import socket
import logging
import os
import json
import rsa
import pickle
from cryptography.fernet import Fernet


logging.basicConfig(level='INFO')
LOGGER = logging.getLogger(__name__)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SRC_DIR = os.path.join(PROJECT_DIR, 'from')


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('localhost', 20002)
sock.bind(server_address)
sock.listen(1)

LOGGER.info("Listening for incoming connections...")

conn, client_addr = sock.accept()
LOGGER.info("Accepted connection from: %s", client_addr)


LOGGER.info('Starting key exchange.')
key_pub = pickle.loads(conn.recv(1024))  # msg enc key
FILE_KEY = Fernet.generate_key()        # file enc key



data = rsa.encrypt(FILE_KEY, key_pub)
conn.sendall(data)


FILE_KEY = Fernet(FILE_KEY)

CMDS = None
FILES = {}

def list_cmds(*args):
    return list(CMDS.keys())

def list_files(*args):
    global FILES
    FILES = {id_: file for id_, file in enumerate(os.listdir(SRC_DIR))}
    return json.dumps(FILES, indent=4)

def send_file(file_id):
    global FILES

    file_name = FILES.get(int(file_id))

    LOGGER.info("Sending %s", file_name)

    chunk_size = 4096 
    with open(os.path.join(PROJECT_DIR, 'from', file_name), 'rb') as f:
        # Read the file contents into memory
        file_data = f.read()
        LOGGER.info('Total file size %d', len(file_data))
        file_data = FILE_KEY.encrypt(file_data)




        total = len(file_data)
        LOGGER.info('Total file size (ENCRYPTED) %d', total)
        file_data = [file_data[i:i+chunk_size] for i in range(0, total, chunk_size)]


    LOGGER.info("first_chunk: %d, last_chuck size: %d", len(file_data[0]), len(file_data[-1]))

    data = f"{total},{file_name}"
    LOGGER.info('Sending metadata : %s', data)
    conn.sendall(data.encode('utf-8'))

    LOGGER.info('Sending chunks.')
    # Send the chunks one by one
    for chunk in file_data:
        conn.sendall(chunk)
        _ = conn.recv(14)
    
    return f'{file_name}: transfer completed!'

if __name__ == '__main__':

    CMDS = {'ls': {'f': list_files},
            'send': {'f': send_file},
            'help': {'f': list_cmds}}
    
    _ = list_files()

    print('Enter command:')
    while True:
        data = input('> ')
        if data == '': continue
        data = data.split(' ')
        cmd = CMDS.get(data[0])

        data = cmd['f'](data[-1])
        print(data)
