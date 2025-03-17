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
 
 # Start the bootstrap node
 echo "Starting bootstrap node on $BOOTSTRAP_IP:$BOOTSTRAP_PORT..."
 ssh -t team_3-vm1 << EOF
     nohup python3 cli.py --bootstrap --port $BOOTSTRAP_PORT > /dev/null 2>&1 &
     exit
 EOF
 echo "Bootstrap node started on $BOOTSTRAP_IP:$BOOTSTRAP_PORT."
 
 # Start the other nodes
 for NODE in "${!NODES[@]}"; do
     IFS=':' read -r IP PORT <<< "${NODES[$NODE]}"
     # Extract the VM name from the node identifier (e.g., VM1, VM2, etc.)
     VM=$(echo "$NODE" | sed -E 's/NODE[0-9]_//')
     VM="team_3-${VM,,}"  # Convert to lowercase (e.g., team_3-vm1, team_3-vm2, etc.)
     
     echo "Starting $NODE on $VM at $IP:$PORT..."
     ssh -t $VM << EOF
         nohup python3 cli.py -ip $BOOTSTRAP_IP --port $PORT > /dev/null 2>&1 &
         exit
 EOF
     echo "$NODE started on $VM at $IP:$PORT."
 done
 
 echo "All nodes have been started."
