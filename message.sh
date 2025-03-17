#!/bin/bash

# Generic team setup script to be placed in each team's folder (output/team_X/)
# This script automatically detects which team it belongs to and sets up multi-login SSH configuration

# Get the current directory name to determine team number
CURRENT_DIR=$(basename "$(pwd)")
TEAM_NAME=$CURRENT_DIR

echo "Setting up multi-login SSH configuration for $TEAM_NAME..."

# Variables
CREDENTIALS_FILE="${TEAM_NAME}_credentials.csv"
IPS_FILE="${TEAM_NAME}_ips.csv"
S3_BUCKET="distributed-systems-course-team-keys-4cdcfb7e4d04685bbd448e40d9"
KEY_PATH="$HOME/.ssh/team_key.pem"
SSH_CONFIG_PATH="$HOME/.ssh/config"

# Step 1: Check if required files exist
echo "Step 1: Checking for required files..."
if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "Error: Credentials file not found at $CREDENTIALS_FILE"
    echo "Make sure you're running this script from your team folder."
    exit 1
fi

if [ ! -f "$IPS_FILE" ]; then
    echo "Error: IPs file not found at $IPS_FILE"
    echo "Make sure you're running this script from your team folder."
    exit 1
fi

if [ ! -f "team_guide.pdf" ]; then
    echo "Warning: team_guide.pdf not found in the current directory."
    echo "You may want to review the guide for complete instructions."
fi

echo "Required files found."

# Step 2: Configure AWS CLI with team credentials
echo "Step 2: Configuring AWS CLI with $TEAM_NAME credentials..."
# Extract credentials from CSV file (skip header line)
ACCESS_KEY=$(tail -n 1 "$CREDENTIALS_FILE" | cut -d ',' -f 4)
SECRET_KEY=$(tail -n 1 "$CREDENTIALS_FILE" | cut -d ',' -f 5)

if [ -z "$ACCESS_KEY" ] || [ -z "$SECRET_KEY" ]; then
    echo "Error: Could not extract access key or secret key from credentials file."
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Installing instructions:"
    echo "macOS: brew install awscli"
    echo "Windows: Download from AWS website"
    echo "Linux: sudo apt-get install awscli"
    echo ""
    echo "Please install AWS CLI and run this script again."
    exit 1
fi

# Create AWS credentials file
mkdir -p ~/.aws
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = $ACCESS_KEY
aws_secret_access_key = $SECRET_KEY
EOF

# Create AWS config file
cat > ~/.aws/config << EOF
[default]
region = eu-central-1
output = json
EOF

echo "AWS CLI configured successfully."

# Step 3: Download the private SSH key
echo "Step 3: Downloading private SSH key..."
mkdir -p ~/.ssh
aws s3 cp "s3://$S3_BUCKET/$TEAM_NAME/private_key.pem" "$KEY_PATH" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "Private key downloaded successfully."
    chmod 600 "$KEY_PATH"
    echo "Key permissions set to 600 (read/write for owner only)."
else
    echo "Error: Could not download private key from S3 bucket."
    echo "This could be due to:"
    echo "1. The S3 bucket doesn't exist or has a different name."
    echo "2. The credentials don't have permission to access the bucket."
    echo "3. The private key file doesn't exist in the expected location."
    echo "4. Network connectivity issues."
    
    # Check if we can list the bucket
    echo "Checking if we can access the S3 bucket..."
    aws s3 ls "s3://$S3_BUCKET" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "S3 bucket is accessible. Checking for the private key file..."
        aws s3 ls "s3://$S3_BUCKET/$TEAM_NAME/" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "Team directory exists in the bucket. Listing contents:"
            aws s3 ls "s3://$S3_BUCKET/$TEAM_NAME/"
        else
            echo "Team directory doesn't exist or is not accessible."
        fi
    else
        echo "Cannot access the S3 bucket. Check your credentials and permissions."
    fi
fi

