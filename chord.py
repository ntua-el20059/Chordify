import argparse
import threading
from pymongo import MongoClient
import sys
from chord_node import ChordNode

def process_command(line, node):
    """Process a single command line and execute corresponding actions."""
    parts = [part.strip() for part in line.split(',')]
    if not parts:
        return False

    cmd = parts[0].lower()

    if cmd == "exit":
        print("👋 Departing.")
        node.depart()
        return True
    elif cmd == "help":
        print_help()
    elif cmd == "status":
        print_status(node)
    elif cmd == "greet":
        process_greet(parts, node)
    elif cmd == "insert":
        process_insert(parts, node)
    elif cmd == "delete":
        process_delete(parts, node)
    elif cmd == "query":
        process_query(parts, node)
    else:
        print(f"❌ Invalid command: {cmd}")
    return False

def print_help():
    """Display formatted help message with available commands."""
    print("ℹ️ Available commands:")
    print("  help - Display this help message")
    print("  status - Show node status and ring structure")
    print("  greet, [<ip>], [<port>] - Greet another node (default: 127.0.0.1:5000)")
    print("  insert, <song> [, <value>] - Store key-value pair in DHT")
    print("  delete, <song> - Remove entry from DHT")
    print("  query, <song> - Retrieve value from DHT")
    print("  exit - Leave the network and shutdown")

def print_status(node):
    """Display current node status and chord ring information."""
    print("\n🔄 Network Status:")
    print(f"• Self: {node.node_id//2**155}")
    print(f"• Successor: {node.successor['node_id']//2**155}")
    print(f"• Predecessor: {node.predecessor['node_id']//2**155}")
    
    print("\n💾 Local Storage:")
    for entry in node.collection.find():
        print(f"  {entry['_id']}: {entry.get('value', '')}")

def process_greet(parts, node):
    """Handle greeting command with optional IP/port parameters."""
    ip = parts[1].strip() if len(parts) > 1 else "127.0.0.1"
    port = int(parts[2].strip()) if len(parts) > 2 else 5000
    node.greet(target_ip=ip, target_port=port)

def process_insert(parts, node):
    """Handle insert command with optional value parameter."""
    if len(parts) < 2:
        print("❌ Missing song name for insertion")
        return
    
    song = parts[1]
    value = parts[2] if len(parts) > 2 else ""
    node.insert(song, value)
    print(f"✅ Inserted: {song} => {value}")

def process_delete(parts, node):
    """Handle delete command with required song parameter."""
    if len(parts) < 2:
        print("❌ Missing song name for deletion")
        return
    
    song = parts[1]
    node.delete(song)
    print(f"✅ Deleted: {song}")

def process_query(parts, node):
    """Handle query command with required song parameter."""
    if len(parts) < 2:
        print("❌ Missing song name for query")
        return
    
    song = parts[1]
    result = node.query(song)
    print(f"🔍 Query result for {song}: {result}")

def cli(node, input_file=None):
    """Command line interface with support for both interactive and file input."""
    if input_file:
        try:
            with open(input_file) as f:
                for line in f:
                    line = line.strip()
                    if line and process_command(line, node):
                        break
        except FileNotFoundError:
            print(f"❌ Error: File '{input_file}' not found")
    else:
        print("\n🎯 Chord DHT CLI - Enter commands ('help' for reference)")
        while True:
            try:
                line = input("> ").strip()
                if process_command(line, node):
                    break
            except KeyboardInterrupt:
                print("\n👋 Graceful shutdown initiated")
                node.depart()
                break

def main():
    """Configure and start the Chord node with enhanced CLI."""
    parser = argparse.ArgumentParser(description="Distributed Hash Table Node")
    parser.add_argument("--bootstrap", action="store_true", 
                      help="Initialize as bootstrap node")
    parser.add_argument("--ip", help="Bootstrap node IP address")
    parser.add_argument("--port", type=int, default=5000,
                      help="Port number (default: 5000)")
    parser.add_argument("--file", help="Read commands from input file")
    args = parser.parse_args()

    if args.bootstrap:
        node = ChordNode(port=args.port, bootstrap_node=None)
        print(f"🚀 Bootstrap node started at {node.ip}:{args.port}")
    else:
        if not args.ip:
            print("❌ Must specify bootstrap IP with --ip when not in bootstrap mode")
            return
        node = ChordNode(port=args.port, bootstrap_node={"ip": args.ip, "port": args.port})
        print(f"🌐 Node started at {node.ip}:{args.port}")

    cli_thread = threading.Thread(target=cli, args=(node, args.file))
    cli_thread.daemon = True
    cli_thread.start()

    try:
        node.start_server()
    except KeyboardInterrupt:
        print("\n🛑 Received shutdown signal")
        node.depart()
        sys.exit(0)

if __name__ == "__main__":
    main()