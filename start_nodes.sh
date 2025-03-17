#!/bin/bash

# Define the bootstrap node details
BOOTSTRAP_IP="10.0.10.67"
BOOTSTRAP_PORT=5000

# Define the IPs and ports for each node (excluding the bootstrap node)
declare -A NODES=(
    ["NODE1_VM1"]="10.0.10.67:2000"
    ["NODE2_VM2"]="10.0.10.241:3000"
    ["NODE3_VM2"]="10.0.10.241:4000"
    ["NODE4_VM3"]="10.0.10.130:5000"
    ["NODE5_VM3"]="10.0.10.130:6000"
    ["NODE6_VM4"]="10.0.10.225:7000"
    ["NODE7_VM4"]="10.0.10.225:8000"
    ["NODE8_VM5"]="10.0.10.252:9000"
    ["NODE9_VM5"]="10.0.10.252:10000"
)

# Start the bootstrap node using its IP directly.
echo "Starting bootstrap node on $BOOTSTRAP_IP:$BOOTSTRAP_PORT..."
ssh -t $BOOTSTRAP_IP << 'EOF'
    # Change to the Chordify directory if needed
    cd ~/Chordify
    nohup python3 cli.py --bootstrap --port '"$BOOTSTRAP_PORT"' > /dev/null 2>&1 &
    exit
EOF
echo "Bootstrap node started on $BOOTSTRAP_IP:$BOOTSTRAP_PORT."

# Start the other nodes using their IP addresses directly.
for NODE in "${!NODES[@]}"; do
    IFS=':' read -r NODE_IP NODE_PORT <<< "${NODES[$NODE]}"
    echo "Starting $NODE on $NODE_IP at port $NODE_PORT..."
    ssh -t $NODE_IP << EOF
        cd ~/Chordify
        nohup python3 cli.py -ip $BOOTSTRAP_IP --port $NODE_PORT > /dev/null 2>&1 &
        exit
EOF
    echo "$NODE started on $NODE_IP at port $NODE_PORT."
done

echo "All nodes have been started."
