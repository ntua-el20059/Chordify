import socket
import json
from chord_node_handlers import ChordNodeHandlers
from pymongo import MongoClient

class ChordNodeOperations(ChordNodeHandlers):
    def greet(self, target_ip, target_port):
        if target_port == None and target_ip == None:
            target_ip = self.bootstrap_node["ip"]
            target_port = self.bootstrap_node["port"]

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_socket:
                temp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                temp_socket.bind(("0.0.0.0", 0))  # Bind to a free port
                temp_port = temp_socket.getsockname()[1]
                temp_socket.listen(1)
                print(f"🔍 Listening for response on temporary port {temp_port}")

                request = {
                    "type": "greet",
                    "sender_ip": self.ip,
                    "sender_port": temp_port,
                    "sender_id": self.node_id,
                    "target_id": self.hash_function(f"{target_ip}:{target_port}")
                }
                self.pass_request(request=request, target_ip=target_ip, target_port=target_port)

                # Wait for the response on the temporary socket
                print("🕒 Waiting for response...")
                conn, addr = temp_socket.accept()
                data = conn.recv(1024).decode()
                if data:
                    response = json.loads(data)
                    print(f"📨 Received response: {response['msg']}")
                conn.close()

    def join(self):
        """Join an existing Chord network using the bootstrap node."""
        print(f"🟡 Joining network via bootstrap node {self.bootstrap_node}")

        # Create a temporary socket to listen for the response
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_socket:
            temp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            temp_socket.bind(("0.0.0.0", 0))  # Bind to a free port
            temp_port = temp_socket.getsockname()[1]
            temp_socket.listen(1)
            print(f"🔍 Listening for response on temporary port {temp_port}")

            request = {
                "type": "join",
                "sender_ip": self.ip,
                "sender_port": self.port,
                "sender_temp_port": temp_port,
                "sender_id": self.node_id,
                "found_predecessor": False  # Initialize found_predecessor as False
            }

            # Send the join request to the bootstrap node
            self.pass_request(request=request, target_ip=self.bootstrap_node["ip"], target_port=self.bootstrap_node["port"])

            # Wait for the response on the temporary socket
            print("🕒 Waiting for response...")
            conn, _ = temp_socket.accept()
            data = conn.recv(1024).decode()
            if data:
                response = json.loads(data)
                print(f"📨 Received response: {response}")
                self.successor = {
                    "ip": response['successor_ip'],
                    "port": response['successor_port'],
                    "node_id": response['successor_id']
                }
                self.predecessor = {
                    "ip": response['predecessor_ip'],
                    "port": response['predecessor_port'],
                    "node_id": response['predecessor_id']
                }
                print(f"🟢 Successfully joined network. Successor: {self.successor}, Predecessor: {self.predecessor}")
            conn.close()

    def depart(self):
        """Depart from the Chord network gracefully."""
        if self.successor["node_id"] != self.node_id:
            # Notify the successor to update its predecessor
            request = {
                "type": "departure",
                "sender_ip": self.ip,
                "sender_port": self.port,
                "sender_id": self.node_id,
                "successor_ip": self.successor["ip"],
                "successor_port": self.successor["port"],
                "successor_id": self.successor["node_id"],
                "predecessor_ip": self.predecessor["ip"],
                "predecessor_port": self.predecessor["port"],
                "predecessor_id": self.predecessor["node_id"]
            }
            self.pass_request(request)
            self.pass_request(request=request,target_ip=self.predecessor["ip"],target_port=self.predecessor["port"])
            request["type"] = "departure_announcement"
            self.pass_request(request, self.bootstrap_node["ip"], self.bootstrap_node["port"])

        self.stop()
    
    def insert(self, key):
        """Insert a key into the Chord network."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_socket:
            temp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            temp_socket.bind(("0.0.0.0", 0))  # Bind to a free port
            temp_port = temp_socket.getsockname()[1]
            temp_socket.listen(1)


            key_hash = self.hash_function(key)
            print(f"🔍 Querying for key {key} with hash {key_hash}")
            request = {
                "type": "insertion",
                "key": key_hash,
                "value": key,
                "sender_ip": self.ip,
                "sender_port": self.port,
                "sender_temp_port": temp_port,
                "sender_id": self.node_id,
                "times_copied": 0
            }
            self.pass_request(request,self.ip,self.port)
            print("🕒 Waiting for response...")
            conn, _ = temp_socket.accept()
            data = conn.recv(1024).decode()
            if data:
                response = json.loads(data)
                if response:
                    print(f"📨 Song was inserted successfully")
            conn.close()
            

    def query(self, key):
        """Query for a key in the Chord network."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_socket:
            temp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            temp_socket.bind(("0.0.0.0", 0))  # Bind to a free port
            temp_port = temp_socket.getsockname()[1]
            temp_socket.listen(1)


            key_hash = self.hash_function(key)
            print(f"🔍 Querying for key {key} with hash {key_hash}")
            request = {
                "type": "query",
                "key": key_hash,
                "sender_ip": self.ip,
                "sender_port": self.port,
                "sender_temp_port": temp_port,
                "sender_id": self.node_id,
                "times_copied": 0,
                "found": None
            }
            self.pass_request(request,self.ip,self.port)
            print("🕒 Waiting for response...")
            conn, _ = temp_socket.accept()
            data = conn.recv(1024).decode()
            if data:
                response = json.loads(data)
                print(f"📨 Song \"{key}\" was { "not" if response["found"]==False else " "}found")
            conn.close()
            

    def stop(self):
        """Stop the server and clean up resources."""
        self.running = False
        self.mongoclient.close()
        if self.server_socket:
            self.server_socket.close()
        print("🛑 Stopping node...")
