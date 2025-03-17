#!/usr/bin/env python3
import time
import threading
import sys
import argparse
from chord_node import ChordNode

def run_requests(file_path, node):
    with open(file_path, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    for line in lines:
        parts = [p.strip() for p in line.split(',')]
        op = parts[0].lower()
        if op == "insert":
            key = parts[1]
            value = parts[2] if len(parts) > 2 else None
            node.insert(key, value)
        elif op == "query":
            key = parts[1]
            node.query(key)
        # Optionally, add support for delete or other operations here.
        time.sleep(0.1)  # slight delay between operations; adjust as needed
    print("[Requests Experiment] All operations completed.")

def main():
    parser = argparse.ArgumentParser(description="Experiment Runner for Mixed Requests")
    parser.add_argument("--file", required=True, help="Path to the requests commands file (e.g. requests_00.txt)")
    parser.add_argument("--bootstrap", action="store_true", help="Run as bootstrap node")
    parser.add_argument("-ip", help="Bootstrap node IP (required if not bootstrap)")
    parser.add_argument("--port", type=int, default=5000, help="Port to use")
    parser.add_argument("--consistency", choices=["linearizability", "eventual"], default="linearizability", help="Consistency model")
    parser.add_argument("--replication", type=int, default=3, help="Replication factor (k)")
    args = parser.parse_args()

    bootstrap_node = None
    if not args.bootstrap:
        if not args.ip:
            print("Error: Bootstrap IP required if not running as bootstrap.")
            sys.exit(1)
        bootstrap_node = {"ip": args.ip, "port": args.port}
    
    node = ChordNode(port=args.port, bootstrap_node=bootstrap_node)
    node.replication_factor = args.replication
    node.consistency_type = args.consistency

    server_thread = threading.Thread(target=node.start_server, daemon=True)
    server_thread.start()
    time.sleep(1)

    run_requests(args.file, node)

if __name__ == "__main__":
    main()
