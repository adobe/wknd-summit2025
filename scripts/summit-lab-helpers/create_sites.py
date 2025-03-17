#!/usr/bin/env python3

import os
import time
import requests
import sys
import base64
import argparse
import re

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

# Create an instance of GoogleDocCloner to work with Google Drive folders
try:
    from clone_oppt_file import GoogleDocCloner
    doc_cloner = GoogleDocCloner()
    print("Successfully initialized GoogleDocCloner for folder management")
except ImportError as e:
    print(f"Error importing GoogleDocCloner: {e}")
    print("Make sure clone_oppt_file.py is in the same directory")
    sys.exit(1)
except Exception as e:
    print(f"Error initializing GoogleDocCloner: {e}")
    print("Make sure credentials.json exists and is valid")
    sys.exit(1)

# Import the AemSitesOptimizerBackoffice class for opportunity handling
try:
    from clone_oppt import AemSitesOptimizerBackoffice
    print("Successfully imported AemSitesOptimizerBackoffice for opportunity management")
except ImportError as e:
    print(f"Warning: Could not import AemSitesOptimizerBackoffice: {e}")
    print("Opportunity synchronization will not be available")
    AemSitesOptimizerBackoffice = None

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

def get_or_create_config(site_id, site_num):
    """
    Check if a site has a Google Drive configuration, and add it if not present
    
    Args:
        site_id (str): The SpaceCat site ID
        site_num (str): The site number in 3-digit format (e.g. "001", "002", etc.)
        
    Returns:
        dict: The result of the operation with status and details
    """
    # Import re for regex matching
    import re
    
    print(f"Checking Google Drive configuration for site ID: {site_id}")
    
    # 1. Get the current site configuration
    try:
        get_url = f"https://spacecat.experiencecloud.live/api/v1/sites/{site_id}"
        response = requests.get(get_url, headers=headers)
        
        # Check if request was successful
        if response.status_code != 200:
            print(f"Failed to get site configuration. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return {
                "success": False,
                "error": f"Failed to get site configuration. Status code: {response.status_code}"
            }
        
        # Parse the response
        site_config = response.json()
        
        # 2. Check if hlxConfig with Google Drive source already exists
        hlx_config = site_config.get('hlxConfig', {})
        content_config = hlx_config.get('content', {})
        source_config = content_config.get('source', {})
        
        # Get the expected folder ID for this site number
        root_folder_id = "1nljb8SfLhSWMHiE-kTUl3b-93XmYH_Wg"
        expected_folder_id = doc_cloner.get_or_create_folder_id_by_name(site_num)
        # expected_folder_id = root_folder_id  # override it for testing
        if not expected_folder_id:
            return {
                "success": False,
                "error": f"Could not find or create Google Drive folder for site number: {site_num}"
            }
        
        expected_url = f"https://drive.google.com/drive/u/0/folders/{expected_folder_id}"
        
        if source_config.get('type') == 'drive.google':
            current_url = source_config.get('url', '')
            print(f"Site has Google Drive configuration: {current_url}")
            
            # Extract the folder ID from the current URL
            match = re.search(r'folders/([a-zA-Z0-9_-]+)', current_url)
            current_folder_id = match.group(1) if match else None
            
            # Check if the current URL points to the correct folder
            if current_folder_id == expected_folder_id:
                print(f"Google Drive configuration is already correct")
                return {
                    "success": True,
                    "message": "Google Drive configuration already exists and is correct",
                    "config": source_config
                }
            else:
                print(f"Google Drive configuration exists but points to the wrong folder")
                print(f"Current folder ID: {current_folder_id}")
                print(f"Expected folder ID: {expected_folder_id}")
                
                # Update the configuration with the correct folder
                new_hlx_config = {
                    "hlxConfig": {
                        "content": {
                            "source": {
                                "type": "drive.google", 
                                "url": expected_url
                            }
                        }
                    }
                }
                
                # Update the site configuration with PATCH request
                patch_response = requests.patch(
                    get_url,
                    json=new_hlx_config,
                    headers=headers
                )
                
                # Check if PATCH request was successful
                if patch_response.status_code >= 200 and patch_response.status_code < 300:
                    print(f"Successfully updated site with the correct Google Drive configuration")
                    return {
                        "success": True,
                        "message": "Successfully updated Google Drive configuration to the correct folder",
                        "config": new_hlx_config['hlxConfig']['content']['source']
                    }
                else:
                    print(f"Failed to update site configuration. Status code: {patch_response.status_code}")
                    print(f"Response: {patch_response.text}")
                    return {
                        "success": False,
                        "error": f"Failed to update site configuration. Status code: {patch_response.status_code}"
                    }
        
        # If no Google Drive configuration exists, create one
        
        # 3. Create the updated configuration
        new_hlx_config = {
            "hlxConfig": {
                "content": {
                    "source": {
                        "type": "drive.google",
                        "url": expected_url
                    }
                }
            }
        }
        
        # 4. Update the site configuration with PATCH request
        patch_response = requests.patch(
            get_url,
            json=new_hlx_config,
            headers=headers
        )
        
        # Check if PATCH request was successful
        if patch_response.status_code >= 200 and patch_response.status_code < 300:
            print(f"Successfully updated site with Google Drive configuration")
            return {
                "success": True,
                "message": "Successfully added Google Drive configuration",
                "config": new_hlx_config['hlxConfig']['content']['source']
            }
        else:
            print(f"Failed to update site configuration. Status code: {patch_response.status_code}")
            print(f"Response: {patch_response.text}")
            return {
                "success": False,
                "error": f"Failed to update site configuration. Status code: {patch_response.status_code}"
            }
    
    except Exception as e:
        print(f"Error updating site configuration: {e}")
        return {
            "success": False,
            "error": f"Error updating site configuration: {str(e)}"
        }

