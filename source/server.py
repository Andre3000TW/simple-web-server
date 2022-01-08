import os
import socket
import hashlib
from datetime import datetime, timedelta

class WebServer:
    ### HTTP status codes ###

    def __init__(self):
        self.__valid_paths = ['/' + filename for filename in os.listdir('public')]
        self.__server_http_version = 'HTTP/1.1'

        self.__status_200 = '200 OK'
        self.__status_301 = '301 Moved Permanently' # redirect
        self.__status_304 = '304 Not Modified' # for caching
        self.__status_400 = '400 Bad Request'
        self.__status_404 = '404 Not Found'
        self.__status_505 = '505 HTTP Version Not Supported'

        self.__login_path = '/login.html'
        self.__index_path = '/index.html'

        self.__400_path = 'private/__bad-request.html'
        self.__404_path = 'private/__not-found.html'
        self.__505_path = 'private/__http-version-not-supported.html'

        self.__cookie = 'token=coooooooooooooooooooooooooooooooookieeeeeee'
    # end __init__()

    def __pathNormalization(self, path):
        if path == '/': 
            new_path = '/login.html'
            redirect = True
            return new_path, redirect
        elif path.endswith('.html'): 
            new_path = path
            redirect = False
            return new_path, redirect
        else: 
            new_path = path + '.html'
            redirect = new_path in self.__valid_paths
            return new_path, redirect
    # end __pathNormalization()

    def __getResLine(self, status):
        return f'{self.__server_http_version} {status}'
    # end __getResLine()

    def __getResHeaders(self, other_headers=[]):
        headers = f'Date: {self.__getTime()}\r\n'
        for other_header in other_headers: headers += other_header + '\r\n'
        return headers
        # 'Content-Type: text/html; charset=utf-8\r\n'
    # end __getResHeaders()

    def __getResBody(self, body):
        return body
    # end __getResBody()

    def __getFile(self, path):
        with open(path, 'r', encoding='utf-8') as file: 
            page = file.read()
        return page
    # end __getFile()

    def __createItem(self, key, value):
        with open('public/index.html', 'r', encoding='utf-8') as file: page = file.read()

        if page.find(f'Item {key}') == -1:
            if page.rfind('</p>') != -1:
                new_item_index = page.find('\n', page.rfind('</p>')) + 1
            elif page.rfind('<br>') != -1:
                new_item_index = page.find('\n', page.rfind('<br>')) + 1
            else: raise Exception('Error: Unknown error when POST')

            page = page[:new_item_index] + f'{" " * 8}<p>Item {key} = {value}</p>\n' + page[new_item_index:]
            with open('public/index.html', 'w', encoding='utf-8') as file: file.write(page)
        else: raise Exception('Error: POST item already exists')
    # end __createItem()

    def __updateItem(self, key, value):
        with open('public/index.html', 'r', encoding='utf-8') as file: page = file.read()

        item_start_index = page.find(f'<p>Item {key}')
        item_end_index = page.find('\n', item_start_index)
        if item_start_index != -1:
            page = page[:item_start_index] + f'<p>Item {key} = {value}</p>' + page[item_end_index:]
            with open('public/index.html', 'w', encoding='utf-8') as file: file.write(page)
        else: raise Exception('Error: POST/PUT/DELETE key not found')
    # end __updateItem()

    def __deleteItem(self, key):
        with open('public/index.html', 'r', encoding='utf-8') as file: page = file.read()

        item_index = page.find(f'<p>Item {key}')
        start_index = page.rfind('\n', 0, item_index)
        end_index = page.find('\n', start_index + 1)
        if item_index != -1:
            page = page[:start_index] + page[end_index:]
            with open('public/index.html', 'w', encoding='utf-8') as file: file.write(page)
        else: raise Exception('Error: POST/PUT/DELETE key not found')
    # end __deleteItem()

    def __getTime(self, time_delta=0, file_path=None):
        datetime_format = '%a, %d %b %Y %H:%M:%S GMT'
        
        if file_path:
            mt = os.path.getmtime(file_path)
            return datetime.fromtimestamp(mt).strftime(datetime_format)
        else: 
            return (datetime.utcnow() + timedelta(seconds=time_delta)).strftime(datetime_format)
    # end __getTime()

    def __getETag(self, str):
        return '"' + hashlib.sha3_256(str.encode()).hexdigest() + '"'
    # end 

    def __handleRequest(self, req):
        try:
            # response components setup
            res_status = ''
            res_headers = []
            res_body = ''
            # insert separator for later split
            req = req[:req.find('\r\n')] + '***SEPARATOR***' + req[req.find('\r\n'):]
            req = req[:req.find('\r\n\r\n')] + '***SEPARATOR***' + req[req.find('\r\n\r\n'):]

            # split the request to derive (request line, request headers, request body)
            # request line
            req_line, req_headers, req_body = req.split('***SEPARATOR***')
            method, path, version = req_line.split()
            # request headers
            req_headers = list(filter(None, req_headers.split('\r\n')))
            req_headers = {req_header.split(': ')[0]:req_header.split(': ')[1] for req_header in req_headers}
            # request body
            req_body = list(filter(None, req_body.split('\r\n')))
            #
            
            # parse the request
            if version != self.__server_http_version: 
                raise Exception('505')
            elif method == 'GET' or method == 'HEAD':
                path, redirect = self.__pathNormalization(path)
                
                # 301 Moved Permanently (redirect)
                if redirect:
                    res_status = self.__status_301
                    res_headers.append(f'Location: {path}')
                # handle GET request (May include 400/404)
                elif path in self.__valid_paths:
                    if path == self.__index_path and req_headers.get('Cookie', '') != self.__cookie:
                        raise Exception('400')
                    else:
                        path = 'public' + path
                        # response status
                        if (req_headers.get('If-None-Match', '') == self.__getETag(self.__getFile(path))
                            and
                            req_headers.get('If-Modified-Since', '') == self.__getTime(file_path=path)):
                            res_status = self.__status_304
                        else:
                            res_status = self.__status_200
                        # headers (for conditional GET)
                        res_headers.append('Cache-Control: max-age=30')
                        res_headers.append(f'ETag: {self.__getETag(self.__getFile(path))}')
                        res_headers.append(f'Last-Modified: {self.__getTime(file_path=path)}')
                        # body
                        if method != 'HEAD' and res_status == self.__status_200:
                            res_body = self.__getFile(path)
                else: raise Exception('404')
                # end if-elif-else
            elif method == 'POST' or method == 'PUT' or method == 'DELETE':
                if method =='POST' and path == self.__login_path:
                    username, password = ''.join(req_body).split('&')
                    username = username.split('=')[1]
                    password = password.split('=')[1]
                    if username == 'admin' and password =='admin':
                        exp_time = self.__getTime(600)
                        res_status = self.__status_200
                        res_headers.append(f'Set-Cookie: {self.__cookie}; Expires={exp_time};') # ; HttpOnly
                        res_body = 'Authentication Success'
                    else: raise Exception('400')
                elif path.startswith('/index/items/') and req_headers.get('Cookie', '') == self.__cookie:
                    path = path.split('/')
                    if method == 'POST': self.__createItem(path[-2], path[-1])
                    elif method == 'PUT': self.__updateItem(path[-2], path[-1])
                    else: self.__deleteItem(path[-1])
                    res_status = self.__status_200
                else: raise Exception('400')
            else: raise Exception('400')
        except (ValueError, IndexError, KeyError, Exception) as e:
            error_message = str(e)
            print(f'Error: {e}')

            if error_message == '505':
                res_status = self.__status_505
                if req.startswith('GET'): res_body = self.__getFile(self.__505_path)
            elif error_message == '404':
                res_status = self.__status_404
                if req.startswith('GET'): res_body = self.__getFile(self.__404_path)
            else:
                res_status = self.__status_400
                if req.startswith('GET'): res_body = self.__getFile(self.__400_path)
            # end if-elif-else
        finally:
            return self.__createResponse(self.__getResLine(res_status),
                                         self.__getResHeaders(res_headers),
                                         self.__getResBody(res_body)
                                        )
        # end try-except-finally
    # end __handleRequest()

    def __createResponse(self, res_line, res_headers, res_body):
        res = res_line + '\r\n'
        res += res_headers + '\r\n'
        res += res_body
        return res
    # end __createResponse():

    def runServer(self):
        # create a TCP socket & listen on server_addr
        server_addr = ('0.0.0.0', 80)
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.bind(server_addr)
        tcp_socket.listen()

        # Ready to receive requests from clients
        print('Server start listening')
        while True:
            # accept a connection request from the client
            connection_socket, client_addr = tcp_socket.accept()
            print(f'---Accept a connection request from {client_addr}---')

            # receive a request from the client
            req = connection_socket.recv(1024).decode()
            print(f'-Receive a request from {client_addr}:')
            print(req)

            # handle the received request and create a response
            res = self.__handleRequest(req)

            # send the response back to the client
            connection_socket.sendall(res.encode())
            print(f'-Send response back to {client_addr}:')
            print(res)

            # close the connection
            connection_socket.shutdown(socket.SHUT_RDWR)
            connection_socket.close()
            print('---Connection socket closed---')
            print()
        # end while

        tcp_socket.shutdown(socket.SHUT_RDWR)
        tcp_socket.close()
    # end runServer()

# end class WebServer

if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))
    server = WebServer()
    server.runServer()
# end if
