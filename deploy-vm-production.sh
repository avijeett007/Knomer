#!/bin/bash

# Production VM Deployment Script for Video Merger API
# This script sets up a production-ready VM with Application Gateway

set -e

echo "🚀 Starting Video Merger API Production Deployment"

# Configuration
RESOURCE_GROUP="video-merger-rg"
LOCATION="eastus"
VM_NAME="video-merger-vm"
VM_SIZE="Standard_D4s_v3"
VNET_NAME="video-merger-vnet"
APPGW_NAME="video-merger-appgw"

# Check if Azure CLI is installed and logged in
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first."
    exit 1
fi

if ! az account show &> /dev/null; then
    echo "❌ Not logged into Azure. Please run 'az login' first."
    exit 1
fi

echo "✅ Azure CLI is ready"

# Step 1: Create Resource Group
echo "📦 Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Step 2: Create Virtual Network
echo "🌐 Creating virtual network..."
az network vnet create \
  --resource-group $RESOURCE_GROUP \
  --name $VNET_NAME \
  --address-prefix 10.0.0.0/16 \
  --subnet-name vm-subnet \
  --subnet-prefix 10.0.1.0/24

az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name appgw-subnet \
  --address-prefix 10.0.2.0/24

# Step 3: Create Network Security Group
echo "🔒 Creating network security group..."
az network nsg create \
  --resource-group $RESOURCE_GROUP \
  --name video-merger-vm-nsg

az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name video-merger-vm-nsg \
  --name AllowSSH \
  --protocol Tcp \
  --priority 1000 \
  --destination-port-range 22 \
  --access Allow

az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name video-merger-vm-nsg \
  --name AllowAppGateway \
  --protocol Tcp \
  --priority 1100 \
  --destination-port-range 8001 \
  --source-address-prefix 10.0.2.0/24 \
  --access Allow

# Step 4: Create VM
echo "💻 Creating virtual machine..."
az vm create \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --image Ubuntu2204 \
  --size $VM_SIZE \
  --admin-username azureuser \
  --generate-ssh-keys \
  --vnet-name $VNET_NAME \
  --subnet vm-subnet \
  --nsg video-merger-vm-nsg \
  --public-ip-address video-merger-vm-ip \
  --public-ip-sku Standard

# Get VM IPs
VM_PRIVATE_IP=$(az vm show --resource-group $RESOURCE_GROUP --name $VM_NAME --show-details --query privateIps --output tsv)
VM_PUBLIC_IP=$(az vm show --resource-group $RESOURCE_GROUP --name $VM_NAME --show-details --query publicIps --output tsv)

echo "✅ VM Created:"
echo "   Private IP: $VM_PRIVATE_IP"
echo "   Public IP: $VM_PUBLIC_IP"

# Step 5: Create Application Gateway
echo "🌐 Creating Application Gateway..."
az network public-ip create \
  --resource-group $RESOURCE_GROUP \
  --name video-merger-appgw-ip \
  --allocation-method Static \
  --sku Standard

az network application-gateway create \
  --name $APPGW_NAME \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --subnet appgw-subnet \
  --capacity 1 \
  --sku Standard_v2 \
  --http-settings-cookie-based-affinity Disabled \
  --frontend-port 80 \
  --http-settings-port 8001 \
  --http-settings-protocol Http \
  --public-ip-address video-merger-appgw-ip \
  --servers $VM_PRIVATE_IP

# Create health probe
az network application-gateway probe create \
  --gateway-name $APPGW_NAME \
  --resource-group $RESOURCE_GROUP \
  --name health-probe \
  --protocol Http \
  --host-name-from-http-settings true \
  --path /health \
  --interval 30 \
  --timeout 30 \
  --threshold 3

# Update backend settings
az network application-gateway http-settings update \
  --gateway-name $APPGW_NAME \
  --resource-group $RESOURCE_GROUP \
  --name appGatewayBackendHttpSettings \
  --probe health-probe \
  --timeout 300

APPGW_PUBLIC_IP=$(az network public-ip show \
  --resource-group $RESOURCE_GROUP \
  --name video-merger-appgw-ip \
  --query ipAddress \
  --output tsv)

echo "✅ Application Gateway Created:"
echo "   Public IP: $APPGW_PUBLIC_IP"

# Step 6: Create setup script for VM
echo "📝 Creating VM setup script..."
cat > vm-setup.sh << 'EOF'
#!/bin/bash
set -e

echo "🔧 Setting up VM environment..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and tools
sudo apt install -y docker.io docker-compose git curl jq bc
sudo usermod -aG docker $USER
sudo systemctl enable docker
sudo systemctl start docker

# Create application directory
sudo mkdir -p /app/video-merger-api
sudo chown azureuser:azureuser /app/video-merger-api

echo "✅ VM setup complete!"
echo "Next steps:"
echo "1. Clone your repository to /app/video-merger-api"
echo "2. Configure .env.production with Supabase credentials"
echo "3. Run docker-compose -f docker-compose.production.yml up -d"
EOF

chmod +x vm-setup.sh

# Step 7: Copy setup script to VM and run it
echo "🚀 Setting up VM environment..."
scp -o StrictHostKeyChecking=no vm-setup.sh azureuser@$VM_PUBLIC_IP:~/
ssh -o StrictHostKeyChecking=no azureuser@$VM_PUBLIC_IP 'bash ~/vm-setup.sh'

echo ""
echo "🎉 Infrastructure Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. SSH into your VM:"
echo "   ssh azureuser@$VM_PUBLIC_IP"
echo ""
echo "2. Clone your repository:"
echo "   cd /app/video-merger-api"
echo "   git clone https://github.com/your-username/video-merger-api.git ."
echo ""
echo "3. Configure Supabase credentials in .env.production"
echo ""
echo "4. Deploy the application:"
echo "   docker-compose -f docker-compose.production.yml up -d"
echo ""
echo "🌐 Your API will be available at:"
echo "   Application Gateway: http://$APPGW_PUBLIC_IP"
echo "   Direct VM access: http://$VM_PUBLIC_IP:8001"
echo ""
echo "📖 For detailed setup instructions, see VM_DEPLOYMENT_GUIDE.md"
echo ""
echo "🔧 Resource Information:"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   VM Name: $VM_NAME"
echo "   VM Private IP: $VM_PRIVATE_IP"
echo "   VM Public IP: $VM_PUBLIC_IP"
echo "   Application Gateway: $APPGW_NAME"
echo "   Application Gateway IP: $APPGW_PUBLIC_IP"

# Clean up temporary files
rm -f vm-setup.sh

echo ""
echo "✅ Deployment script completed successfully!"
