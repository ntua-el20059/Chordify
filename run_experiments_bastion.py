#!/usr/bin/env python3
import argparse
import subprocess
import socket
import sys
import time


def execute_command(hostname, command):
    try:
        print(f"Executing on {hostname}:\n{command}")
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.stdout:
            print(f"Output from {hostname}:\n{result.stdout.decode()}")
        if result.stderr:
            print(f"Errors from {hostname}:\n{result.stderr.decode()}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute commands on {hostname}: {e.stderr.decode()}")
        return False

def trigger_signal(host, port, message="go"):
    """
    Connect to the given host and port and send a signal message.
    
    This function acts as a client that triggers the server's wait_for_signal() function.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(message.encode())
            print(f"Sent signal '{message}' to {host}:{port}")
    except Exception as e:
        print(f"Error triggering signal: {e}")


def main():
    parser = argparse.ArgumentParser(description="SSH Experiment Runner for Chord Nodes")
    parser.add_argument('--base_hostname', type=str, default="team_3-vm", help="Base hostname for VMs (e.g., team3-vm)")
    args = parser.parse_args()

    for i in range(5):
        hostname = f"{args.base_hostname}{i+1}"
        node1 = 2 * i
        node2 = 2 * i + 1
        signal_port1 = 6000 + node1
        signal_port2 = 6000 + node2

        # Key Fix: Combine the nohup commands into one string without semicolon after &
        command=(f"ssh {hostname}<<EOF\n" +
            "   cd Chordify\n"+
            "   git pull\n"+
            f"  nohup python3 run_experiments.py --node_number {node1} --consistency linearizability --replication 1 --bootstrap_ip 10.0.10.67 --bootstrap_port 5000 --signal_port {signal_port1} > node0{node1}.log 2>&1 & \n"+
            "   sleep 1\n"+
            f"  nohup python3 run_experiments.py --node_number {node2} --consistency linearizability --replication 1 --bootstrap_ip 10.0.10.67 --bootstrap_port 5000 --signal_port {signal_port2} > node0{node2}.log 2>&1 & "+
            "   sleep 1\n"+
            "   exit\nEOF")
        

        success = execute_command(hostname, command)
        if not success:
            print(f"Failed to complete tasks on {hostname}. Exiting...")
            sys.exit(1)

    for _ in range(3):
        time.sleep(10)
        for i in range(10):
            hostname = f"{args.base_hostname}{i+1}"
            target_port = 6000 + i
            trigger_signal(hostname, target_port)


if __name__ == "__main__":
    main()