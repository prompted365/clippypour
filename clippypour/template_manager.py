"""
Template Manager module for ClippyPour.

This module provides functionality for saving, loading, and managing form templates and profiles.
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import re
from urllib.parse import urlparse

class TemplateManager:
    """
    Manages form templates and profiles for ClippyPour.
    """
    
    def __init__(self, storage_dir: str = None):
        """
        Initialize the TemplateManager.
        
        Args:
            storage_dir (str, optional): Directory to store templates and profiles.
                If None, defaults to ~/.clippypour/templates
        """
        if storage_dir is None:
            home_dir = os.path.expanduser("~")
            storage_dir = os.path.join(home_dir, ".clippypour", "templates")
        
        self.storage_dir = storage_dir
        self.templates_dir = os.path.join(storage_dir, "templates")
        self.profiles_dir = os.path.join(storage_dir, "profiles")
        
        # Create directories if they don't exist
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.profiles_dir, exist_ok=True)
    
    def save_template(self, template_data: Dict[str, Any], name: str = None) -> str:
        """
        Save a form template.
        
        Args:
            template_data (Dict[str, Any]): Template data to save.
            name (str, optional): Name for the template. If None, generates a name.
            
        Returns:
            str: The template ID (filename without extension).
        """
        # Generate a name if none provided
        if name is None:
            # Try to extract a name from the URL or title
            url = template_data.get("url", "")
            title = template_data.get("title", "")
            
            if url:
                domain = urlparse(url).netloc
                path = urlparse(url).path
                name = f"{domain}{path}".replace("/", "_").strip("_")
            elif title:
                name = re.sub(r'[^\w\s-]', '', title).strip().lower()
                name = re.sub(r'[-\s]+', '-', name)
            else:
                name = f"template_{int(time.time())}"
        
        # Ensure the name is valid as a filename
        name = re.sub(r'[^\w\s-]', '', name).strip().lower()
        name = re.sub(r'[-\s]+', '-', name)
        
        # Add metadata
        template_data["metadata"] = {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "name": name
        }
        
        # Save the template
        template_id = name
        template_path = os.path.join(self.templates_dir, f"{template_id}.json")
        
        # If file exists, add a timestamp to make it unique
        if os.path.exists(template_path):
            template_id = f"{name}_{int(time.time())}"
            template_path = os.path.join(self.templates_dir, f"{template_id}.json")
        
        with open(template_path, "w") as f:
            json.dump(template_data, f, indent=2)
        
        return template_id
    
    def load_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a form template.
        
        Args:
            template_id (str): Template ID (filename without extension).
            
        Returns:
            Optional[Dict[str, Any]]: Template data, or None if not found.
        """
        template_path = os.path.join(self.templates_dir, f"{template_id}.json")
        
        if not os.path.exists(template_path):
            return None
        
        with open(template_path, "r") as f:
            return json.load(f)
    
    def delete_template(self, template_id: str) -> bool:
        """
        Delete a form template.
        
        Args:
            template_id (str): Template ID (filename without extension).
            
        Returns:
            bool: True if deleted, False if not found.
        """
        template_path = os.path.join(self.templates_dir, f"{template_id}.json")
        
        if not os.path.exists(template_path):
            return False
        
        os.remove(template_path)
        return True
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """
        List all available templates.
        
        Returns:
            List[Dict[str, Any]]: List of template metadata.
        """
        templates = []
        
        for filename in os.listdir(self.templates_dir):
            if filename.endswith(".json"):
                template_id = filename[:-5]  # Remove .json extension
                template_path = os.path.join(self.templates_dir, filename)
                
                try:
                    with open(template_path, "r") as f:
                        template_data = json.load(f)
                    
                    # Extract metadata
                    metadata = template_data.get("metadata", {})
                    url = template_data.get("url", "")
                    title = template_data.get("title", "")
                    
                    templates.append({
                        "id": template_id,
                        "name": metadata.get("name", template_id),
                        "created_at": metadata.get("created_at", ""),
                        "updated_at": metadata.get("updated_at", ""),
                        "url": url,
                        "title": title
                    })
                except:
                    # Skip invalid templates
                    continue
        
        # Sort by updated_at (newest first)
        templates.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return templates
    
    def save_profile(self, profile_data: Dict[str, Any], name: str) -> str:
        """
        Save a user profile.
        
        Args:
            profile_data (Dict[str, Any]): Profile data to save.
            name (str): Name for the profile.
            
        Returns:
            str: The profile ID (filename without extension).
        """
        # Ensure the name is valid as a filename
        profile_id = re.sub(r'[^\w\s-]', '', name).strip().lower()
        profile_id = re.sub(r'[-\s]+', '-', profile_id)
        
        # Add metadata
        profile_data["metadata"] = {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "name": name
        }
        
        # Save the profile
        profile_path = os.path.join(self.profiles_dir, f"{profile_id}.json")
        
        with open(profile_path, "w") as f:
            json.dump(profile_data, f, indent=2)
        
        return profile_id
    
    def load_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a user profile.
        
        Args:
            profile_id (str): Profile ID (filename without extension).
            
        Returns:
            Optional[Dict[str, Any]]: Profile data, or None if not found.
        """
        profile_path = os.path.join(self.profiles_dir, f"{profile_id}.json")
        
        if not os.path.exists(profile_path):
            return None
        
        with open(profile_path, "r") as f:
            return json.load(f)
    
    def delete_profile(self, profile_id: str) -> bool:
        """
        Delete a user profile.
        
        Args:
            profile_id (str): Profile ID (filename without extension).
            
        Returns:
            bool: True if deleted, False if not found.
        """
        profile_path = os.path.join(self.profiles_dir, f"{profile_id}.json")
        
        if not os.path.exists(profile_path):
            return False
        
        os.remove(profile_path)
        return True
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """
        List all available profiles.
        
        Returns:
            List[Dict[str, Any]]: List of profile metadata.
        """
        profiles = []
        
        for filename in os.listdir(self.profiles_dir):
            if filename.endswith(".json"):
                profile_id = filename[:-5]  # Remove .json extension
                profile_path = os.path.join(self.profiles_dir, filename)
                
                try:
                    with open(profile_path, "r") as f:
                        profile_data = json.load(f)
                    
                    # Extract metadata
                    metadata = profile_data.get("metadata", {})
                    
                    profiles.append({
                        "id": profile_id,
                        "name": metadata.get("name", profile_id),
                        "created_at": metadata.get("created_at", ""),
                        "updated_at": metadata.get("updated_at", "")
                    })
                except:
                    # Skip invalid profiles
                    continue
        
        # Sort by name
        profiles.sort(key=lambda x: x.get("name", ""))
        
        return profiles
    
    def find_template_for_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Find a template that matches a given URL.
        
        Args:
            url (str): URL to match.
            
        Returns:
            Optional[Dict[str, Any]]: Matching template, or None if not found.
        """
        # Parse the URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path
        
        # List all templates
        templates = self.list_templates()
        
        # First, try to find an exact URL match
        for template_meta in templates:
            template_id = template_meta["id"]
            template = self.load_template(template_id)
            
            if template and template.get("url") == url:
                return template
        
        # Next, try to find a domain + path match
        for template_meta in templates:
            template_id = template_meta["id"]
            template = self.load_template(template_id)
            
            if not template:
                continue
            
            template_url = template.get("url", "")
            if not template_url:
                continue
            
            parsed_template_url = urlparse(template_url)
            template_domain = parsed_template_url.netloc
            template_path = parsed_template_url.path
            
            # Check if domain matches and path is similar
            if template_domain == domain and (
                template_path == path or 
                template_path.startswith(path) or 
                path.startswith(template_path)
            ):
                return template
        
        # Finally, just try to match the domain
        for template_meta in templates:
            template_id = template_meta["id"]
            template = self.load_template(template_id)
            
            if not template:
                continue
            
            template_url = template.get("url", "")
            if not template_url:
                continue
            
            parsed_template_url = urlparse(template_url)
            template_domain = parsed_template_url.netloc
            
            if template_domain == domain:
                return template
        
        return None