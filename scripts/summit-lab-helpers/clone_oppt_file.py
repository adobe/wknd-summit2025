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
    
    def _get_file_name(self, doc_id):
        """
        Get the original filename of a Google Doc
        
        Args:
            doc_id (str): Google Doc ID
            
        Returns:
            str: Original filename or None if not found
        """
        if not self.drive_service:
            self.logger.info(f"Placeholder: Would get filename for doc ID {doc_id}")
            return f"Placeholder Document {doc_id}"
            
        try:
            file_metadata = self.drive_service.files().get(
                fileId=doc_id, 
                fields='name'
            ).execute()
            file_name = file_metadata.get('name')
            self.logger.info(f"Original filename for {doc_id}: {file_name}")
            return file_name
        except Exception as e:
            self.logger.error(f"Error getting filename: {str(e)}")
            return None
    
    def _file_exists_in_folder(self, folder_id, file_name):
        """
        Check if a file with the given name exists in the specified folder
        
        Args:
            folder_id (str): Folder ID to check
            file_name (str): Filename to look for
            
        Returns:
            str: File ID if exists, None otherwise
        """
        if not self.drive_service:
            self.logger.info(f"Placeholder: Would check if '{file_name}' exists in folder {folder_id}")
            return None
            
        try:
            query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
            response = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageToken=None
            ).execute()
            
            files = response.get('files', [])
            if files:
                self.logger.info(f"File '{file_name}' already exists in folder {folder_id} with ID {files[0].get('id')}")
                return files[0].get('id')
            else:
                self.logger.info(f"File '{file_name}' does not exist in folder {folder_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error checking if file exists: {str(e)}")
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
    
    def _get_or_create_folder_id_by_name(self, folder_name):
        """
        Get or create a Google Drive folder by name within the lab-337 folder
        
        Args:
            folder_name (str): Folder name to find or create
            
        Returns:
            str: Folder ID of the found or created folder, None if failed
        """
        if not self.drive_service:
            self.logger.info(f"Placeholder: Would find or create folder '{folder_name}'")
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
            
            # Check if the folder already exists
            files = response.get('files', [])
            if files:
                folder_id = files[0].get('id')
                self.logger.info(f"Found existing folder: {folder_name} ({folder_id})")
                return folder_id
            
            # If folder does not exist, create it
            self.logger.info(f"Folder '{folder_name}' not found. Creating new folder.")
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.base_folder_id]
            }
            
            created_folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            new_folder_id = created_folder.get('id')
            self.logger.info(f"Created new folder: {folder_name} ({new_folder_id})")
            return new_folder_id
            
        except Exception as e:
            self.logger.error(f"Error finding or creating folder: {str(e)}")
            return None
    
    def clone_doc_to_folder(self, doc_id, target_folder_id, new_title=None, override=False):
        """
        Clone a Google Doc to a target folder
        
        Args:
            doc_id (str): Google Doc ID to clone
            target_folder_id (str): Target folder ID
            new_title (str, optional): New title for the cloned document
            override (bool, optional): Whether to override existing files with the same name
            
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
            
            # Check if a file with the same name already exists in the target folder
            existing_file_id = self._file_exists_in_folder(target_folder_id, new_title)
            
            if existing_file_id:
                if override:
                    # Delete the existing file if override is True
                    self.logger.info(f"Deleting existing file '{new_title}' with ID {existing_file_id}")
                    self.drive_service.files().delete(fileId=existing_file_id).execute()
                else:
                    # If override is False, return the existing file ID
                    self.logger.info(f"File '{new_title}' already exists and override=False. Returning existing file ID.")
                    return existing_file_id
            
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
    
    def clone_google_doc(self, google_doc_url, base_url, override=False):
        """
        Main method to clone a Google Doc to the target folder specified in the base URL
        
        Args:
            google_doc_url (str): URL of the Google Doc to clone
            base_url (str): Base URL from sites JSON containing the target folder
            override (bool, optional): Whether to override existing files with the same name
            
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
        
        # Get the original filename of the document
        original_filename = self._get_file_name(doc_id)
        if not original_filename:
            return {
                "success": False,
                "error": f"Could not get filename for document: {doc_id}"
            }
        
        # Extract target folder from base URL
        target_folder = self._extract_target_folder_from_base_url(base_url)
        if not target_folder:
            return {
                "success": False,
                "error": f"Could not extract target folder from base URL: {base_url} or it's an _adobe_presenters folder"
            }
        
        # Find or create the folder ID for the target folder
        target_folder_id = self._get_or_create_folder_id_by_name(target_folder)
        if not target_folder_id:
            return {
                "success": False,
                "error": f"Could not find or create folder ID for target folder: {target_folder}"
            }
        
        # Clone the document to the target folder
        cloned_doc_id = self.clone_doc_to_folder(doc_id, target_folder_id, original_filename, override)
        if not cloned_doc_id:
            return {
                "success": False,
                "error": f"Failed to clone document {doc_id} to folder {target_folder_id}"
            }
        
        return {
            "success": True,
            "original_doc_id": doc_id,
            "original_filename": original_filename,
            "target_folder": target_folder,
            "target_folder_id": target_folder_id,
            "cloned_doc_id": cloned_doc_id,
            "doc_url": f"https://docs.google.com/document/d/{cloned_doc_id}/edit"
        }


def main():
    """Example usage of the GoogleDocCloner class"""
    # Example URLs
    google_doc_url = "https://docs.google.com/document/d/1WcaYMcb-jtkrWhIgTKFDa55F8l3P6HxRbiPiuqqrQQ0/edit?tab=t.0"
    base_url = "https://main--wknd-summit2025--adobe.aem.live/lab-337/105/"
    
    # Create an instance of GoogleDocCloner
    cloner = GoogleDocCloner()
    
    # Clone the Google Doc
    result = cloner.clone_google_doc(google_doc_url, base_url, override=False)
    
    # Print the result
    if result["success"]:
        print(f"Successfully cloned document '{result['original_filename']}' to folder {result['target_folder']}")
        print(f"New document URL: {result['doc_url']}")
    else:
        print(f"Failed to clone document: {result.get('error')}")


if __name__ == "__main__":
    main() 