def sync_gdrive(start_folder=0, end_folder=200, report_path=None, files_to_sync=None, files_override=False):
    """
    Synchronize Google Drive folders and files for a range of site numbers
    
    This function:
    1. Ensures folders exist for each site number in the range
    2. If files_to_sync is provided, copies those files to each folder
    3. Generates a detailed report of the synchronization process
    
    Args:
        start_folder (int): The starting folder number
        end_folder (int): The ending folder number (exclusive)
        report_path (str, optional): Path to save the sync report to
        files_to_sync (list, optional): List of Google Doc URLs to copy to each folder
        files_override (bool, optional): Whether to override existing files when syncing (default: False)
        
    Returns:
        tuple: (success_count, failure_count, results_dict)
    """
    print(f"\nSynchronizing Google Drive folders from {start_folder:03d} to {end_folder-1:03d}...")
    
    # Track success and failure counts
    success_count = 0
    failure_count = 0
    results = {}
    
    # Calculate total number of folders to sync
    total_folders = end_folder - start_folder
    
    # Sync each folder in the range
    for i, num in enumerate(range(start_folder, end_folder)):
        folder_num = f"{num:03d}"
        
        # Show progress
        progress = (i + 1) / total_folders * 100
        print(f"\n[{progress:.1f}%] Syncing folder {folder_num}...", end=" ")
        
        try:
            # Try to get or create the folder
            folder_id = doc_cloner.get_or_create_folder_id_by_name(folder_num)
            
            if folder_id:
                success_count += 1
                status = "SUCCESS"
                url = f"https://drive.google.com/drive/u/0/folders/{folder_id}"
                print(f"SUCCESS - Folder ID: {folder_id}")
                print(f"Google Drive URL: {url}")
                
                # Store result
                results[folder_num] = {
                    "status": status,
                    "folder_id": folder_id,
                    "url": url
                }
                
                # Sync files if provided
                if files_to_sync:
                    file_results = []
                    for file_url in files_to_sync:
                        try:
                            # Construct a base URL for the folder
                            base_url = f"https://main--wknd-summit2025--adobe.aem.live/lab-337/{folder_num}/"
                            
                            # Use the clone_google_doc method to sync the file
                            clone_result = doc_cloner.clone_google_doc(file_url, base_url, override=files_override)
                            
                            file_results.append({
                                "file_url": file_url,
                                "success": clone_result.get("success", False),
                                "details": clone_result
                            })
                            
                            if clone_result.get("success", False):
                                print(f"  - Synced file: {clone_result.get('original_filename', 'Unknown')}")
                            else:
                                print(f"  - Failed to sync file: {file_url} - {clone_result.get('error', 'Unknown error')}")
                                
                        except Exception as file_e:
                            file_results.append({
                                "file_url": file_url,
                                "success": False,
                                "error": str(file_e)
                            })
                            print(f"  - Error syncing file {file_url}: {str(file_e)}")
                    
                    # Add file sync results to the folder results
                    results[folder_num]["files"] = file_results
                
            else:
                failure_count += 1
                status = "FAILED"
                print(f"FAILED - Could not find or create folder")
                
                # Store result
                results[folder_num] = {
                    "status": status,
                    "error": "Could not find or create folder"
                }
        except Exception as e:
            failure_count += 1
            status = "ERROR"
            error_msg = str(e)
            print(f"ERROR - Exception occurred: {error_msg}")
            
            # Store result
            results[folder_num] = {
                "status": status,
                "error": error_msg
            }
        
        # Add a small delay to avoid overwhelming the Google Drive API
        time.sleep(0.2)
    
    # Print summary
    print(f"\nGoogle Drive synchronization complete.")
    print(f"Successful folders: {success_count}")
    print(f"Failed folders: {failure_count}")
    print(f"Total folders processed: {total_folders}")
    
    # Save report if requested
    if report_path:
        try:
            import json
            with open(report_path, 'w') as f:
                json.dump({
                    "summary": {
                        "success_count": success_count,
                        "failure_count": failure_count,
                        "total_processed": total_folders
                    },
                    "results": results
                }, f, indent=2)
            print(f"Sync report saved to: {report_path}")
        except Exception as e:
            print(f"Failed to save sync report: {e}")
    
    return success_count, failure_count, results

