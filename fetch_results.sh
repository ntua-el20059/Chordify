#!/bin/bash

# Define the base directory
BASE_DIR="/home/ubuntu/Chordify"

# Define the list of VMs and their corresponding node directories
declare -A VMS=(
    ["team_3-vm2"]="node02 node03"
    ["team_3-vm3"]="node04 node05"
    ["team_3-vm4"]="node06 node07"
    ["team_3-vm5"]="node08 node09"
)

# Loop through each VM and copy the node directories
for VM in "${!VMS[@]}"; do
    NODES=${VMS[$VM]}
    for NODE in $NODES; do
        echo "Copying $NODE from $VM to $BASE_DIR on team_3-vm1..."
        scp -r "$VM:$BASE_DIR/$NODE" "$BASE_DIR/"
        if [ $? -eq 0 ]; then
            echo "Successfully copied $NODE from $VM."
        else
            echo "Failed to copy $NODE from $VM."
        fi
    done
done

echo "All node directories have been copied to team_3-vm1."