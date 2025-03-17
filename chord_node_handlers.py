import json
from chord_node_core import ChordNodeCore
from pymongo import MongoClient


class ChordNodeHandlers(ChordNodeCore):
    def handle_request(self, conn):
        """Handle incoming requests from other nodes."""
        try:
            data = conn.recv(1024).decode()
            if data:
                request = json.loads(data)
                if self.debugging:
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
                elif request['type'] == 'query_all':
                    self.handle_query_all_request(request)
                elif request['type'] == 'deletion':
                    self.handle_deletion_request(request)
                elif request['type'] == 'overlay':
                    self.handle_overlay_request(request)
                elif request['type'] == 'departure_announcement':
                    if self.bootstrap_node["node_id"] == self.node_id and self.debugging:
                        (f"🟡 Node {request['sender_ip']}:{request['sender_port']} is departing.")

        except Exception as e:
            print(f"❌ Error handling request: {e}")
        finally:
            conn.close()

    def handle_greet_request(self, request):
        """Handle a greet request."""
        print(f"👋 Received messsage from {request['sender_ip']}:{request['sender_port']}\n{request["msg"]}")
        response = {
            "type": "greet_response",
            "sender_ip": self.ip,
            "sender_port": self.port,
            "sender_id": self.node_id,
            "msg": "O pappous einai EKEI. 1-0"
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
                "successor_id": self.node_id,
                "consistency_type": request["consistency_type"],
                "replication_factor": request["replication_factor"]
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
        self.node_id < request['key_hash'] < self.successor["node_id"] or  # Normal case
        (self.successor["node_id"] < self.node_id and  # Wrap-around case
        (request['key_hash'] > self.node_id or request['key_hash'] < self.successor["node_id"])) and request["times_copied"]==0) or
        0<request['times_copied']<self.replication_factor):
            request['times_copied']+=1


            self.insert_into_mongodb(request['key'], request['key_hash'], request['value'])


            if request['times_copied']==self.replication_factor and self.consistency_type=="linearizability":
                response = {
                    "type": "insertion_response",
                    "key": request['key'],
                    "key_hash": request['key_hash'],
                    "inserted": True
                }
                self.pass_request(response, target_ip=request['sender_ip'], target_port=request['sender_temp_port'])
            if request['times_copied']==1 and self.consistency_type=="eventual":
                response = {
                    "type": "insertion_response",
                    "key": request['key'],
                    "key_hash": request['key_hash'],
                    "inserted": True
                }
                self.pass_request(response, target_ip=request['sender_ip'], target_port=request['sender_temp_port'])
            if request['times_copied']<self.replication_factor:
                self.pass_request(request)
        else:
            # Forward the request to the successor
            self.pass_request(request)
    
    def insert_into_mongodb(self, key, key_hash, value):
        """Insert a key-value pair into the MongoDB collection."""
        old_value = self.query_mongodb(key_hash)
        if old_value is not None:
            self.remove_from_mongodb(key_hash)
            self.collection.insert_one({"key":key, "key_hash": f"{key_hash}", "value": old_value+value})
        else:
            self.collection.insert_one({"key":key, "key_hash": f"{key_hash}", "value": value})

    def handle_query_request(self, request):
        if self.consistency_type=="eventual":
            self.handle_query_request_eventual_consistency(request)
        elif self.consistency_type=="linearizability":
            self.handle_query_request_linearizability(request)


    def handle_query_request_eventual_consistency(self, request):
        """Handle a query request."""
        if (self.successor["node_id"] == self.node_id or  # Bootstrap node case
            self.node_id < request['key_hash'] < self.successor["node_id"] or  # Normal case
            (self.successor["node_id"] < self.node_id and  # Wrap-around case
            (request['key_hash'] > self.node_id or request['key_hash'] < self.successor["node_id"]))):
            response = {
                "type": "query_response",
                "sender_ip": self.ip,
                "sender_port": self.port,
                "sender_node_id": self.node_id,
                "key": request['key'],
                "key_hash": request['key_hash'],
                "value": self.query_mongodb(request['key_hash'])
            }
            self.pass_request(response, target_ip=request['sender_ip'], target_port=request['sender_temp_port'])
        else:
            self.pass_request(request)


    def handle_query_request_linearizability(self, request):
        if ((self.successor["node_id"] == self.node_id or  # Bootstrap node case
        self.node_id < request['key_hash'] < self.successor["node_id"] or  # Normal case
        (self.successor["node_id"] < self.node_id and  # Wrap-around case
        (request['key_hash'] > self.node_id or request['key_hash'] < self.successor["node_id"])) and request["times_copied"]==0) or
        0<request['times_copied']<self.replication_factor):
            request['times_copied']+=1
            if request['times_copied']==self.replication_factor:
                response = {
                    "type": "query_response",
                    "sender_ip": self.ip,
                    "sender_port": self.port,
                    "sender_node_id": self.node_id,
                    "key": request['key'],
                    "key_hash": request['key_hash'],
                    "value": self.query_mongodb(request['key_hash'])
                }
                self.pass_request(response, target_ip=request['sender_ip'], target_port=request['sender_temp_port'])
            elif request['times_copied']<self.replication_factor:
                self.pass_request(request)
        else:
            # Forward the request to the successor
            self.pass_request(request)
    
    def query_mongodb(self, key_hash):
        query = self.collection.find_one({"key_hash": f"{key_hash}"})
        if query:
            return query["value"]
        else:
            return None

    def handle_query_all_request(self, request):
        print("ftanoume sthn handle query all request")
        response = {
            "type": "query_all_response",
            "next": self.successor,
            "node_id": self.node_id,
            "key_value_list" : self.query_all_mongodb()
        }
        self.pass_request(response, target_ip=request['sender_ip'], target_port=request['sender_temp_port'])
    

    def query_all_mongodb(self):
        """Returns a list of all key value pairs inside the local mongodb collection."""
        print("EDW PREPEI NA TO VALOUME NA KANEI FIND ALL KAI META NA TA PAIRNEI ENA ENA KAI NA TA VAZEI SE MIA LISTA KAI NA THN KANEI RETURN")
        return [{"key": "fanh", "value": "vohtheia"}]

    def handle_deletion_request(self, request):
        if ((self.successor["node_id"] == self.node_id or  # Bootstrap node case
        self.node_id < request['key_hash'] < self.successor["node_id"] or  # Normal case
        (self.successor["node_id"] < self.node_id and  # Wrap-around case
        (request['key_hash'] > self.node_id or request['key_hash'] < self.successor["node_id"])) and request["times_copied"]==0) or
        0<request['times_copied']<self.replication_factor):
            request['times_copied']+=1


            self.remove_from_mongodb(request['key_hash'])


            if request['times_copied']==self.replication_factor and self.consistency_type=="linearizability":
                response = {
                    "type": "deletion_response",
                    "key": request['key'],
                    "key_hash": request['key_hash'],
                    "inserted": True
                }
                self.pass_request(response, target_ip=request['sender_ip'], target_port=request['sender_temp_port'])
            if request['times_copied']==1 and self.consistency_type=="eventual":
                response = {
                    "type": "deletion_response",
                    "key": request['key'],
                    "key_hash": request['key_hash'],
                    "inserted": True
                }
                self.pass_request(response, target_ip=request['sender_ip'], target_port=request['sender_temp_port'])
            if request['times_copied']<self.replication_factor:
                self.pass_request(request)
        else:
            # Forward the request to the successor
            self.pass_request(request)
    
    def remove_from_mongodb(self, key_hash):
        """Remove a key from mongo collection."""
        self.collection.delete_one({"key_hash": f"{key_hash}"})
    
    def handle_overlay_request(self, request):
        """Handle an overlay request."""
        response = {
            "type": "overlay_response",
            "node_characteristics": {"ip":self.ip,"port":self.port,"node_id":self.node_id},
            "next": self.successor
        }
        self.pass_request(response, target_ip=request['sender_ip'], target_port=request['sender_temp_port'])
