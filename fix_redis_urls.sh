#!/bin/bash

# Script to check and fix Redis URLs in .env.production

ENV_FILE=".env.production"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found. Please run this script in the root directory of your project."
    exit 1
fi

# Backup original file
cp "$ENV_FILE" "${ENV_FILE}.bak"
echo "Backed up original $ENV_FILE to ${ENV_FILE}.bak"

# Process Redis URLs
while IFS= read -r line; do
    # Check if line contains Redis URL with rediss:// scheme
    if [[ "$line" == *"REDIS_URL"*"rediss://"* || "$line" == *"CELERY_BROKER_URL"*"rediss://"* || "$line" == *"CELERY_RESULT_BACKEND"*"rediss://"* ]]; then
        # Check if ssl_cert_reqs parameter is missing
        if [[ "$line" != *"ssl_cert_reqs"* ]]; then
            # If URL already has query parameters
            if [[ "$line" == *"?"* ]]; then
                new_line="${line}&ssl_cert_reqs=CERT_NONE"
            else
                new_line="${line}?ssl_cert_reqs=CERT_NONE"
            fi
            echo "Fixing: $line"
            echo "To: $new_line"
            # Replace line in file
            sed -i.tmp "s|$line|$new_line|" "$ENV_FILE"
        else
            echo "OK: $line (already has ssl_cert_reqs)"
        fi
    fi
done < "$ENV_FILE"

# Clean up temporary sed file
rm -f "${ENV_FILE}.tmp"

echo "Redis URLs in $ENV_FILE have been checked and fixed."
echo "After verifying the changes, you should restart your Docker containers:"
echo "docker-compose -f docker-compose.production.yml down && docker-compose -f docker-compose.production.yml up -d"
