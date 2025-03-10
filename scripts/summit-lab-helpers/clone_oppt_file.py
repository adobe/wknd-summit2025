#!/usr/bin/env python3

import os
import json
import logging
import requests
from googleapiclient.discovery import build
from google.oauth2 import service_account
from urllib.parse import urlparse, parse_qs

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GoogleDocCloner:
    """
    Class for cloning Google Docs to specific target folders
    """
    
    def __init__(self, credentials_path="credentials.json"):
        """
        Initialize the Google Doc Cloner
        
        Args:
            credentials_path (str): Path to the Google API service account credentials file
        """
        self.logger = logger
        self.credentials_path = credentials_path
        self.drive_service = None
        self.base_folder_id = "1MF90nBGR1LDyQN7kaDDye91bujdB87cL"  # Lab-337 base folder
        
        # Initialize Google Drive API
        try:
            self._initialize_drive_api()
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Drive API: {str(e)}")
    
    def _initialize_drive_api(self):
        """Initialize the Google Drive API service"""
        if os.path.exists(self.credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=['https://www.googleapis.com/auth/drive']
            )
            self.drive_service = build('drive', 'v3', credentials=credentials)
            self.logger.info("Google Drive API initialized successfully")
        else:
            self.logger.warning(f"Credentials file not found at {self.credentials_path}")
            self.logger.info("Using placeholder implementation for demonstration")
    
    def _extract_doc_id_from_url(self, google_doc_url):
        """
        Extract document ID from Google Doc URL
        
        Args:
            google_doc_url (str): Google Doc URL
            
        Returns:
            str: Google Doc ID
        """
        parsed_url = urlparse(google_doc_url)
        
        # Handle different Google Doc URL formats
        if 'docs.google.com' in parsed_url.netloc:
            # Format: https://docs.google.com/document/d/DOC_ID/edit
            path_parts = parsed_url.path.split('/')
            for i, part in enumerate(path_parts):
                if part == 'd' and i + 1 < len(path_parts):
                    return path_parts[i + 1]
        
        # Handle drive.google.com URLs
        elif 'drive.google.com' in parsed_url.netloc:
            # Format: https://drive.google.com/file/d/DOC_ID/view
            if '/file/d/' in parsed_url.path:
                doc_id = parsed_url.path.split('/file/d/')[1].split('/')[0]
                return doc_id
            
            # Format: https://drive.google.com/open?id=DOC_ID
            query_params = parse_qs(parsed_url.query)
            if 'id' in query_params:
                return query_params['id'][0]
        
        self.logger.error(f"Could not extract document ID from URL: {google_doc_url}")
        return None
    
    def _extract_target_folder_from_base_url(self, base_url):
        """
        Extract target folder from base URL
        
        Args:
            base_url (str): Base URL from sites JSON
            
        Returns:
            str: Target folder name
        """
        # Clean up the base_url (remove @ and spaces if present)
        base_url = base_url.replace('@', '').strip()
        
        # Skip _adobe_presenters folders as they're source folders
        if '_adobe_presenters' in base_url:
            self.logger.info(f"Skipping _adobe_presenters folder: {base_url}")
            return None
            
        # Extract the last part of the path which is the target folder
        parsed_url = urlparse(base_url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        # The target folder should be the last element after "lab-337"
        if len(path_parts) > 0:
            target_folder = path_parts[-1] if path_parts[-1] else None
            return target_folder
        
        return None
    
    def _find_folder_id_by_name(self, folder_name):
        """
        Find Google Drive folder ID by name within the lab-337 folder
        
        Args:
            folder_name (str): Folder name to find
            
        Returns:
            str: Folder ID if found, None otherwise
        """
        if not self.drive_service:
            self.logger.info(f"Placeholder: Would find folder ID for '{folder_name}'")
            return f"placeholder-folder-id-{folder_name}"
            
        try:
            # Search for the folder within the lab-337 parent folder
            query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and '{self.base_folder_id}' in parents and trashed = false"
            response = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageToken=None
            ).execute()
            
            for folder in response.get('files', []):
                self.logger.info(f"Found folder: {folder.get('name')} ({folder.get('id')})")
                return folder.get('id')
                
            self.logger.warning(f"No folder found with name '{folder_name}'")
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding folder: {str(e)}")
            return None
    
    def clone_doc_to_folder(self, doc_id, target_folder_id, new_title=None):
        """
        Clone a Google Doc to a target folder
        
        Args:
            doc_id (str): Google Doc ID to clone
            target_folder_id (str): Target folder ID
            new_title (str, optional): New title for the cloned document
            
        Returns:
            str: ID of the cloned document or None if operation failed
        """
        if not self.drive_service:
            self.logger.info(f"Placeholder: Would clone doc {doc_id} to folder {target_folder_id}")
            return f"placeholder-cloned-doc-id-{doc_id}"
            
        try:
            # Get the original file metadata to preserve title if not provided
            if not new_title:
                file_metadata = self.drive_service.files().get(
                    fileId=doc_id, 
                    fields='name'
                ).execute()
                new_title = file_metadata.get('name', f"Copy of document {doc_id}")
            
            # Create a copy in the target folder
            copied_file = self.drive_service.files().copy(
                fileId=doc_id,
                body={
                    'name': new_title,
                    'parents': [target_folder_id]
                }
            ).execute()
            
            cloned_id = copied_file.get('id')
            self.logger.info(f"Successfully cloned document to {new_title} ({cloned_id})")
            return cloned_id
            
        except Exception as e:
            self.logger.error(f"Error cloning document: {str(e)}")
            return None
    
    def clone_google_doc(self, google_doc_url, base_url):
        """
        Main method to clone a Google Doc to the target folder specified in the base URL
        
        Args:
            google_doc_url (str): URL of the Google Doc to clone
            base_url (str): Base URL from sites JSON containing the target folder
            
        Returns:
            dict: Result of the operation with status and details
        """
        self.logger.info(f"Cloning Google Doc from {google_doc_url} to {base_url}")
        
        # Extract document ID from URL
        doc_id = self._extract_doc_id_from_url(google_doc_url)
        if not doc_id:
            return {
                "success": False,
                "error": f"Could not extract document ID from URL: {google_doc_url}"
            }
        
        # Extract target folder from base URL
        target_folder = self._extract_target_folder_from_base_url(base_url)
        if not target_folder:
            return {
                "success": False,
                "error": f"Could not extract target folder from base URL: {base_url} or it's an _adobe_presenters folder"
            }
        
        # Find the folder ID for the target folder
        target_folder_id = self._find_folder_id_by_name(target_folder)
        if not target_folder_id:
            return {
                "success": False,
                "error": f"Could not find folder ID for target folder: {target_folder}"
            }
        
        # Clone the document to the target folder
        cloned_doc_id = self.clone_doc_to_folder(doc_id, target_folder_id)
        if not cloned_doc_id:
            return {
                "success": False,
                "error": f"Failed to clone document {doc_id} to folder {target_folder_id}"
            }
        
        return {
            "success": True,
            "original_doc_id": doc_id,
            "target_folder": target_folder,
            "target_folder_id": target_folder_id,
            "cloned_doc_id": cloned_doc_id,
            "doc_url": f"https://docs.google.com/document/d/{cloned_doc_id}/edit"
        }


def main():
    """Example usage of the GoogleDocCloner class"""
    # Example URLs
    google_doc_url = "https://docs.google.com/document/d/1WcaYMcb-jtkrWhIgTKFDa55F8l3P6HxRbiPiuqqrQQ0/edit?tab=t.0"
    base_url = "https://main--wknd-summit2025--adobe.aem.live/lab-337/000/"
    
    # Create an instance of GoogleDocCloner
    cloner = GoogleDocCloner()
    
    # Clone the Google Doc
    result = cloner.clone_google_doc(google_doc_url, base_url)
    
    # Print the result
    if result["success"]:
        print(f"Successfully cloned document to folder {result['target_folder']}")
        print(f"New document URL: {result['doc_url']}")
    else:
        print(f"Failed to clone document: {result.get('error')}")


if __name__ == "__main__":
    main() 