import hashlib
import socket
import threading
import json

class ChordNode:
    def __init__(self, ip, port, bootstrap_node=None):
        self.ip = ip
        self.port = port
        self.node_id = self.hash_function(f"{ip}:{port}")
        self.data_store = {}  # Local DHT storage (key = song name, value = IP of node)
        self.successor = None
        self.predecessor = None
        self.bootstrap_node = bootstrap_node  # Αν υπάρχει, συνδεόμαστε στο δίκτυο

        if bootstrap_node is None:
            # Αν είναι ο πρώτος κόμβος, είναι ο μόνος στο δίκτυο
            self.successor = {"ip": self.ip, "port": self.port, "node_id": self.node_id}
            self.predecessor = {"ip": self.ip, "port": self.port, "node_id": self.node_id}
            print(f"🟢 Bootstrap node started at {self.ip}:{self.port}, ID: {self.node_id}")
        else:
            self.join_network()

    def hash_function(self, key):
        return int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**160)

    def start_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Αποφυγή Address in use
        server_socket.bind((self.ip, self.port))
        server_socket.listen(5)
        print(f"🔵 Chord Node {self.ip}:{self.port} started. ID: {self.node_id}")
        while True:
            conn, _ = server_socket.accept()
            threading.Thread(target=self.handle_connection, args=(conn,)).start()

    def handle_connection(self, conn):
        try:
            request = json.loads(conn.recv(1024).decode())
            if request["operation"] == "join":
                response = self.handle_join(request["node_id"], request["ip"], request["port"])
            elif request["operation"] == "depart":
                response = self.handle_depart()
            else:
                response = json.dumps({"error": "Unknown operation"})
        except Exception as e:
            response = json.dumps({"error": str(e)})
        conn.sendall(response.encode())
        conn.close()

    def handle_join(self, node_id, ip, port):
        print(f"🟢 Node {ip}:{port} is joining the network.")
        new_node = {"node_id": node_id, "ip": ip, "port": port}
        
        if self.successor["node_id"] == self.node_id:
            self.successor = new_node
            self.predecessor = new_node
        else:
            self.successor = new_node

        return json.dumps({
            "successor": self.successor,
            "predecessor": self.predecessor
        })

    def handle_depart(self):
        print(f"🔴 Node {self.ip}:{self.port} is leaving the network.")
        
        if self.successor and self.predecessor:
            # Update the links so that the predecessor points to the successor
            self.predecessor["successor"] = self.successor
            self.successor["predecessor"] = self.predecessor
            
        return json.dumps({"message": f"Node {self.ip}:{self.port} has left the network."})

    def join_network(self):
        try:
            print(f"🔍 Trying to connect to Bootstrap Node at {self.bootstrap_node['ip']}:{self.bootstrap_node['port']}")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.bootstrap_node["ip"], self.bootstrap_node["port"]))
                request = json.dumps({"operation": "join", "node_id": self.node_id, "ip": self.ip, "port": self.port})
                s.sendall(request.encode())
                response = json.loads(s.recv(1024).decode())
                self.successor = response["successor"]
                self.predecessor = response["predecessor"]
                print("✅ Connected successfully!")
        except Exception as e:
            print(f"❌ Error connecting to bootstrap node: {e}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3:
        node = ChordNode(sys.argv[1], int(sys.argv[2]))
    elif len(sys.argv) == 5:
        node = ChordNode(sys.argv[1], int(sys.argv[2]), bootstrap_node={"ip": sys.argv[3], "port": int(sys.argv[4])})
    else:
        print("Usage:")
        print("  python node.py <ip> <port>               # Bootstrap Node")
        print("  python node.py <ip> <port> <b_ip> <b_port> # Join Existing Network")
        sys.exit(1)

    node.start_server()
