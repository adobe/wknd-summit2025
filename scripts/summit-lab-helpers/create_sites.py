#!/usr/bin/env python3

import os
import time
import requests
import sys
import base64

# Check if ASO_TOKEN is set
if "ASO_TOKEN" not in os.environ:
    print("Error: ASO_TOKEN environment variable is not set")
    print("Please set it with: export ASO_TOKEN=your_token_here")
    sys.exit(1)

token = os.environ["ASO_TOKEN"]
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

def check_site_exists(base_url):
    """
    Check if a site with the given base URL already exists
    
    Args:
        base_url (str): The base URL to check
        
    Returns:
        bool: True if the site exists, False otherwise
    """
    # Encode the base URL to base64
    base64_url = base64.b64encode(base_url.encode()).decode()
    
    # Make the request to check if the site exists
    try:
        check_url = f"https://spacecat.experiencecloud.live/api/v1/sites/by-base-url/{base64_url}"
        response = requests.get(check_url, headers=headers)
        
        # If status code is 200, the site exists
        if response.status_code == 200:
            site_data = response.json()
            print(f"Site already exists with ID: {site_data.get('id', 'unknown')}")
            return True
        
        # If status code is 404, the site doesn't exist
        elif response.status_code == 404:
            return False
        
        # Handle other status codes
        else:
            print(f"Unexpected status code when checking site: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    
    except Exception as e:
        print(f"Error checking if site exists: {e}")
        return False

# Loop from 3 to 199
for i in range(2, 4):
    # Format the number with leading zeros
    site_num = f"{i:03d}"
    base_url = f"https://main--wknd-summit2025--adobe.aem.live/lab-337/{site_num}/"
    
    print(f"Processing site L337-{site_num}...")
    
    # Check if the site already exists
    if check_site_exists(base_url):
        print(f"Skipping site L337-{site_num} as it already exists")
        print("")
        continue
    
    print(f"Creating site L337-{site_num}...")
    
    # Prepare the data for the request
    data = {
        "organizationId": "d488fc90-d009-412c-82a1-70b338b1869c",
        "baseURL": base_url,
        "deliveryType": "aem_edge",
        "name": f"L337-{site_num}"
    }
    
    # Execute the request
    try:
        response = requests.post(
            "https://spacecat.experiencecloud.live/api/v1/sites",
            json=data,
            headers=headers
        )
        
        # Print status code and headers
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {response.headers}")
        
        # Print response body
        print(f"Response: {response.text}")
        
        # Check if request was successful
        if response.status_code >= 200 and response.status_code < 300:
            print(f"Successfully created site L337-{site_num}")
        else:
            print(f"Failed to create site L337-{site_num}")
    
    except Exception as e:
        print(f"Error creating site L337-{site_num}: {e}")
    
    print("")
    
    # Add a small delay between requests to avoid overwhelming the API
    time.sleep(1)

print("All sites processed!") 