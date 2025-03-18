#!/usr/bin/env python3
import argparse
import subprocess
import socket
import sys
import time

def read_ips(filename):
    """Read IP addresses from a file."""
    with open(filename, 'r') as file:
        return [line.strip() for line in file]

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


def run_experiment(base_hostname, consistency, replication):
     # Read IPs from file
    IPs = read_ips("ips.txt")

    for i in range(5):
        hostname = f"{base_hostname}{i+1}"
        node1 = 2 * i
        node2 = 2 * i + 1
        signal_port1 = 6000 + node1
        signal_port2 = 6000 + node2

        command = f"""
        ssh {hostname} <<EOF
            cd Chordify
            nohup python3 run_experiments.py --node_number {node1} --consistency {consistency} --replication {replication} --bootstrap_ip 10.0.10.67 --bootstrap_port 5000 --signal_port {signal_port1} > node0{node1}_{consistency}_{replication}.log 2>&1 &
            sleep 0.5
            nohup python3 run_experiments.py --node_number {node2} --consistency {consistency} --replication {replication} --bootstrap_ip 10.0.10.67 --bootstrap_port 5000 --signal_port {signal_port2} > node0{node2}_{consistency}_{replication}.log 2>&1 &
            sleep 0.5
            exit
        EOF
        """

        success = execute_command(hostname, command)
        if not success:
            print(f"Failed to complete tasks on {hostname}. Exiting...")
            sys.exit(1)

    time.sleep(1)

    for _ in range(3):
        for i in range(5):
            ip = IPs[i]
            target_port1 = 6000 + 2*i
            target_port2 = 6000 + 2*i + 1
            trigger_signal(ip, target_port1)
            trigger_signal(ip, target_port2)
        time.sleep(3)

    for i in range(4,-1,-1):
            ip = IPs[i]
            target_port1 = 6000 + 2*i+1
            target_port2 = 6000 + 2*i
            trigger_signal(ip, target_port1)
            time.sleep(1)
            trigger_signal(ip, target_port2)
            time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description="SSH Experiment Runner for Chord Nodes")
    parser.add_argument('--base_hostname', type=str, default="team_3-vm", help="Base hostname for VMs (e.g., team3-vm)")
    args = parser.parse_args()

    for i in range(5):
        hostname = f"{args.base_hostname}{i+1}"
        command = f"""
        ssh {hostname} <<EOF
            cd Chordify
            git pull origin main
            exit
        EOF
        """
        success = execute_command(hostname, command)
        if not success:
            print(f"Failed to git pull on {hostname}. Exiting...")
            sys.exit(1)

    consistency = "linearizability"
    replication = 5
    run_experiment(args.base_hostname, consistency, replication)
   

if __name__ == "__main__":
    main()