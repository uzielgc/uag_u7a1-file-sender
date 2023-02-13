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
import time
import json
import threading
import argparse
from tqdm import tqdm
from cryptography.fernet import Fernet


# Initialize parser
PARSER = argparse.ArgumentParser()
# set argument to identify if process will run as message broker.
PARSER.add_argument("-p", "--port")
PARSER.add_argument("-pp", "--pport")
ARGS = PARSER.parse_args()

logging.basicConfig(level='INFO')
LOGGER = logging.getLogger(__name__)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

SRC_DIR = os.path.join(PROJECT_DIR, 'from')
TRGT_DIR = os.path.join(PROJECT_DIR, 'to')


class Network:

    CHUNK_SIZE = 4096

    def __init__(self, port, remote_port) -> None:
        self.addr = ("127.0.0.1", port)
        self.remote_addr = ("127.0.0.1", remote_port)
        self.enc_key = self._load_key()

    def _load_key(self):
        key_path = os.path.join(PROJECT_DIR, 'secure', 'key')
        with open(key_path, 'rb') as f:
            enc_key = f.read()
        return Fernet(enc_key)
    
    def serv_forever(self):
        LOGGER.info('Starting server. %s', self.addr)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(self.addr)
            sock.listen()

            LOGGER.info('Waiting for connection.')
            conn, addr = sock.accept()

            LOGGER.info('Client connected %s', addr)
            with conn:
                print(f"Connected by {addr}")
                while True:
                    self.get_file(conn)
    
    def connect(self):
        LOGGER.info('Starting client')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            LOGGER.info('Testing connection.')
            while (res := sock.connect_ex(self.remote_addr)) != 0:
                time.sleep(5)
                LOGGER.info('Still waiting %s - %d', self.remote_addr, res)
            
            LOGGER.info('Connected.')

            self.CMDS = {'ls': {'f': self.list_files},
                        'send': {'f': self.send_file, 'args': sock},
                        'help': {'f': self.list_cmds}}
            
            _ = self.list_files()

            print('Enter command:')
            while True:
                data = input('> ')
                if data == '': continue
                data = data.split(' ')
                cmd = self.CMDS.get(data[0])

                if args := cmd.get('args', {}):
                    args = {'file_id': data[-1], 'sock': args}


                data = cmd['f'](**args)
                print(data)

    def list_cmds(self, **kargs):
        return list(self.CMDS.keys())

    def list_files(self, *kargs):
        self.FILES = {id_: file for id_, file in enumerate(os.listdir(SRC_DIR))}
        return json.dumps(self.FILES, indent=4)
    
    def get_file(self, sock):
        # Get the file name to receive
        f_size, file_name = sock.recv(1024).decode('utf-8').split(',')
        f_size = int(f_size)
        file_name = os.path.join(TRGT_DIR, file_name)

        bar = tqdm(range(f_size), f"Getting {file_name}", unit="B", unit_scale=True, unit_divisor=self.CHUNK_SIZE)
        data = []
        rec_count = 0
        while f_size > rec_count:
            chunk = sock.recv(self.CHUNK_SIZE)
            sock.send(b'ack')

            rec_count += len(chunk)
            data.append(chunk)
            bar.update(len(chunk))


        LOGGER.info("first_chunk size: %d, last_chuck size: %d", len(data[0]), len(data[-1]))
        data = b''.join(data)
        LOGGER.info("Total data received: %d", len(data))
        LOGGER.info("Decrypt data.")
        data = self.enc_key.decrypt(data)
        LOGGER.info("File size after decrypt: %d", len(data))

        LOGGER.info('Writing data to file.')
        with open(file_name, 'wb') as f:
            # Receive the chunks one by one and write them to the file
            f.write(data)

        LOGGER.info('%s: transfer completed!', file_name)
    
    def send_file(self, file_id, sock):
        file_name = self.FILES.get(int(file_id))

        LOGGER.info("Sending %s", file_name)
        with open(os.path.join(PROJECT_DIR, 'from', file_name), 'rb') as f:
            # Read the file contents into memory
            file_data = f.read()
            LOGGER.info('Total file size %d', len(file_data))
            file_data = self.enc_key.encrypt(file_data)

            total = len(file_data)
            LOGGER.info('Total file size (ENCRYPTED) %d', total)
            file_data = [file_data[i:i+self.CHUNK_SIZE] for i in range(0, total, self.CHUNK_SIZE)]

        LOGGER.info("first_chunk: %d, last_chuck size: %d", len(file_data[0]), len(file_data[-1]))

        data = f"{total},{file_name}"
        LOGGER.info('Sending metadata : %s', data)
        sock.sendall(data.encode('utf-8'))

        LOGGER.info('Sending chunks.')
        # Send the chunks one by one
        for chunk in file_data:
            sock.sendall(chunk)
            _ = sock.recv(14)
        
        return f'{file_name}: transfer completed!'


node = Network(int(ARGS.port), int(ARGS.pport))
LOGGER.info('%s -- %s',node.addr, node.remote_addr)

LOGGER.info('Starting server thread.')
threading.Thread(target=node.serv_forever, daemon=True).start()

time.sleep(3)

LOGGER.info('Starting client (console) thread.')
node.connect()
