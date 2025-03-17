#!/usr/bin/env python3
import argparse
import paramiko
import sys
import time


def ssh_execute_commands(hostname, username, commands, port=22, timeout=10):
    """
    Establish an SSH connection to a host and execute a list of commands.
    
    Args:
        hostname (str): The IP or hostname of the target machine.
        username (str): The SSH username.
        commands (list): List of commands to execute.
        port (int): SSH port (default: 22).
        timeout (int): Timeout for the SSH connection in seconds.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Initialize the SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Automatically add host key
        print(f"Connecting to {hostname} as {username}...")
        client.connect(hostname=hostname, username=username, port=port, timeout=timeout)

        # Open an interactive shell session
        for command in commands:
            print(f"Executing on {hostname}: {command}")
            stdin, stdout, stderr = client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()  # Wait for the command to complete
            if exit_status != 0:
                print(f"Error executing '{command}' on {hostname}: {stderr.read().decode()}")
            else:
                print(f"Output from {hostname}: {stdout.read().decode()}")

        # Close the connection
        client.close()
        print(f"Disconnected from {hostname}")
        return True

    except Exception as e:
        print(f"Failed to connect or execute commands on {hostname}: {e}")
        return False


def main():
    # Parse command-line arguments for IPs and username
    parser = argparse.ArgumentParser(description="SSH Experiment Runner for Chord Nodes")
    parser.add_argument('--username', type=str, required=True, help="SSH username for the VMs")
    parser.add_argument('--base_hostname', type=str, default="team_3-vm", help="Base hostname for VMs (e.g., team_3-vm)")
    args = parser.parse_args()

    # Loop over the range of VMs (team_3-vm0 to team_3-vm4)
    for i in range(5):
        hostname = f"{args.base_hostname}{i}"  # e.g., team_3-vm0, team_3-vm1, etc.
        node1 = 2 * i  # Even node number: 0, 2, 4, 6, 8
        node2 = 2 * i + 1  # Odd node number: 1, 3, 5, 7, 9
        signal_port1 = 6000 + node1  # e.g., 6000, 6002, ..., 6008
        signal_port2 = 6000 + node2  # e.g., 6001, 6003, ..., 6009

        # Define the commands to execute on the VM
        commands = [
            "cd Chordify",  # Navigate to the Chordify directory
            f"nohup python3 run_experiments.py --node_number {node1} --consistency linearizability --replication 1 --signal_port {signal_port1}",
            f"nohup python3 run_experiments.py --node_number {node2} --consistency linearizability --replication 1 --signal_port {signal_port2}"
        ]

        # Execute the commands via SSH
        success = ssh_execute_commands(
            hostname=hostname,
            username=args.username,
            commands=commands
        )

        if not success:
            print(f"Failed to complete tasks on {hostname}. Exiting...")
            sys.exit(1)

        # Optional: Add a small delay between VM connections to avoid overwhelming the network
        time.sleep(1)


if __name__ == "__main__":
    main()