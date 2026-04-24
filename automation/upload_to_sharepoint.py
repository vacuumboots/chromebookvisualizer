#!/usr/bin/env python3
import sys
import os
from msal import ConfidentialClientApplication
import requests

# Automatically load environment variables from automation/.env if present
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass  # dotenv is optional if running with env vars already set

# Configuration — credentials loaded from environment variables
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SHAREPOINT_HOSTNAME = os.getenv("SHAREPOINT_HOSTNAME", "fsd365.sharepoint.com")
SITE_PATH = os.getenv("SITE_PATH", "/TechnologyServices")  # e.g. "/TechnologyServices" or site name
LIBRARY_NAME = os.getenv("LIBRARY_NAME", "Documents")  # Document library name
FOLDER_PATH = os.getenv("FOLDER_PATH", "/chromebook reports")  # folder within library, leading slash optional

# Validate required credentials
if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
    print("ERROR: Missing required environment variables:")
    print("  AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET")
    print("Set them in the environment or in automation/.env file")
    sys.exit(1)

def get_access_token():
    """Get access token using client credentials (Graph API scope)"""
    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=CLIENT_SECRET
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Failed to get token: {result.get('error_description')}")

def get_site_id(access_token):
    """Get SharePoint site ID by hostname and path"""
    hostname = SHAREPOINT_HOSTNAME.replace("https://", "").replace("http://", "").rstrip("/")
    # Site path should be like "/TechnologyServices" or site name
    site_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{SITE_PATH.lstrip('/')}"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(site_url, headers=headers)
    if resp.status_code == 200:
        return resp.json()["id"]
    else:
        raise Exception(f"Failed to get site ID: {resp.status_code} - {resp.text}")

def get_drive_id(access_token, site_id):
    """Get document library (drive) ID by name"""
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        drives = resp.json().get("value", [])
        for drive in drives:
            if drive["name"].lower() == LIBRARY_NAME.lower():
                return drive["id"]
        raise Exception(f"Drive '{LIBRARY_NAME}' not found. Available: {[d['name'] for d in drives]}")
    else:
        raise Exception(f"Failed to list drives: {resp.status_code} - {resp.text}")

def upload_file_to_sharepoint(local_path, remote_filename=None):
    """Upload a file to SharePoint using Microsoft Graph API"""
    if remote_filename is None:
        remote_filename = os.path.basename(local_path)

    access_token = get_access_token()

    # Step 1: Get the site ID
    site_id = get_site_id(access_token)

    # Step 2: Get the drive (document library) ID
    drive_id = get_drive_id(access_token, site_id)

    # Step 3: Build the upload URL
    # Folder path: strip leading/trailing slashes, URL-encode
    folder = FOLDER_PATH.strip("/")
    if folder:
        item_path = f"{folder}/{remote_filename}"
    else:
        item_path = remote_filename

    upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{item_path}:/content"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream"
    }

    with open(local_path, "rb") as f:
        content = f.read()

    response = requests.put(upload_url, headers=headers, data=content)
    if response.status_code in (200, 201):
        print(f"Successfully uploaded to SharePoint: {item_path}")
        return True
    else:
        print(f"Upload failed: {response.status_code} - {response.text}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: upload_to_sharepoint.py <file_path> [remote_filename]")
        sys.exit(1)

    file_path = sys.argv[1]
    remote_name = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.isfile(file_path):
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    try:
        upload_file_to_sharepoint(file_path, remote_name)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
