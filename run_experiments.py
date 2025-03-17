#!/usr/bin/env python3
import time
import threading
import sys
import argparse
import socket
import os
from pathlib import Path
from chord_node import ChordNode

def run_inserts(file_path, node, output_file):
    """Run insert operations from the specified file and write results to output_file."""
    with open(file_path, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    start_time = time.time()
    for line in lines:
        parts = [p.strip() for p in line.split(',')]
        if parts[0].lower() == "insert":
            key = parts[1]
            value = parts[2] if len(parts) > 2 else None
            node.insert(key, value)
    end_time = time.time()
    duration = end_time - start_time
    throughput = len(lines) / duration if duration > 0 else 0
    with open(output_file, "a") as f:
        f.write(f"[Insert Experiment] Completed {len(lines)} inserts in {duration:.2f} seconds, throughput: {throughput:.2f} ops/sec\n")

def run_queries(file_path, node, output_file):
    """Run query operations from the specified file and write results to output_file."""
    with open(file_path, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    start_time = time.time()
    for line in lines:
        parts = [p.strip() for p in line.split(',')]
        if parts[0].lower() == "query":
            key = parts[1]
            node.query(key)
    end_time = time.time()
    duration = end_time - start_time
    throughput = len(lines) / duration if duration > 0 else 0
    with open(output_file, "a") as f:
        f.write(f"[Query Experiment] Completed {len(lines)} queries in {duration:.2f} seconds, throughput: {throughput:.2f} ops/sec\n")

def run_requests(file_path, node, output_file):
    """Run mixed request operations from the specified file and write completion to output_file."""
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
        time.sleep(0.1)  # Slight delay between operations
    with open(output_file, "a") as f:
        f.write("[Requests Experiment] All operations completed.\n")

def wait_for_signal(listening_socket):
    """Wait for a 'go' signal from an external coordinator."""
    print(f"Waiting for signal on port {listening_socket.getsockname()[1]}...")
    connection, address = listening_socket.accept()
    data = connection.recv(1024).decode().strip()
    print(f"Received signal: {data}")
    connection.close()

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Unified Experiment Runner for Chord Node")
    parser.add_argument("--node_number", type=int, required=True, help="Node number (e.g., 0, 1, 2, ...)")
    parser.add_argument("--consistency", choices=["linearizability", "eventual"], default="linearizability", help="Consistency model")
    parser.add_argument("--replication", type=int, default=1, help="Replication factor (k)")
    parser.add_argument("--bootstrap_ip", help="Bootstrap node IP (required if node_number != 0)")
    parser.add_argument("--bootstrap_port", type=int, default="5000", help="Bootstrap node port (default: 5000)")
    parser.add_argument("--signal_port", type=int, required=True, help="Port to listen for signals")
    args = parser.parse_args()

    # Validate arguments
    if args.node_number != 0:
        if not args.bootstrap_ip:
            print("Error: --bootstrap_ip and --bootstrap_port are required for non-bootstrap nodes.")
            sys.exit(1)
    
    # Construct file names based on node_number
    node_number = args.node_number
    insert_file = f"./inserts/insert_0{node_number}.txt"
    query_file = f"./queries/query_0{node_number}.txt"
    requests_file = f"./requests/requests_0{node_number}.txt"
    output_file = f"./node0{node_number}/node_0{node_number}_{args.consistency}_{args.replication}.out"

    # Create directories if they don't exist
    Path("./inserts").mkdir(parents=True, exist_ok=True)
    Path("./queries").mkdir(parents=True, exist_ok=True)
    Path("./requests").mkdir(parents=True, exist_ok=True)
    Path(f"./node0{node_number}").mkdir(parents=True, exist_ok=True)

    # Create files if they don't exist
    Path(insert_file).touch(exist_ok=True)
    Path(query_file).touch(exist_ok=True)
    Path(requests_file).touch(exist_ok=True)
    Path(output_file).touch(exist_ok=True)

    # Configure bootstrap node
    bootstrap_node = {"ip": args.bootstrap_ip, "port": args.bootstrap_port} if args.node_number != 0 else None

    # Set up socket for listening to signals
    listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listening_socket.bind(("0.0.0.0", args.signal_port))
        listening_socket.listen(1)
    except OSError as e:
        print(f"Error binding to signal_port {args.signal_port}: {e}")
        sys.exit(1)

    # Initialize and configure the Chord node
    node = ChordNode(bootstrap_node=bootstrap_node, replication_factor=args.replication, consistency_type=args.consistency)

    # Start the node's server in a background thread
    server_thread = threading.Thread(target=node.start_server, daemon=True)
    server_thread.start()
    time.sleep(1)  # Allow the server time to initialize

    # Clear or create the output file at the start
    with open(output_file, "w") as f:
        f.write("Experiment Results\n\n")

    # Run the experiments in sequence, waiting for signals
    wait_for_signal(listening_socket)
    run_inserts(insert_file, node, output_file)

    wait_for_signal(listening_socket)
    run_queries(query_file, node, output_file)

    wait_for_signal(listening_socket)
    run_requests(requests_file, node, output_file)

    # Clean up
    listening_socket.close()

if __name__ == "__main__":
    main()