# Step 4: Extract IPs for connection
echo "Step 4: Extracting connection information..."
# Extract IPs from CSV file (skip header line)
PUBLIC_IP=$(tail -n 1 "$IPS_FILE" | cut -d ',' -f 2)
PRIVATE_IPS=$(tail -n 1 "$IPS_FILE" | cut -d ',' -f 3-)

if [ -z "$PUBLIC_IP" ]; then
    echo "Error: Could not extract public IP from IPs file."
    exit 1
fi

# Format private IPs for display and use
IFS=',' read -ra IP_ARRAY <<< "$PRIVATE_IPS"

# Step 5: Set up SSH config for easier connections
echo "Step 5: Setting up SSH config for easier connections..."
# Create or append to SSH config file
touch "$SSH_CONFIG_PATH"
chmod 600 "$SSH_CONFIG_PATH"

# Add bastion host config
cat >> "$SSH_CONFIG_PATH" << EOF

# $TEAM_NAME Bastion Host
Host ${TEAM_NAME}-bastion
    HostName $PUBLIC_IP
    User ubuntu
    IdentityFile $KEY_PATH
    StrictHostKeyChecking no

EOF

# Add private VM configs
VM_COUNT=1
for IP in "${IP_ARRAY[@]}"; do
    # Remove any leading/trailing whitespace
    IP=$(echo "$IP" | xargs)
    if [ ! -z "$IP" ]; then
        cat >> "$SSH_CONFIG_PATH" << EOF
# $TEAM_NAME VM $VM_COUNT
Host ${TEAM_NAME}-vm$VM_COUNT
    HostName $IP
    User ubuntu
    IdentityFile $KEY_PATH
    ProxyJump ${TEAM_NAME}-bastion
    StrictHostKeyChecking no

EOF
        VM_COUNT=$((VM_COUNT+1))
    fi
done

echo "SSH config updated with $((VM_COUNT-1)) VMs for $TEAM_NAME."

# Step 6: Create helper scripts for common tasks
echo "Step 6: Creating helper scripts for common tasks..."

# Create script for connecting to bastion host
cat > "connect_bastion.sh" << EOF
#!/bin/bash
# Script to connect to the $TEAM_NAME bastion host
ssh ${TEAM_NAME}-bastion
EOF
chmod +x "connect_bastion.sh"

# Create script for connecting to VMs
cat > "connect_vm.sh" << EOF
#!/bin/bash
# Script to connect to a $TEAM_NAME VM

