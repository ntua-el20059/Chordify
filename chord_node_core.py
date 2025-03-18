import hashlib
import socket
from pymongo import MongoClient
import threading
import json


class ChordNodeCore:
    def __init__(self, bootstrap_node=None, replication_factor=1, consistency_type="linearizability", debugging=True):
        try:
            self.ip = socket.gethostbyname(socket.gethostname())
        except Exception as e:
            print(f"❌ Failed to resolve local IP: {e}\n❌ Aborting...")
            exit(1)   
        if bootstrap_node is not None:
            self.port = self.get_free_port()  # Assign a free port
        else:
            self.port = 5000
        self.node_id = self.hash_function(f"{self.ip}:{self.port}")
        self.replication_factor = replication_factor
        self.successor = None
        self.predecessor = None
        if bootstrap_node!=None:
            bootstrap_node["node_id"] = self.hash_function(f"{bootstrap_node['ip']}:{bootstrap_node['port']}")
        self.bootstrap_node = bootstrap_node  # Dictionary containing bootstrap node details
        self.running = True  # Flag to control the server loop
        self.server_socket = None  # Store the server socket for cleanup
        self.debugging = debugging
        #self.print_lock = threading.Lock()

        if bootstrap_node is None:
            # If this is the first node, it is its own successor and predecessor
            self.consistency_type = consistency_type 
            self.successor = {"ip": self.ip, "port": self.port, "node_id": self.node_id}
            self.predecessor = {"ip": self.ip, "port": self.port, "node_id": self.node_id}
            self.bootstrap_node = {"ip": self.ip, "port": self.port, "node_id": self.node_id}
            print(f"🟢 Bootstrap node started at {self.ip}:{self.port}, ID: {self.node_id}")
        else:
            self.join()
        self.mongoclient = MongoClient("mongodb://localhost:27017/")  
        self.db = self.mongoclient["database"]  
        self.collection = self.db["collection"]

        #server_thread = threading.Thread(target=self.start_server, args=())
        #server_thread.daemon = True
        #server_thread.start()

    def get_free_port(self):
        """Assign a free port."""
        for i in range(5000,6000):
            if self.is_port_free(i):
                return i
        return -1

    def is_port_free(self, port):
        """Check if a port is free."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("0.0.0.0", port))
                return True
            except:
                return False

    def get_port(self):
        return self.port

    def get_successor(self):
        """Get the successor of this node."""
        return self.successor["ip"], self.successor["port"]

    def get_predecessor(self):
        """Get the predecessor of this node."""
        return self.predecessor["ip"], self.predecessor["port"]
    
    def get_bootstrap(self):
        """Fetch the information of the bootstrap node"""
        return self.bootstrap_node

    def hash_function(self, key):
        """Hash a key using SHA-1 and return a 160-bit integer."""
        return int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**160)

    def start_server(self):
        """Start the server to listen for incoming connections."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("0.0.0.0", self.port))  # Listen on all interfaces
        self.server_socket.listen()  # Listen for incoming connections
        print(f"🔵 Chord Node {self.ip}:{self.port} started. ID: {self.node_id}")
        while self.running:
            try:
                conn, _ = self.server_socket.accept()
                threading.Thread(target=self.handle_request, args=(conn,)).start()
            except Exception as e:
                if self.running:
                    print(f"❌ Error accepting connection: {e}")
        self.server_socket.close()
        print("🔴 Server stopped.")

    def pass_request(self, request, target_ip=None, target_port=None):
        """Send a request to another node without waiting for a response."""
        try:
            if target_ip is None or target_port is None:
                succ_ip, succ_port = self.get_successor()
                self.pass_request(request, succ_ip, succ_port)
            else:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(10)  
                    sock.connect((target_ip, target_port))
                    if self.debugging:
                        print(f"📤 Sent request to {target_ip}:{target_port}")
                    sock.send(json.dumps(request).encode())
                    sock.shutdown(socket.SHUT_WR) 
        except Exception as e:
            print(f"❌ Failed to send request to {target_ip}:{target_port}: {e}")

