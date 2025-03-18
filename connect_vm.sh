#!/bin/bash
# Script to connect to a team_3 VM

# Check if VM number is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <vm_number>"
    echo "Example: $0 1"
    echo "Available VMs: 1-5"
    exit 1
fi

VM_NUMBER=$1

if [ $VM_NUMBER -lt 1 ] || [ $VM_NUMBER -gt 5 ]; then
    echo "Error: VM number must be between 1 and 5"
    exit 1
fi

echo "Connecting to team_3-vm$VM_NUMBER..."
ssh team_3-vm$VM_NUMBER 
