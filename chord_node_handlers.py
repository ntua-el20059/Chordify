import json
from chord_node_core import ChordNodeCore  # Import the ChordNode class

class ChordNodeHandlers(ChordNodeCore):
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
                elif request['type'] == 'insertion':
                    self.handle_insertion_request(request)
                elif request['type'] == 'query':
                    self.handle_query_request(request)
                elif request['type'] == 'deletion':
                    self.handle_deletion_request(request)
                elif request['type'] == 'departure_announcement':
                    if self.bootstrap_node["node_id"] == self.node_id:
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
            "msg": "Einai o pappous ekei?"
        }
        self.pass_request(response, target_ip=request['sender_ip'], target_port=request['sender_port'])# Send response back to the sender
        
    def handle_join_request(self, request):
        """Handle a join request."""
        print(f"🟡 Node {request['sender_ip']}:{request['sender_port']} is joining the network.")

        if not request.get("found_predecessor", False):
            # If predecessor is not yet found
            if self.bootstrap_node["node_id"] == self.node_id:
                request["consistency_type"] = self.consistency_type
                request["replication_factor"] = self.replication_factor

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
            self.pass_request(response, target_ip=request['sender_ip'], target_port= request['sender_temp_port'])

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

    def handle_insertion_request(self, request):
        """Handle an insertion request."""
        if ((self.successor["node_id"] == self.node_id or  # Bootstrap node case
        self.node_id < request['key'] < self.successor["node_id"] or  # Normal case
        (self.successor["node_id"] < self.node_id and  # Wrap-around case
        (request['key'] > self.node_id or request['key'] < self.successor["node_id"])) and request["times_copied"]==0) or
        0<request['times_copied']<self.replication_factor):
            request['times_copied']+=1


            # EDW MPAINEI TO INSERTION STO MONGO


            if request['times_copied']==self.replication_factor and self.consistency_type=="linearizability":
                response = {
                    "type": "insertion_response",
                    "key": request['key'],
                    "inserted": True
                }
                self.pass_request(response, target_ip=request['sender_ip'], target_port=request['sender_temp_port'])
            if request['times_copied']==1 and self.consistency_type=="eventual":
                response = {
                    "type": "insertion_response",
                    "key": request['key'],
                    "inserted": True
                }
                self.pass_request(response, target_ip=request['sender_ip'], target_port=request['sender_temp_port'])
            if request['times_copied']<self.replication_factor:
                self.pass_request(request)
        else:
            # Forward the request to the successor
            self.pass_request(request)

    def handle_query_request(self, request):
        if self.consistency_type=="eventual":
            self.handle_query_request_eventual_consistency(request)
        elif self.consistency_type=="linearizability":
            self.handle_query_request_linearizability(request)


    def handle_query_request_eventual_consistency(self, request):
        """Handle a query request."""
        if (self.successor["node_id"] == self.node_id or  # Bootstrap node case
            self.node_id < request['key'] < self.successor["node_id"] or  # Normal case
            (self.successor["node_id"] < self.node_id and  # Wrap-around case
            (request['key'] > self.node_id or request['key'] < self.successor["node_id"]))):
            response = {
                "type": "query_response",
                "key": request['key'],
                "found": False
            }
            self.pass_request(response, target_ip=request['sender_ip'], target_port=request['sender_temp_port'])
        else:
            self.pass_request(request)

    def handle_query_request_linearizability(self, request):
        if ((self.successor["node_id"] == self.node_id or  # Bootstrap node case
        self.node_id < request['key'] < self.successor["node_id"] or  # Normal case
        (self.successor["node_id"] < self.node_id and  # Wrap-around case
        (request['key'] > self.node_id or request['key'] < self.successor["node_id"])) and request["times_copied"]==0) or
        0<request['times_copied']<self.replication_factor):
            request['times_copied']+=1
            if request['times_copied']==self.replication_factor:
                response = {
                    "type": "insertion_response",
                    "key": request['key'],
                    "inserted": True
                }
                self.pass_request(response, target_ip=request['sender_ip'], target_port=request['sender_temp_port'])
            if request['times_copied']<self.replication_factor:
                self.pass_request(request)
        else:
            # Forward the request to the successor
            self.pass_request(request)

    def handle_deletion_request(self, request):
        """Handle a deletion request."""
        if (self.successor["node_id"] == self.node_id or  # Bootstrap node case
        self.node_id < request['key'] < self.successor["node_id"] or  # Normal case
        (self.successor["node_id"] < self.node_id and  # Wrap-around case
        (request['key'] > self.node_id or request['key'] < self.successor["node_id"])) or
        0<request['times_deleted']<self.replication_factor):
            # Key belongs to this node
            #if request['key'] in self.data_store:
            print(f"🟢 Key {request['key']} deleted successfully.")
            #self.data_store[request['key']] = request['value']
            request['times_deleted']+=1
            if request['times_copied']<self.replication_factor:
                self.pass_request(request)
        else:
            # Forward the request to the successor
            self.pass_request(request)
