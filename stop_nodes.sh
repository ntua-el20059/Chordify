#!/bin/bash
BOOTSTRAP_IP="10.0.10.67"

# Define the IPs for each node (excluding the bootstrap node)
declare -A NODES=(
    ["NODE1_VM1"]="10.0.10.67"
    ["NODE2_VM2"]="10.0.10.241"
    ["NODE3_VM2"]="10.0.10.241"
    ["NODE4_VM3"]="10.0.10.130"
    ["NODE5_VM3"]="10.0.10.130"
    ["NODE6_VM4"]="10.0.10.225"
    ["NODE7_VM4"]="10.0.10.225"
    ["NODE8_VM5"]="10.0.10.252"
    ["NODE9_VM5"]="10.0.10.252"
)

# SSH options to bypass host key verification, force non-interactive mode, and use the team key.
SSH_OPTS="-i ~/.ssh/team_key.pem -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes"

# Stop the bootstrap node.
echo "Stopping bootstrap node on $BOOTSTRAP_IP..."
ssh $SSH_OPTS ubuntu@$BOOTSTRAP_IP << EOF
    sudo pkill -f "cli.py"
    exit
EOF
echo "Bootstrap node stopped on $BOOTSTRAP_IP."

# Stop the other nodes.
for NODE in "${!NODES[@]}"; do
    NODE_IP="${NODES[$NODE]}"
    echo "Stopping $NODE on $NODE_IP..."
    ssh $SSH_OPTS ubuntu@$NODE_IP << EOF
        sudo pkill -f "cli.py"
        exit
EOF
    echo "$NODE stopped on $NODE_IP."
done

echo "All nodes have been stopped."
