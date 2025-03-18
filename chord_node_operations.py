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
                temp_socket.settimeout(10)
                print(f"🔍 Listening for response on temporary port {temp_port}")

                request = {
                    "type": "greet",
                    "sender_ip": self.ip,
                    "sender_port": temp_port,
                    "sender_id": self.node_id,
                    "target_id": self.hash_function(f"{target_ip}:{target_port}"),
                    "msg": "Einai o pappous ekei?"
                }
                self.pass_request(request=request, target_ip=target_ip, target_port=target_port)

                # Wait for the response on the temporary socket
                print("🕒 Waiting for response...")
                try:
                    conn, _ = temp_socket.accept()
                    data = conn.recv(1024).decode()
                    if data:
                        response = json.loads(data)
                        print(f"📨 Received response: {response['msg']}")
                    conn.close()
                except socket.timeout:
                    print("⏳ Timeout: No response received within the timeout period.")

    def join(self):
        """Join an existing Chord network using the bootstrap node."""
        print(f"🟡 Joining network via bootstrap node {self.bootstrap_node}")

        # Create a temporary socket to listen for the response
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_socket:
            temp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            temp_socket.bind(("0.0.0.0", 0))  # Bind to a free port
            temp_port = temp_socket.getsockname()[1]
            temp_socket.listen(1)
            temp_socket.settimeout(10)
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
            try:
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
                    self.consistency_type = response["consistency_type"]
                    self.replication_factor = response["replication_factor"]
                    print(f"🟢 Successfully joined network. Successor: {self.successor}, Predecessor: {self.predecessor}")
                conn.close()
            except socket.timeout:
                    print("⏳ Timeout: No response received within the timeout period.")
                    self.close()

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
            if self.debugging:
                request["type"] = "departure_announcement"
                self.pass_request(request, self.bootstrap_node["ip"], self.bootstrap_node["port"])

        self.stop()
    
    def insert(self, key, value=None):
        """Insert a key-value pair into the Chord network."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_socket:
            temp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            temp_socket.bind(("0.0.0.0", 0))  # Bind to a free port
            temp_port = temp_socket.getsockname()[1]
            temp_socket.listen(1)
            temp_socket.settimeout(10)


            key_hash = self.hash_function(key)
            print(f"🔍 Querying for key {key} with hash {key_hash}")
            request = {
                "type": "insertion",
                "key": key,
                "key_hash": key_hash,
                "value": key if value is None else value,
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
            try:    
                if data:
                    response = json.loads(data)
                    if response:
                        print(f"📨 Song was inserted successfully")
                conn.close()
            except socket.timeout:
                    print("⏳ Timeout: No response received within the timeout period.")
            

    def query(self, key):
        """Query for a key in the Chord network."""

        if key == "*":
            print("🔍 Querying for every key.")
            print(self.query_all())
            return
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_socket:
            temp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            temp_socket.bind(("0.0.0.0", 0))  # Bind to a free port
            temp_port = temp_socket.getsockname()[1]
            temp_socket.listen(1)
            temp_socket.settimeout(10)
            
            key_hash = self.hash_function(key)
            print(f"🔍 Querying for key {key} with hash {key_hash}")
            request = {
                "type": "query",
                "key": key,
                "key_hash": key_hash,
                "sender_ip": self.ip,
                "sender_port": self.port,
                "sender_temp_port": temp_port,
                "sender_id": self.node_id,
                "times_copied": 0
            }
            self.pass_request(request,self.ip,self.port)
            print("🕒 Waiting for response...")
            try:
                conn, _ = temp_socket.accept()
                data = conn.recv(1024).decode()
                if data:
                    response = json.loads(data)
                    if response["value"]==None:
                        print(f"📨 Song \"{key}\" was not found.")
                    else:
                        print(f"📨 Song \"{key}\" was found in node {response['sender_ip']}:{response['sender_port']}({response["sender_node_id"]//2**155}) with value {response['value']}")
                conn.close()
            except socket.timeout:
                    print("⏳ Timeout: No response received within the timeout period.")

    def query_all(self):
        """Query all keys in the Chord network."""
        # Start with local key–value pairs.

        key_value_list = []

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_socket:
            temp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            temp_socket.bind(("0.0.0.0", 0))  # Bind to a free port
            temp_port = temp_socket.getsockname()[1]
            temp_socket.listen(1)
            temp_socket.settimeout(20)

            print("🔍 Querying for every key in the Chord network.")
            request = {
                "type": "query_all",
                "sender_ip": self.ip,
                "sender_port": self.port,
                "sender_temp_port": temp_port,
                "sender_id": self.node_id,
            }

            target_ip, target_port = self.ip, self.port

            while True:
                self.pass_request(request, target_ip, target_port)
                print("🕒 Waiting for response...")
                try:
                    conn, _ = temp_socket.accept()
                    data = conn.recv(1024).decode()
                    conn.close()

                    if data:
                        response = json.loads(data)
                        key_value_list += response.get("key_value_list", [])

                        if response.get("node_id") == self.predecessor["node_id"]:
                            if self.debugging:
                                print("✅ Completed full cycle of the network.")
                            key_value_list = sorted(list(set(key_value_list)), key=lambda x: x["key"])
                            return key_value_list
                        else:
                            next_node = response.get("next")
                            target_ip, target_port = next_node.get("ip"), next_node.get("port")
                    else:
                        print("⚠️ No data received from the node.")
                        break
                except socket.timeout:
                    print("⏳ Timeout: No response received within the timeout period.")
                    break

        return []
    
    def overlay(self):
        """Display the overlay of the Chord network."""
        # Start with the local node's characteristics.
        node_list = []

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_socket:
            temp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            temp_socket.bind(("0.0.0.0", 0))  # Bind to a free port
            temp_port = temp_socket.getsockname()[1]
            temp_socket.listen(1)
            temp_socket.settimeout(10)

            print("🔍 Fetching the overlay of the Chord network.")
            request = {
                "type": "overlay",
                "sender_ip": self.ip,
                "sender_port": self.port,
                "sender_temp_port": temp_port,
                "sender_id": self.node_id,
            }
            target_ip, target_port = self.ip, self.port

            while True:
                self.pass_request(request, target_ip, target_port)
                print("🕒 Waiting for response...")
                try:
                    conn, _ = temp_socket.accept()
                    data = conn.recv(1024).decode()
                    conn.close()

                    if not data:
                        print("⚠️ No data received from node.")
                        break

                    response = json.loads(data)
                    # Append node characteristics if not already added.
                    sender = response.get("sender")
                    if sender:
                        node_list.append(sender)

                    # Check if we have completed a full cycle.
                    if sender.get("node_id") == self.predecessor["node_id"]:
                        print("✅ Completed full cycle of overlay.")
                        return node_list

                    # Update target with the next node's info.
                    next_node = response.get("next")
                    if next_node:
                        target_ip, target_port = next_node.get("ip"), next_node.get("port")
                    else:
                        print("⚠️ Next node info missing.")
                        return node_list

                except socket.timeout:
                    print("⏳ Timeout: No response received within the timeout period.")
                    return 

        return node_list
        

    def delete(self, key):
          "Remove a key from the Chord Network"
          with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_socket:
            temp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            temp_socket.bind(("0.0.0.0", 0))  # Bind to a free port
            temp_port = temp_socket.getsockname()[1]
            temp_socket.listen(1)
            temp_socket.settimeout(10)


            key_hash = self.hash_function(key)
            print(f"🔍 Querying for key {key} with hash {key_hash}")
            request = {
                "type": "deletion",
                "key": key,
                "key_hash": key_hash,
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
            try:    
                if data:
                    response = json.loads(data)
                    if response:
                        print(f"📨 Song was deleted successfully")
                conn.close()
            except socket.timeout:
                    print("⏳ Timeout: No response received within the timeout period.")


    def stop(self):
        """Stop the server and clean up resources."""
        self.running = False
        #try:
        #    self.server_socket.shutdown(socket.SHUT_RDWR)
        #except:
        #    pass
        self.mongoclient.close()
        if self.server_socket:
            self.server_socket.close()
            self.collection.delete_many({})
        print("🛑 Stopping node...")
