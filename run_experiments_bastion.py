#!/usr/bin/env python3
import argparse
import subprocess
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
            f"  nohup python3 run_experiments.py --node_number {node1} --consistency linearizability --replication 1 --bootstrap_ip 10.0.10.67 --bootstrap_port 5000 --signal_port {signal_port1} > node0{node1}.log 2>&1 & \n"+
            "   sleep 1\n"+
            f"  nohup python3 run_experiments.py --node_number {node2} --consistency linearizability --replication 1 --bootstrap_ip 10.0.10.67 --bootstrap_port 5000 --signal_port {signal_port2} > node0{node2}.log 2>&1 & "+
            "   sleep 1\n"+
            "   exit\nEOF")
        

        success = execute_command(hostname, command)
        if not success:
            print(f"Failed to complete tasks on {hostname}. Exiting...")
            sys.exit(1)


if __name__ == "__main__":
    main()