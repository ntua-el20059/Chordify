#!/usr/bin/env python3
import argparse
import subprocess
import sys
import time


def ssh_execute_commands(hostname, commands):
    """
    Execute a list of commands on a remote host using the `ssh` command.
    
    Args:
        hostname (str): The hostname of the target machine (e.g., team3-vm1).
        commands (list): List of commands to execute on the remote host.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Combine the commands into a single string to execute on the remote host
        command_str = "; ".join(commands)
        
        # Construct the SSH command
        ssh_command = f"ssh {hostname} '{command_str}'"
        
        print(f"Executing on {hostname}: {ssh_command}")
        
        # Run the SSH command using subprocess
        result = subprocess.run(ssh_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Print the output
        if result.stdout:
            print(f"Output from {hostname}:\n{result.stdout.decode()}")
        if result.stderr:
            print(f"Errors from {hostname}:\n{result.stderr.decode()}")
        
        return True

    except subprocess.CalledProcessError as e:
        print(f"Failed to execute commands on {hostname}: {e.stderr.decode()}")
        return False


def main():
    # Parse command-line arguments for the base hostname
    parser = argparse.ArgumentParser(description="SSH Experiment Runner for Chord Nodes")
    parser.add_argument('--base_hostname', type=str, default="team_3-vm", help="Base hostname for VMs (e.g., team3-vm)")
    args = parser.parse_args()

    # Loop over the range of VMs (team3-vm1 to team3-vm5)
    for i in range(5):
        hostname = f"{args.base_hostname}{i+1}"  # e.g., team3-vm1, team3-vm2, etc.
        node1 = 2 * i  # Even node number: 0, 2, 4, 6, 8
        node2 = 2 * i + 1  # Odd node number: 1, 3, 5, 7, 9
        signal_port1 = 6000 + node1  # e.g., 6000, 6002, ..., 6008
        signal_port2 = 6000 + node2  # e.g., 6001, 6003, ..., 6009

        # Define the commands to execute on the VM
        commands = [
            "cd Chordify",  # Navigate to the Chordify directory
            f"nohup python3 run_experiments.py --node_number {node1} --consistency linearizability --replication 1 --signal_port {signal_port1} 2>&1 &",
            f"nohup python3 run_experiments.py --node_number {node2} --consistency linearizability --replication 1 --signal_port {signal_port2} 2>&1 &"
        ]

        # Execute the commands via SSH
        success = ssh_execute_commands(
            hostname=hostname,
            commands=commands
        )

        if not success:
            print(f"Failed to complete tasks on {hostname}. Exiting...")
            sys.exit(1)

        # Optional: Add a small delay between VM connections to avoid overwhelming the network
        time.sleep(1)


if __name__ == "__main__":
    main()
