# Summit Lab Helpers

This directory contains helper scripts for the AEM Sites Summit Lab.

## Scripts Overview

- `clone_oppt.py` - Main class for interacting with AEM Sites Optimizer Backoffice API
- `clone_oppt_file.py` - Google Drive integration for cloning documents to target folders
- `extract_urls.sh` - Shell script for extracting URLs from documents

## Setup and Dependencies

This project uses the UV package manager for Python dependencies. The required packages are specified in `pyproject.toml`.

To install dependencies:

```bash
cd scripts/summit-lab-helpers
uv sync
```

## Google Drive Integration

The `clone_oppt_file.py` script requires Google Drive API access to clone documents. Follow these steps to set up a Google Service Account:

### Creating a Google Service Account

#### Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown menu at the top of the page
3. Click "New Project"
4. Name your project "AEM Sites Agent" (or similar)
5. Click "Create"
6. Wait for the project to be created and select it

#### Step 2: Enable the Google Drive API

1. In your new project, navigate to "APIs & Services" > "Library" from the left navigation menu
2. Search for "Google Drive API"
3. Click on "Google Drive API" in the results
4. Click "Enable"

#### Step 3: Create the Service Account

1. Navigate to "APIs & Services" > "Credentials" from the left navigation menu
2. Click "Create Credentials" at the top of the page
3. Select "Service Account" from the dropdown
4. Fill in the service account details:
   - Name: "AEM Sites Agent"
   - Service account ID: will be auto-generated based on the name (e.g., aem-sites-agent)
   - Description: "Service account for AEM Sites document operations"
5. Click "Create and Continue"
6. On the "Grant this service account access to project" screen:
   - You may skip this step as we will handle permissions separately
   - Click "Continue"
7. On the "Grant users access to this service account" screen:
   - You can add your email if you want to administer this account
   - This step is optional
8. Click "Done"

#### Step 4: Create and Download Service Account Key

1. In the Credentials page, find your newly created service account in the list
2. Click on the service account name to go to its details page
3. Navigate to the "Keys" tab
4. Click "Add Key" > "Create new key"
5. Select "JSON" as the key type
6. Click "Create"
7. A JSON file will be automatically downloaded to your computer - this is your credentials.json file
8. Rename this file to `credentials.json` and place it in the scripts/summit-lab-helpers directory

#### Step 5: Share Target Google Drive Folders with the Service Account

For the service account to access your Google Drive folders, you need to share the folders with the service account email:

1. In the Google Cloud Console, go to "IAM & Admin" > "Service Accounts"
2. Find your service account and note its email address (it should look like `aem-sites-agent@project-id.iam.gserviceaccount.com`)
3. Go to your Google Drive
4. Navigate to the folder with ID "1MF90nBGR1LDyQN7kaDDye91bujdB87cL" (your lab-337 base folder)
5. Right-click on the folder and select "Share"
6. Enter the service account's email address
7. Set the permission to "Editor" to allow creating files
8. Uncheck "Notify people" (optional)
9. Click "Share"

## Usage Examples

```bash
uv run ./clone_oppt.py --token "$ASO_TOKEN" --site-id 13b91559-bbed-41d3-af66-c60660223ed5 --oppt-file ./oppt/opp--broken-internal-links--3_7_2025.json
uv run ./clone_oppt.py --token "$ASO_TOKEN" --site-id 13b91559-bbed-41d3-af66-c60660223ed5 --oppt-file ./oppt/opp--alt-text--3_7_2025.json
uv run ./clone_oppt.py --token "$ASO_TOKEN" --site-id 13b91559-bbed-41d3-af66-c60660223ed5 --oppt-file ./oppt/opp--high-organic-low-ctr--3_7_2025.json
```