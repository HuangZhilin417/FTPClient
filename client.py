import argparse
import os
import socket
import sys
import re
import time
from os import path
from urllib.parse import urlparse

# These are the valid operations for this FTP client
valid_operation = {'ls': 1, 'rm': 1, 'rmdir': 1, 'mkdir': 1, 'cp': 2, 'mv': 2}
operation_action = {'ls': [['PASV'], ['LIST']]}
ftp_servers = []


def recv_all(sock):
    response = ''
    while True:
        received = sock.recv(8192).decode()
        response += received
        if received[-1] == '\n':
            break
    print("this is here")
    return response


def connect_sock(sock, host, port):
    connect_info = (host, port)
    sock.connect(connect_info)


def parse_ip_to_port(first, second):
    return (int(first) << 8) + int(second)


def parse_ip_to_address(address):
    result = ''
    for x in address:
        if x != address[3]:
            result += x
            result += '.'
        else:
            result += x
    return result


def parse_dcr_response(msg):
    res_list = msg.split()
    print(msg)
    if res_list[0] == '227':
        l = re.findall(r'\((.*?)\)', msg)
        return l[0].split(",")

    print('failed')
    sys.exit()


# This is the FTP Client


class Client:
    def __init__(self, path, host, username='anonymous', password='', port=21):
        self.path = path
        self.username = username
        self.host = host
        self.commands = set(['USER', 'PASS', 'TYPE', 'MODE',
                             'STRU', 'LIST', 'DELE', 'MKD',
                             'RMD', 'STOR', 'RETR', 'QUIT', 'PASV'])
        self.password = password
        self.port = port
        self.data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dataChannelIP = ''
        self.dataChannelPort = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.end_line_message = '\r\n'

    # connects to the FTP servers, and setting the required environment to download files for this project
    def connect(self):

        connect_sock(self.sock, self.host, self.port)

        if self.username == 'anonymous' and self.password != '':
            print("Wrong Input Format for Username and Password: "
                  "Must have a username if you have a password")
            sys.exit()

        self.send_message('USER ' + self.username)

        if self.password != '':
            self.send_message('PASS ' + self.password)

        # set connection to 8-bit binary data mode
        self.send_message('TYPE I')
        # set connection to stream mode
        self.send_message('MODE S')
        # set connection to file-oriented mode
        self.send_message('STRU F')

    # receive all of the message from the server

    def quit(self):
        self.send_message('QUIT')
        time.sleep(2)
        self.sock.close()

    def request_data_channel(self):
        res = self.send_message('PASV')
        parsed_dcr = parse_dcr_response(res)
        self.dataChannelPort = parse_ip_to_port(parsed_dcr[4], parsed_dcr[5])
        self.dataChannelIP = parse_ip_to_address(parsed_dcr[0:4])

    def connect_data_channel(self):
        connect_sock(self.data_sock, self.dataChannelIP, self.dataChannelPort)

    # connect_sock(self.data_sock, self.dataChannelIP, self.dataChannelPort)

    def send_message(self, message):
        msg = message + self.end_line_message
        print(msg)
        self.sock.sendall(msg.encode())
        response = recv_all(self.sock)
        print(response)
        return response

    def send_file(self, paths):
        print(paths)
        f = open(paths, 'rb')

        while True:
            chunk = f.read(1024)
            if not chunk:
                print("File transfer completed")
                f.close()
                break
            self.data_sock.send(chunk)

        self.data_sock.close()

    def download_file(self, path):
        total_data = ''
        while True:
            data = self.data_sock.recv(1024)
            total_data = total_data + data.decode()
            if not data:
                break

        file = open(path, 'w+')
        file.write(total_data)
        file.close


    def send_command(self, command, param):
        if command == 'ls':
            self.request_data_channel()
            self.connect_data_channel()
            self.send_message('LIST ' + param[0])
            print(recv_all(self.data_sock))
            self.data_sock.close()
        elif command == 'mkdir':
            self.send_message('MKD ' + param[0])
        elif command == 'rmdir':
            self.send_message('RMD ' + param[0])
        elif command == 'cptoserver':
            self.request_data_channel()
            self.connect_data_channel()
            self.send_message('STOR ' + param[0])
            self.send_file(param[1])
        elif command == 'cpfromserver':
            self.request_data_channel()
            self.connect_data_channel()
            self.send_message('RETR ' + param[0])
            self.download_file(param[1])
        elif command == 'mvtoserver':
            self.request_data_channel()
            self.connect_data_channel()
            self.send_message('STOR ' + param[0])
            self.send_file(param[1])
            os.remove(param[1])
        elif command == 'mvfromserver':
            self.request_data_channel()
            self.connect_data_channel()
            self.send_message('RETR ' + param[0])
            self.download_file(param[1])
            self.send_message('DELE ' + param[0])




def parse_param(params):
    return urlparse(params)


def parse_arg():
    parser = argparse.ArgumentParser(description='FTP Client')
    parser.add_argument('operation')
    parser.add_argument('params', nargs='+')

    args = parser.parse_args(sys.argv[1:])
    param_num = check_operation(args.operation)
    param_num_check(args, param_num)

    return args


def check_operation(operation):
    if operation in valid_operation:
        return valid_operation[operation]
    print("Invalid Input for operation")

    sys.exit()


def param_num_check(args, num):
    if len(args.params) == 2 and num == 2:
        return
    if len(args.params) == 1 and num == 1:
        return
    print("Input Param Error")
    sys.exit()


if __name__ == '__main__':
    arg = parse_arg()
    ftp_info = parse_param(arg.params[0])
    param_list = []
    purpose = ''
    op = arg.operation
    if len(arg.params) == 2:
        if ftp_info.scheme != 'ftp':
            ftp_info = parse_param(arg.params[1])
            param_list.append(ftp_info.path)
            param_list.append(arg.params[0])
            purpose = 'toserver'
            op += purpose
        else:
            param_list.append(ftp_info.path)
            param_list.append(arg.params[1])
            purpose = 'fromserver'
            op += purpose
    else:
        param_list.append(ftp_info.path)

    client = Client(ftp_info.path, ftp_info.hostname, ftp_info.username, ftp_info.password)
    client.connect()
    client.send_command(op, param_list)
    client.quit()

