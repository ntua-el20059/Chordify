import argparse
import threading
from pymongo import MongoClient
import sys
from chord_node import ChordNode

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
            node.greet(target_ip=target_ip, target_port=target_port)
        elif choice == "status":
            print(node.get_bootstrap())
            print(f"ℹ️ Self: {node.node_id//2**155}")
            print(f"ℹ️ Successor: {node.successor['node_id']//2**155}")
            print(f"ℹ️ Predecessor: {node.predecessor['node_id']//2**155}")
            for key in node.collection.find():
                print(key)
        elif choice == "insert":
            key = input("Enter the key to insert: ")
            node.insert(key)
        elif choice == "query":
            key = f"{input("Enter the key to query: ")}"
            node.query(key)
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
        node.depart()
        sys.exit(0)


if __name__ == "__main__":
    main()
