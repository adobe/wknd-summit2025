#!/usr/bin/env python3

import os
import time
import requests
import sys
import base64
import argparse

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
        
        if source_config.get('type') == 'drive.google':
            print(f"Site already has Google Drive configuration: {source_config.get('url')}")
            return {
                "success": True,
                "message": "Google Drive configuration already exists",
                "config": source_config
            }
        
        # 3. Get or create the folder for the site number (always with 3 digits and leading zeros)
        folder_id = doc_cloner.get_or_create_folder_id_by_name(site_num)
        if not folder_id:
            return {
                "success": False,
                "error": f"Could not find or create Google Drive folder for site number: {site_num}"
            }
        
        # 4. Create the updated configuration
        new_hlx_config = {
            "hlxConfig": {
                "content": {
                    "source": {
                        "type": "drive.google",
                        "url": f"https://drive.google.com/drive/u/0/folders/{folder_id}"
                    }
                }
            }
        }
        
        # 5. Update the site configuration with PATCH request
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

  # skip site creation and sync
  uv run create_sites.py --skip-sites --skip-sync
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