# Check if VM number is provided
if [ \$# -ne 1 ]; then
    echo "Usage: \$0 <vm_number>"
    echo "Example: \$0 1"
    echo "Available VMs: 1-$((VM_COUNT-1))"
    exit 1
fi

VM_NUMBER=\$1

if [ \$VM_NUMBER -lt 1 ] || [ \$VM_NUMBER -gt $((VM_COUNT-1)) ]; then
    echo "Error: VM number must be between 1 and $((VM_COUNT-1))"
    exit 1
fi

echo "Connecting to ${TEAM_NAME}-vm\$VM_NUMBER..."
ssh ${TEAM_NAME}-vm\$VM_NUMBER
EOF
chmod +x "connect_vm.sh"

# Create script for connecting to multiple VMs in separate terminals
cat > "connect_all.sh" << EOF
#!/bin/bash
# Script to open connections to all $TEAM_NAME VMs in separate terminals

# Function to detect the terminal emulator
detect_terminal() {
    # Print debug info
    echo "Debug: OSTYPE=\$OSTYPE"
    echo "Debug: uname=\$(uname)"
    
    # Check for macOS using multiple methods
    if [ "\$(uname)" = "Darwin" ]; then
        # macOS detected using uname
        echo "open -a Terminal"
    elif [ "\$OSTYPE" = "darwin"* ] || [[ "\$OSTYPE" == darwin* ]]; then
        # macOS detected using OSTYPE
        echo "open -a Terminal"
    elif command -v gnome-terminal &> /dev/null; then
        echo "gnome-terminal --"
    elif command -v konsole &> /dev/null; then
        echo "konsole -e"
    elif command -v xterm &> /dev/null; then
        echo "xterm -e"
    else
        echo ""
    fi
}

# For macOS, we can directly check using uname before trying the function
if [ "\$(uname)" = "Darwin" ]; then
    TERMINAL="open -a Terminal"
    echo "Debug: macOS detected using uname, setting TERMINAL to: \$TERMINAL"
else
    TERMINAL=\$(detect_terminal)
    echo "Debug: Terminal detection result: \$TERMINAL"
fi

if [ -z "\$TERMINAL" ]; then
    echo "Error: Could not detect terminal emulator. Please connect to VMs manually."
    echo "You can manually connect using:"
    echo "  - ./connect_bastion.sh (to connect to the bastion host)"
    echo "  - ./connect_vm.sh <number> (to connect to a specific VM)"
    exit 1
fi

echo "Opening connections to all VMs in separate terminals..."

# Connect to bastion host
\$TERMINAL ./connect_bastion.sh &

# Wait a bit for the bastion connection to establish
sleep 2

# Connect to each VM
for ((i=1; i<=$((VM_COUNT-1)); i++)); do
    \$TERMINAL ./connect_vm.sh \$i &
    sleep 1
done

echo "Connection windows opened for bastion host and $((VM_COUNT-1)) VMs."
EOF
chmod +x "connect_all.sh"

# Step 7: Test SSH connection to bastion host (if key was downloaded)
if [ -f "$KEY_PATH" ]; then
    echo "Step 7: Testing SSH connection to bastion host ($PUBLIC_IP)..."
    echo "Attempting to connect (timeout 5 seconds, non-interactive)..."
    ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@$PUBLIC_IP exit 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "Success: SSH connection to bastion host established!"
        CONNECTION_SUCCESS=true
    else
        echo "Warning: Could not establish SSH connection to bastion host."
        echo "This could be due to:"
        echo "1. The bastion host is not running or is unreachable."
        echo "2. The SSH service on the bastion host is not running."
        echo "3. A firewall is blocking the SSH connection."
        echo "4. The SSH key is incorrect for this host."
        CONNECTION_SUCCESS=false
    fi
else
    echo "Step 7: Skipping SSH connection test as private key was not downloaded."
    CONNECTION_SUCCESS=false
fi

# Step 8: Provide connection instructions
echo ""
echo "===== CONNECTION INSTRUCTIONS FOR $TEAM_NAME ====="
echo ""
echo "The following helper scripts have been created in your team folder:"
echo ""
echo "1. connect_bastion.sh"
echo "   - Connects to the bastion host"
echo "   - Usage: ./connect_bastion.sh"
echo ""
echo "2. connect_vm.sh <vm_number>"
echo "   - Connects to a specific VM through the bastion host"
echo "   - Usage: ./connect_vm.sh 1"
echo ""
echo "3. connect_all.sh"
echo "   - Opens connections to all VMs in separate terminals"
echo "   - Usage: ./connect_all.sh"
echo ""
echo "You can also use the SSH aliases set up in your SSH config:"
echo "- ssh ${TEAM_NAME}-bastion (connects to bastion host)"
echo "- ssh ${TEAM_NAME}-vm1 (connects to VM 1 through bastion host)"
echo "- ssh ${TEAM_NAME}-vm2 (connects to VM 2 through bastion host)"
echo "- etc."
echo ""

if [ "$CONNECTION_SUCCESS" = true ]; then
    echo "Setup complete! SSH connection to the bastion host was successful."
    echo "You should now be able to connect to the private VMs through the bastion host."
else
    echo "Setup partially complete. SSH connection to the bastion host could not be verified."
    echo "Please check the error messages above and try to resolve any issues before connecting."
fi
