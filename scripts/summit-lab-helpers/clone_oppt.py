#!/usr/bin/env python3

import json
import requests
import logging

class AemSitesOptimizerBackoffice:
    """
    Class for interacting with AEM Sites Optimizer Backoffice API
    """
    
    def __init__(self, base_url="https://spacecat.experiencecloud.live/api/v1", token=None):
        """
        Initialize the AEM Sites Optimizer Backoffice client
        
        Args:
            base_url (str): Base URL for the API
            token (str): IMS Token for authentication
        """
        self.base_url = base_url
        self.token = token
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.DEBUG, 
                           format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    def clone_google_doc(self, google_doc_url, site_id):
        """
        Clone a Google Doc for a specific site
        
        Args:
            google_doc_url (str): The URL of the Google Doc to clone
            site_id (str): The ID of the site
            
        Returns:
            str: A message indicating the Google Doc URL and site baseURL
        """
        self.logger.info(f"Cloning Google Doc: {google_doc_url} into site {site_id}")
        
        # Fetch the site data to get the baseURL
        sites_url = "https://main--wknd-summit2025--adobe.aem.live/lab-337/lab-337-sites.json"
        self.logger.info(f"Fetching site data from: {sites_url}")
        
        try:
            response = requests.get(sites_url)
            response.raise_for_status()  # Raise an exception for non-200 responses
            
            sites_data = response.json()
            base_url = None
            
            # Find the site with matching ID
            for site in sites_data.get("data", []):
                if site.get("id") == site_id:
                    base_url = site.get("baseURL")
                    break
            
            if base_url:
                self.logger.info(f"Found baseURL for site {site_id}: {base_url}")
            else:
                self.logger.warning(f"No baseURL found for site {site_id}")
                
            # This would be implemented to actually clone the Google Doc
            return f"Would clone Google Doc at {google_doc_url} into site with baseURL: {base_url}"
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching site data: {str(e)}")
            return f"Error: Could not fetch site data - {str(e)}"
    
    def clone_opportunity(self, site_id, oppt_file_path):
        """
        Clone an opportunity by reading from a JSON file and POSTing to the opportunities endpoint,
        then add suggestions from the same file to the created opportunity
        
        Args:
            site_id (str): The ID of the site
            oppt_file_path (str): Path to the opportunity JSON file
            
        Returns:
            dict: The response containing both opportunity and suggestions responses
        """
        result = {
            "opportunity": None,
            "suggestions": None,
            "google_docs": []
        }
        
        try:
            # Read the opportunity JSON file (only once)
            with open(oppt_file_path, 'r') as file:
                oppt_data = json.load(file)
            
            # Extract the opportunity data
            if 'opportunity' not in oppt_data:
                raise ValueError(f"No 'opportunity' key found in {oppt_file_path}")
            
            opportunity = oppt_data['opportunity']
            
            # Create the payload based on the opportunity data
            payload = {
                "auditId": opportunity.get("auditId", ""),
                "runbook": opportunity.get("runbook", ""),
                "type": opportunity.get("type", ""),
                "origin": opportunity.get("origin", "AUTOMATION"),
                "title": opportunity.get("title", ""),
                "description": opportunity.get("description", ""),
                "tags": opportunity.get("tags", []),
                "data": opportunity.get("data", {}),
            }
            
            # Only add guidance if it exists in the opportunity
            if "guidance" in opportunity:
                payload["guidance"] = opportunity.get("guidance")
            
            # Prepare headers with token if provided
            headers = {}
            if self.token:
                headers['Authorization'] = f"Bearer {self.token}"
            
            # 1. First POST request - Create opportunity
            opp_url = f"{self.base_url}/sites/{site_id}/opportunities"
            self.logger.info(f"Cloning opportunity to site {site_id}")
            self.logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            
            opportunity_response = requests.post(opp_url, json=payload, headers=headers)
            opportunity_response.raise_for_status()
            
            result["opportunity"] = opportunity_response.json()
            self.logger.info(f"Successfully cloned opportunity. Response: {opportunity_response.status_code}")
            
            # Extract the opportunity ID from the response
            opportunity_id = result["opportunity"].get('id')
            
            if opportunity_id and 'suggestions' in oppt_data:
                # 2. Second POST request - Add suggestions
                suggestions = oppt_data['suggestions']
                
                # Check for Google Doc URLs in suggestions and clone them if needed
                for suggestion in suggestions:
                    if "data" in suggestion and "variations" in suggestion["data"]:
                        for variation in suggestion["data"]["variations"]:
                            variation_edit_url = variation.get("variationEditPageUrl")
                            if variation_edit_url and variation_edit_url.startswith("https://docs.google.com"):
                                # Call the placeholder method for cloning Google Doc
                                doc_result = self.clone_google_doc(google_doc_url=variation_edit_url, site_id=site_id)
                                result["google_docs"].append({
                                    "url": variation_edit_url,
                                    "result": doc_result
                                })
                
                # Update opportunityId in each suggestion
                for suggestion in suggestions:
                    suggestion["opportunityId"] = opportunity_id
                
                suggestions_url = f"{self.base_url}/sites/{site_id}/opportunities/{opportunity_id}/suggestions"
                self.logger.info(f"Adding {len(suggestions)} suggestions to opportunity {opportunity_id}")
                self.logger.debug(f"Suggestions payload: {json.dumps(suggestions, indent=2)}")
                
                suggestions_response = requests.post(suggestions_url, json=suggestions, headers=headers)
                suggestions_response.raise_for_status()
                
                result["suggestions"] = suggestions_response.json()
                self.logger.info(f"Successfully added suggestions. Response: {suggestions_response.status_code}")
            elif not opportunity_id:
                self.logger.warning("No opportunity ID found in response. Suggestions were not added.")
            elif 'suggestions' not in oppt_data:
                self.logger.warning("No suggestions found in the opportunity file.")
            
            return result
            
        except FileNotFoundError:
            self.logger.error(f"Opportunity file not found: {oppt_file_path}")
            raise
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in file: {oppt_file_path}")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            raise

if __name__ == "__main__":
    import argparse
    # clone_oppt.py --token 1234567890 --site-id 9f466aa2-e734-4714-8399-c173bd96347e --oppt-file ./oppt/opp--alt-text--3_7_2025.json
    parser = argparse.ArgumentParser(description='Clone an AEM Sites Optimizer opportunity')
    parser.add_argument('--site-id', required=True, help='The site ID')
    parser.add_argument('--oppt-file', required=True, help='Path to the opportunity JSON file')
    parser.add_argument('--token', required=True, help='IMS Token from https://experience.adobe.com/?organizationId=d488fc90-d009-412c-82a1-70b338b1869c#/@sitesinternal/sites-optimizer/sites/9d5ab4bc-6521-40b9-9d47-1e5d0a616fe4/home')
    
    args = parser.parse_args()
    
    backoffice = AemSitesOptimizerBackoffice(token=args.token)
    
    # Clone the opportunity and add suggestions in one method call
    result = backoffice.clone_opportunity(args.site_id, args.oppt_file)
    
    # Print results
    print("\nOpportunity created:")
    print(json.dumps(result["opportunity"], indent=2))
    
    if result["suggestions"]:
        print("\nSuggestions added:")
        print(json.dumps(result["suggestions"], indent=2))
    else:
        print("\nNo suggestions were added.")
        
    if result["google_docs"]:
        print("\nGoogle Docs found and processed:")
        for doc in result["google_docs"]:
            print(f"- {doc['url']}")
            print(f"  {doc['result']}")
