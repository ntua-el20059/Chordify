import hashlib
import socket
import threading
import json
import argparse
import sys


class ChordNode:
    def __init__(self, port=None, bootstrap_node=None):
        try:
            self.ip = socket.gethostbyname(socket.gethostname())
        except Exception as e:
            print(f"❌ Failed to resolve local IP: {e}, defaulting to localhost")
            self.ip = "127.0.0.1"
        self.port = self.get_free_port(port)  # Assign a free port
        self.node_id = self.hash_function(f"{self.ip}:{self.port}")
        self.data_store = {}  # Local DHT storage (key = song name, value = IP of node)
        self.successor = None
        self.predecessor = None
        self.bootstrap_node = bootstrap_node  # Dictionary containing bootstrap node details
        self.running = True  # Flag to control the server loop
        self.server_socket = None  # Store the server socket for cleanup

        if bootstrap_node is None:
            # If this is the first node, it is its own successor and predecessor
            self.successor = {"ip": self.ip, "port": self.port, "node_id": self.node_id}
            self.predecessor = {"ip": self.ip, "port": self.port, "node_id": self.node_id}
            self.bootstrap_node = {"ip": self.ip, "port": self.port, "node_id": self.node_id}
            print(f"🟢 Bootstrap node started at {self.ip}:{self.port}, ID: {self.node_id}")
        else:
            self.join()

    def get_free_port(self, port):
        """Assign a free port. If a specific port is provided, check if it's free."""
        if port is not None:
            if self.is_port_free(port):
                return port
            else:
                print(f"⚠️ Port {port} is not free. Assigning a free port automatically.")
        # Let the OS assign a free port dynamically
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("0.0.0.0", 0))  # Bind to port 0 to let the OS choose a free port
            free_port = sock.getsockname()[1]  # Get the assigned port
            return free_port

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
        """Send a request to another node."""
        try:
            if target_ip is None or target_port is None:
                succ_ip, succ_port = self.get_successor()
                print(f"Succ port is {succ_port}")
                self.pass_request(request, succ_ip, succ_port)
            else:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.connect((target_ip, target_port))
                    sock.send(json.dumps(request).encode())
                    print(f"📤 Sent request to {target_ip}:{target_port}")
        except Exception as e:
            print(f"❌ Failed to send request to {target_ip}:{target_port}: {e}")

    def handle_request(self, conn):
        """Handle incoming requests from other nodes."""
        try:
            data = conn.recv(1024).decode()
            if data:
                request = json.loads(data)
                print(f"📨 Received request from {request['sender_ip']}:{request['sender_port']}")
                print(f"📝 Request details: {request}")

                # Handle different request types
                if request['type'] == 'greet':
                    self.handle_greet_request(request)
                elif request['type'] == 'join':
                    self.handle_join_request(request)
                elif request['type'] == 'departure':
                    self.handle_departure_request(request)
                elif request['type'] == 'departure_announcement':
                    if self.bootstrap_node["node_id"] == self.successor["node_id"]:
                        (f"🟡 Node {request['sender_ip']}:{request['sender_port']} is departing.")
        except Exception as e:
            print(f"❌ Error handling request: {e}")
        finally:
            conn.close()

    def handle_greet_request(self, request):
        """Handle a greet request."""
        print(f"👋 Hello from {request['sender_ip']}:{request['sender_port']}")
        response = {
            "type": "greet_response",
            "sender_ip": self.ip,
            "sender_port": self.port,
            "sender_id": self.node_id,
            "msg": "Hello from the Chord node!"
        }
        # Send response back to the sender
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((request['sender_ip'], request['sender_port']))
            sock.send(json.dumps(response).encode())

    def handle_join_request(self, request):
        """Handle a join request."""
        print(f"🟡 Node {request['sender_ip']}:{request['sender_port']} is joining the network.")

        if not request.get("found_predecessor", False):
            # If predecessor is not yet found
            if (self.successor["node_id"] == self.node_id or  # Bootstrap node case
                self.node_id < request['sender_id'] < self.successor["node_id"] or  # Normal case
                (self.successor["node_id"] < self.node_id and  # Wrap-around case
                (request['sender_id'] > self.node_id or request['sender_id'] < self.successor["node_id"]))):
                
                # The new node fits between this node and its successor
                request["found_predecessor"] = True
                request["predecessor_ip"] = self.ip
                request["predecessor_port"] = self.port
                request["predecessor_id"] = self.node_id

                # Update the successor of the current node to point to the new node

                self.pass_request(request)
                self.successor = {"ip": request['sender_ip'], "port": request['sender_port'], "node_id": request['sender_id']}

                # Forward the request to the new node
            else:
                # Forward the request to the successor
                self.pass_request(request)
        else:
            # Predecessor is found, update successor's predecessor and respond
            self.predecessor = {"ip": request['sender_ip'], "port": request['sender_port'], "node_id": request['sender_id']}
            response = {
                "type": "join_response",
                "predecessor_ip": request["predecessor_ip"],
                "predecessor_port": request["predecessor_port"],
                "predecessor_id": request["predecessor_id"],
                "successor_ip": self.ip,
                "successor_port": self.port,
                "successor_id": self.node_id
            }
            # Send response back to the new node
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((request['sender_ip'], request['sender_temp_port']))
                sock.send(json.dumps(response).encode())
    
    def handle_departure_request(self, request):
        """Handle a departure request."""
        print(f"👋 Node {request['sender_id']} is departing. Updating successor and predecessor.")
        if self.successor["node_id"] == request["sender_id"]:
            self.successor = {"ip": request["successor_ip"], "port": request["successor_port"], "node_id": request["successor_id"]}
            #announce the departure to the successor
            #say that the successor of the node departed
            print(f"🟢 Successor updated to {self.successor}")
        if self.predecessor["node_id"] == request["sender_id"]:
            self.predecessor = {"ip": request["predecessor_ip"], "port": request["predecessor_port"], "node_id": request["predecessor_id"]}
            print(f"🟢 Predecessor updated to {self.predecessor}")

    def join(self):
        """Join an existing Chord network using the bootstrap node."""
        print(f"🟡 Joining network via bootstrap node {self.bootstrap_node}")
        target_ip = self.bootstrap_node["ip"]
        target_port = self.bootstrap_node["port"]

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
            self.pass_request(request=request, target_ip=target_ip, target_port=target_port)

            # Wait for the response on the temporary socket
            print("🕒 Waiting for response...")
            conn, addr = temp_socket.accept()
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

    def stop(self):
        """Stop the server and clean up resources."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("🛑 Stopping node...")


def cli(node):
    """Command Line Interface for sending requests."""
    while True:
        print("\n📜 Available commands: help, status, greet, insert, delete, query, exit")
        choice = input("> ").strip().lower()

        if choice == "help":
            print("ℹ️ Help:\nℹ️ The 'greet' command sends a greeting to another node.")
            print("ℹ️ The 'insert' command adds a song to the DHT.")
            print("ℹ️ The 'delete' command removes a song from the DHT.")
            print("ℹ️ The 'query' command searches for a song in the DHT.")
        elif choice == "greet":
            target_ip = input("Enter target IP: ") or "127.0.0.1"
            target_port = int(input("Enter target port: ") or "5000")
            # Create a temporary socket to listen for the response
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_socket:
                temp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                temp_socket.bind(("0.0.0.0", 0))  # Bind to a free port
                temp_port = temp_socket.getsockname()[1]
                temp_socket.listen(1)
                print(f"🔍 Listening for response on temporary port {temp_port}")

                request = {
                    "type": "greet",
                    "sender_ip": node.ip,
                    "sender_port": temp_port,
                    "sender_id": node.node_id,
                    "target_id": node.hash_function(f"{target_ip}:{target_port}")
                }
                node.pass_request(request=request, target_ip=target_ip, target_port=target_port)

                # Wait for the response on the temporary socket
                print("🕒 Waiting for response...")
                conn, addr = temp_socket.accept()
                data = conn.recv(1024).decode()
                if data:
                    response = json.loads(data)
                    print(f"📨 Received response: {response}")
                conn.close()
        elif choice == "status":
            print(node.get_bootstrap())
            print(f"ℹ️ Self: {node.port}")
            print(f"ℹ️ Successor: {node.successor["port"]}")
            print(f"ℹ️ Predecessor: {node.predecessor["port"]}")
        elif choice == "exit":
            print("👋 Departing.")
            node.depart()
            break
        else:
            print("❌ Invalid option, please try again.")


def main():
    """Parse command-line arguments and start the Chord node."""
    parser = argparse.ArgumentParser(description="Chord Node Implementation")
    parser.add_argument("--bootstrap", action="store_true", help="Start as bootstrap node")
    parser.add_argument("-ip", help="Bootstrap node IP (required if not bootstrap)")
    parser.add_argument("-port", type=int, default=5000, help="Port to use (default: 5000)")
    args = parser.parse_args()

    if args.bootstrap:
        # Start as bootstrap node
        print("🚀 Starting as bootstrap node...")
        node = ChordNode(port=args.port, bootstrap_node=None)
    else:
        if not args.ip:
            print("❌ Error: Bootstrap node IP is required for non-bootstrap nodes.")
            return
        # Start as regular node and join the network
        bootstrap_node = {
            "ip": args.ip,
            "port": args.port,
            "node_id": int(hashlib.sha1(f"{args.ip}:{args.port}".encode()).hexdigest(), 16) % (2**160)
        }
        node = ChordNode(port=args.port, bootstrap_node=bootstrap_node)
        print(f"🚀 Node started at {node.ip}:{node.port}, ID: {node.node_id}")

    # Start the CLI and server
    cli_thread = threading.Thread(target=cli, args=(node,))
    cli_thread.daemon = True
    cli_thread.start()

    try:
        node.start_server()
    except KeyboardInterrupt:
        print("\n🛑 Received KeyboardInterrupt. Shutting down...")
        node.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