def sync_opportunities(start_site=0, end_site=200, token=None, report_path=None):
    """
    Synchronize opportunities to sites in the specified range
    
    This function:
    1. Loads opportunity definitions from JSON files
    2. Uses AemSitesOptimizerBackoffice to clone opportunities to each site
    3. Generates a detailed report of the synchronization process
    
    Args:
        start_site (int): The starting site number
        end_site (int): The ending site number (exclusive)
        token (str): The authorization token for the AEM Sites Optimizer API
        report_path (str, optional): Path to save the sync report to
        
    Returns:
        dict: Results of the opportunity synchronization
    """
    if AemSitesOptimizerBackoffice is None:
        print("\nOpportunity synchronization is not available because AemSitesOptimizerBackoffice could not be imported.")
        return {"error": "AemSitesOptimizerBackoffice not available"}
    
    if not token:
        print("\nError: Token is required for opportunity synchronization.")
        return {"error": "Token is required"}
    
    print(f"\nSynchronizing opportunities for sites from {start_site:03d} to {end_site-1:03d}...")
    
    # Opportunity definitions
    opportunity_files = {
        "broken_links": "./oppt/opp--broken-internal-links--3_7_2025.json",
        "low_ctr": "./oppt/opp--high-organic-low-ctr--3_7_2025.json"
    }
    
    # Initialize the backoffice client
    backoffice = AemSitesOptimizerBackoffice(token=token)
    
    # Track results
    results = {
        "summary": {
            "total_sites": end_site - start_site,
            "success_count": 0,
            "failure_count": 0
        },
        "sites": {}
    }
    
    # Verify the broken links opportunity file exists
    if not os.path.exists(opportunity_files["broken_links"]):
        print(f"Error: Broken links opportunity file not found at {opportunity_files['broken_links']}")
        return {"error": f"Opportunity file not found: {opportunity_files['broken_links']}"}
    
    # Process each site
    for i, num in enumerate(range(start_site, end_site)):
        site_num = f"{num:03d}"
        site_base_url = f"https://main--wknd-summit2025--adobe.aem.live/lab-337/{site_num}/"
        
        # Show progress
        progress = (i + 1) / (end_site - start_site) * 100
        print(f"\n[{progress:.1f}%] Processing site {site_num}...")
        
        # Initialize site results
        site_results = {
            "site_num": site_num,
            "base_url": site_base_url,
            "site_id": None,
            "opportunities": {}
        }
        
        # Get site ID
        try:
            # Encode the base URL to base64
            base64_url = base64.b64encode(site_base_url.encode()).decode()
            check_url = f"https://spacecat.experiencecloud.live/api/v1/sites/by-base-url/{base64_url}"
            response = requests.get(check_url, headers=headers)
            
            if response.status_code == 200:
                site_data = response.json()
                site_id = site_data.get('id')
                if site_id:
                    site_results["site_id"] = site_id
                    print(f"  Found site ID: {site_id}")
                    
                    # Delete existing opportunities first to avoid duplicates
                    delete_result = _delete_opportunities(site_id, token)
                    site_results["deleted_opportunities"] = delete_result
                    if delete_result.get("success", False):
                        print(f"  ✓ Deleted {delete_result.get('count', 0)} existing opportunities")
                    else:
                        print(f"  ⚠ Failed to delete some existing opportunities: {delete_result.get('error', 'Unknown error')}")
                    
                    # 1. Broken internal links opportunity
                    print(f"  Syncing 'Broken Internal Links' opportunity...")
                    try:
                        broken_links_result = backoffice.clone_opportunity(
                            site_id=site_id,
                            oppt_file_path=opportunity_files["broken_links"]
                        )
                        
                        site_results["opportunities"]["broken_links"] = {
                            "success": True,
                            "details": broken_links_result
                        }
                        print(f"  ✓ Successfully synced 'Broken Internal Links' opportunity")
                        
                    except Exception as oppt_e:
                        site_results["opportunities"]["broken_links"] = {
                            "success": False,
                            "error": str(oppt_e)
                        }
                        print(f"  ✗ Failed to sync 'Broken Internal Links' opportunity: {str(oppt_e)}")
                    
                    # 2. High organic traffic low CTR opportunity
                    if os.path.exists(opportunity_files["low_ctr"]):
                        print(f"  Syncing 'High Organic Traffic Low CTR' opportunity...")
                        try:
                            low_ctr_result = backoffice.clone_opportunity(
                                site_id=site_id,
                                oppt_file_path=opportunity_files["low_ctr"]
                            )
                            
                            site_results["opportunities"]["low_ctr"] = {
                                "success": True,
                                "details": low_ctr_result
                            }
                            print(f"  ✓ Successfully synced 'High Organic Traffic Low CTR' opportunity")
                            
                        except Exception as oppt_e:
                            site_results["opportunities"]["low_ctr"] = {
                                "success": False,
                                "error": str(oppt_e)
                            }
                            print(f"  ✗ Failed to sync 'High Organic Traffic Low CTR' opportunity: {str(oppt_e)}")
                    else:
                        print(f"  ⚠ Skipping 'High Organic Traffic Low CTR' opportunity (file not found)")
                        site_results["opportunities"]["low_ctr"] = {
                            "success": False,
                            "error": f"File not found: {opportunity_files['low_ctr']}"
                        }
                    
                    # Update success/failure count
                    if any(oppt["success"] for oppt in site_results["opportunities"].values()):
                        results["summary"]["success_count"] += 1
                    else:
                        results["summary"]["failure_count"] += 1
                else:
                    print(f"  ✗ Failed to get site ID from response")
                    site_results["error"] = "Failed to get site ID from response"
                    results["summary"]["failure_count"] += 1
            else:
                print(f"  ✗ Site not found or error occurred: {response.status_code}")
                site_results["error"] = f"Site not found or error occurred: {response.status_code}"
                results["summary"]["failure_count"] += 1
        
        except Exception as e:
            print(f"  ✗ Error processing site {site_num}: {str(e)}")
            site_results["error"] = str(e)
            results["summary"]["failure_count"] += 1
        
        # Add site results to overall results
        results["sites"][site_num] = site_results
        
        # Add a small delay to avoid overwhelming the API
        time.sleep(0.5)
    
    # Print summary
    print(f"\nOpportunity synchronization complete.")
    print(f"Successfully processed: {results['summary']['success_count']} sites")
    print(f"Failed to process: {results['summary']['failure_count']} sites")
    print(f"Total sites processed: {results['summary']['total_sites']}")
    
    # Save report if requested
    if report_path:
        try:
            import json
            with open(report_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Opportunity sync report saved to: {report_path}")
        except Exception as e:
            print(f"Failed to save opportunity sync report: {e}")
    
    return results

def _delete_opportunities(site_id, token):
    """
    Private method to delete all existing opportunities for a site
    
    Args:
        site_id (str): The site ID
        token (str): The authorization token for the AEM Sites Optimizer API
        
    Returns:
        dict: Results of the deletion operation
    """
    result = {
        "success": True,
        "count": 0,
        "deleted": [],
        "failed": []
    }
    
    # Create authorization headers with token
    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Step 1: List all opportunities for the site
        list_url = f"https://spacecat.experiencecloud.live/api/v1/sites/{site_id}/opportunities"
        list_response = requests.get(list_url, headers=auth_headers)
        
        if list_response.status_code != 200:
            result["success"] = False
            result["error"] = f"Failed to list opportunities: Status code {list_response.status_code}"
            return result
        
        opportunities = list_response.json()
        
        # If no opportunities found, return early
        if not opportunities or len(opportunities) == 0:
            return result
        
        # Step 2: Delete each opportunity
        for opportunity in opportunities:
            oppt_id = opportunity.get("id")
            if not oppt_id:
                continue
                
            try:
                # Delete the opportunity
                delete_url = f"https://spacecat.experiencecloud.live/api/v1/sites/{site_id}/opportunities/{oppt_id}"
                delete_response = requests.delete(delete_url, headers=auth_headers)
                
                # Check if deletion was successful
                if delete_response.status_code >= 200 and delete_response.status_code < 300:
                    result["deleted"].append({
                        "id": oppt_id,
                        "status": delete_response.status_code
                    })
                    result["count"] += 1
                else:
                    result["failed"].append({
                        "id": oppt_id,
                        "status": delete_response.status_code,
                        "response": delete_response.text
                    })
                    
            except Exception as e:
                result["failed"].append({
                    "id": oppt_id,
                    "error": str(e)
                })
        
        # Set success to False if any deletion failed
        if result["failed"]:
            result["success"] = False
            result["error"] = f"Failed to delete {len(result['failed'])} opportunities"
        
    except Exception as e:
        result["success"] = False
        result["error"] = f"Error deleting opportunities: {str(e)}"
    
    return result

def update_sites_csv(output_file="sites.csv", org_id="d488fc90-d009-412c-82a1-70b338b1869c", start_site=None, end_site=None):
    """
    Update a CSV file with site information including ID, baseURL, and baseDocURL
    
    This function:
    1. Retrieves all sites for the given organization
    2. For each site, extracts its ID and baseURL
    3. If the site number is within the start_site and end_site range, attempts to find its Google Drive document
    4. Writes all this information to a CSV file
    
    Args:
        output_file (str): Path to the output CSV file
        org_id (str): The organization ID
        start_site (int, optional): Starting site number to update (inclusive)
        end_site (int, optional): Ending site number to update (exclusive)
        
    Returns:
        dict: Results of the operation with success status and details
    """
    import csv
    import re
    import os
    
    print(f"\nUpdating sites CSV file: {output_file}")
    if start_site is not None and end_site is not None:
        print(f"Updating baseDocURL for sites from {start_site:03d} to {end_site-1:03d} only")
    
    # Results tracking
    results = {
        "success": True,
        "total_sites": 0,
        "sites_processed": 0,
        "sites_with_doc_url": 0,
        "errors": []
    }
    
    # Create initial CSV file if it doesn't exist
    if not os.path.exists(output_file):
        try:
            with open(output_file, 'w', newline='') as csvfile:
                fieldnames = ['id', 'baseURL', 'baseDocURL']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
            print(f"Created new CSV file: {output_file}")
        except Exception as e:
            print(f"Error creating CSV file: {str(e)}")
            results["success"] = False
            results["errors"].append(f"Error creating CSV file: {str(e)}")
            return results
    
    try:
        # Step 1: Get all sites for the organization
        sites_url = f"https://spacecat.experiencecloud.live/api/v1/organizations/{org_id}/sites"
        response = requests.get(sites_url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error retrieving sites: Status code {response.status_code}")
            print(f"Response: {response.text}")
            results["success"] = False
            results["errors"].append(f"Failed to retrieve sites: {response.status_code}")
            return results
        
        sites = response.json()
        results["total_sites"] = len(sites)
        
        print(f"Retrieved {len(sites)} sites from the organization")
        
        # Read the existing CSV content into memory
        existing_data = {}
        try:
            with open(output_file, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    existing_data[row['id']] = row
        except Exception as e:
            print(f"Warning: Could not read existing CSV data: {str(e)}")
        
        # Create a new list to hold updated entries
        updated_entries = []
            
        # Step 2: Process each site
        for site in sites:
            site_id = site.get('id')
            base_url = site.get('baseURL')
            
            # Initialize with existing data or create new entry
            entry = existing_data.get(site_id, {'id': site_id, 'baseURL': base_url, 'baseDocURL': ''})
            
            # Extract site number from baseURL (assuming the format like .../lab-337/123/)
            site_num = None
            if base_url:
                match = re.search(r'/lab-337/(\d+)/?', base_url)
                if match:
                    site_num = match.group(1)
                    numeric_site_num = int(site_num)
                    
                    # Only process sites within the specified range
                    if (start_site is None or end_site is None or 
                        (numeric_site_num >= start_site and numeric_site_num < end_site)):
                        
                        results["sites_processed"] += 1
                        print(f"Processing site {site_num} (ID: {site_id})")
                        
                        # Try to find the Google Drive folder and document
                        try:
                            # Get the site configuration to find the Google Drive folder
                            config_url = f"https://spacecat.experiencecloud.live/api/v1/sites/{site_id}"
                            config_response = requests.get(config_url, headers=headers)
                            
                            if config_response.status_code == 200:
                                site_config = config_response.json()
                                
                                # Extract Google Drive folder URL from hlxConfig
                                hlx_config = site_config.get('hlxConfig', {})
                                content_config = hlx_config.get('content', {})
                                source_config = content_config.get('source', {})
                                
                                if source_config.get('type') == 'drive.google':
                                    folder_url = source_config.get('url')
                                    
                                    if folder_url:
                                        # Extract folder ID from the URL
                                        folder_id_match = re.search(r'folders/([a-zA-Z0-9_-]+)', folder_url)
                                        if folder_id_match:
                                            folder_id = folder_id_match.group(1)
                                            
                                            # Now find the "index" document in this folder
                                            # Use the doc_cloner to find the document in the Google Drive folder
                                            try:
                                                # Check if the doc_cloner has a drive_service (Google Drive API initialized)
                                                if doc_cloner.drive_service:
                                                    # Query for a document named "index" or "index.docx" or similar in the folder
                                                    query = f"name contains 'index' and '{folder_id}' in parents and mimeType contains 'document' and trashed = false"
                                                    response = doc_cloner.drive_service.files().list(
                                                        q=query,
                                                        spaces='drive',
                                                        fields='files(id, name, webViewLink)',
                                                        pageToken=None
                                                    ).execute()
                                                    
                                                    # Get the first matching document
                                                    files = response.get('files', [])
                                                    if files:
                                                        # Use the actual document link
                                                        doc_id = files[0].get('id')
                                                        entry['baseDocURL'] = f"https://docs.google.com/document/d/{doc_id}/edit"
                                                        print(f"  Found index document for site {site_id}: {files[0].get('name')}")
                                                    else:
                                                        # Fallback: Construct expected URL for new document
                                                        entry['baseDocURL'] = f"https://docs.google.com/document/create?folder={folder_id}&name=index"
                                                        print(f"  No index document found for site {site_id}, providing creation URL")
                                                else:
                                                    # If Google Drive API not initialized, construct a placeholder URL
                                                    entry['baseDocURL'] = f"https://drive.google.com/drive/folders/{folder_id}"
                                                    print(f"  Drive API not available, providing folder URL for site {site_id}")
                                                
                                                results["sites_with_doc_url"] += 1
                                            except Exception as doc_e:
                                                print(f"  Error finding index document in folder {folder_id}: {str(doc_e)}")
                                                # Fallback to folder URL
                                                entry['baseDocURL'] = f"https://drive.google.com/drive/folders/{folder_id}"
                        except Exception as e:
                            print(f"Error processing site {site_id}: {str(e)}")
                            results["errors"].append(f"Error for site {site_id}: {str(e)}")
            
            # Add the entry to our list
            updated_entries.append(entry)
        
        # Step 3: Write all entries to the CSV file
        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['id', 'baseURL', 'baseDocURL']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for entry in updated_entries:
                writer.writerow(entry)
        
        print(f"CSV file updated successfully: {output_file}")
        print(f"Total sites: {results['total_sites']}")
        print(f"Sites processed for baseDocURL: {results['sites_processed']}")
        print(f"Sites with document URLs: {results['sites_with_doc_url']}")
        
        return results
    
    except Exception as e:
        print(f"Error updating sites CSV: {str(e)}")
        results["success"] = False
        results["errors"].append(str(e))
        return results

def main(start_num=2, end_num=4):
    """
    Main function to process sites
    
    Args:
        start_num (int): The starting site number (default: 2)
        end_num (int): The ending site number (default: 4)
    """
    print(f"Processing sites from {start_num:03d} to {end_num-1:03d}...")
    
    # Loop through site numbers from start_num to end_num-1 
    # In production, this would typically be a larger range like 000 to 200
    for i in range(start_num, end_num):
        # Format the number with leading zeros to ensure 3-digit format
        site_num = f"{i:03d}"
        base_url = f"https://main--wknd-summit2025--adobe.aem.live/lab-337/{site_num}/"
        
        print(f"Processing site L337-{site_num}...")
        
        # Check if the site already exists
        if check_site_exists(base_url):
            print(f"Skipping site L337-{site_num} as it already exists")
            
            # Get the site ID for existing site
            base64_url = base64.b64encode(base_url.encode()).decode()
            check_url = f"https://spacecat.experiencecloud.live/api/v1/sites/by-base-url/{base64_url}"
            response = requests.get(check_url, headers=headers)
            
            if response.status_code == 200:
                site_data = response.json()
                site_id = site_data.get('id')
                
                # Add Google Drive configuration if needed
                if site_id:
                    config_result = get_or_create_config(site_id, site_num)
                    print(f"Config result: {config_result}")
                else:
                    print("Failed to get site ID for existing site.")
            else:
                print(f"Failed to get site ID for existing site. Status code: {response.status_code}")
            
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
                
                # Get the site ID from the response
                site_data = response.json()
                site_id = site_data.get('id')
                
                # Add Google Drive configuration
                if site_id:
                    config_result = get_or_create_config(site_id, site_num)
                    print(f"Config result: {config_result}")
                else:
                    print("Failed to get site ID from creation response.")
            else:
                print(f"Failed to create site L337-{site_num}")
        
        except Exception as e:
            print(f"Error creating site L337-{site_num}: {e}")
        
        print("")
        
        # Add a small delay between requests to avoid overwhelming the API
        time.sleep(1)
    
    print("All sites processed!")

# If this script is run directly, run the main function and test function
if __name__ == "__main__":
    # Create argument parser
    parser = argparse.ArgumentParser(
        description='''Create sites and synchronize Google Drive folders.
        
Examples:
  # Create sites and configure them with Google Drive folders
  uv run create_sites.py --start 2 --end 4
  
  # Only synchronize Google Drive folders (no site creation)
  uv run create_sites.py --skip-sites --sync-start 0 --sync-end 50
  
  # Sync specific files to all folders
  uv run create_sites.py --skip-sites --sync-file "https://docs.google.com/document/d/18qZz0QZL1D69lvQP2eFL5q_hbEHKxJx1TAQBCmSyUCk/edit" --sync-file "https://docs.google.com/document/d/1JsI492epCL2b8AAACXUENxDebAABoBJa79wt53iz2-E/edit"
  
  # Override existing files when syncing
  uv run create_sites.py --skip-sites --sync-start 0 --sync-end 1 --sync-file "https://docs.google.com/document/d/18qZz0QZL1D69lvQP2eFL5q_hbEHKxJx1TAQBCmSyUCk/edit" --override
  
  # Save sync report to a file
  uv run create_sites.py --skip-sites --report sync_results.json

  # Skip site creation and sync
  uv run create_sites.py --skip-sites --skip-sync
  
  # Sync opportunities to sites (this will delete existing opportunities first)
  uv run create_sites.py --skip-sites --skip-sync --sync-oppties
  
  # Sync opportunities to specific site range
  uv run create_sites.py --skip-sites --skip-sync --sync-oppties --sync-start 10 --sync-end 20

  # Main script with all options needed for lab
  uv run create_sites.py --sync-oppties --sync-file "https://docs.google.com/document/d/18qZz0QZL1D69lvQP2eFL5q_hbEHKxJx1TAQBCmSyUCk/edit" --sync-file "https://docs.google.com/document/d/1JsI492epCL2b8AAACXUENxDebAABoBJa79wt53iz2-E/edit" --override --start 1 --end 2 --sync-start 1 --sync-end 2
  
  # Generate a CSV file with site information including Google Drive document URLs
  uv run create_sites.py --skip-sites --skip-sync --start 0 --end 1 --update-sites-csv sites.csv
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Site creation arguments
    parser.add_argument('--start', type=int, default=2, help='Starting site number (default: 2)')
    parser.add_argument('--end', type=int, default=4, help='Ending site number, exclusive (default: 4)')
    parser.add_argument('--skip-sites', action='store_true', help='Skip site creation and configuration')
    
    # Google Drive synchronization arguments
    parser.add_argument('--sync-start', type=int, default=0, help='Starting folder number for GDrive sync (default: 0)')
    parser.add_argument('--sync-end', type=int, default=200, help='Ending folder number for GDrive sync, exclusive (default: 200)')
    parser.add_argument('--skip-sync', action='store_true', help='Skip Google Drive folder synchronization')
    parser.add_argument('--report', type=str, help='Save sync results to the specified JSON file')
    parser.add_argument('--sync-file', action='append', help='Google Doc URL to sync to each folder. Can be specified multiple times for multiple files')
    parser.add_argument('--override', action='store_true', help='When syncing files, override any existing files with the same name (default: False)')
    
    # Opportunity synchronization arguments
    parser.add_argument('--sync-oppties', action='store_true', help='Synchronize opportunities to sites')
    parser.add_argument('--oppties-report', type=str, help='Save opportunity sync results to the specified JSON file')
    
    # CSV generation arguments
    parser.add_argument('--update-sites-csv', type=str, help='Generate a CSV file with site information (ID, baseURL, baseDocURL)')
    
    args = parser.parse_args()
    
    # Process sites if not skipped
    if not args.skip_sites:
        main(args.start, args.end)
    
    # Run the Google Drive synchronization if not skipped
    if not args.skip_sync:
        sync_gdrive(
            start_folder=args.sync_start, 
            end_folder=args.sync_end, 
            report_path=args.report,
            files_to_sync=args.sync_file,
            files_override=args.override
        ) 
    
    # Run opportunity synchronization if requested
    if args.sync_oppties:
        sync_opportunities(
            start_site=args.sync_start,
            end_site=args.sync_end,
            token=token,
            report_path=args.oppties_report or args.report
        )
        
    # Generate sites CSV if requested
    if args.update_sites_csv:
        update_sites_csv(
            output_file=args.update_sites_csv,
            start_site=args.sync_start,
            end_site=args.sync_end
        ) 