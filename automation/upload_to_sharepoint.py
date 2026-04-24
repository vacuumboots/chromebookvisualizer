#!/usr/bin/env python3
import sys
import os
from msal import ConfidentialClientApplication
import requests

# Configuration — credentials loaded from environment variables
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SHAREPOINT_HOSTNAME = os.getenv("SHAREPOINT_HOSTNAME", "fsd365.sharepoint.com")
SITE_PATH = os.getenv("SITE_PATH", "/TechnologyServices")
LIBRARY_NAME = os.getenv("LIBRARY_NAME", "Documents")
FOLDER_PATH = os.getenv("FOLDER_PATH", "/chromebook reports")

# Validate required credentials
if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
    print("ERROR: Missing required environment variables:")
    print("  AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET")
    print("Set them before running, e.g.:")
    print("  export AZURE_TENANT_ID=your-tenant-id")
    print("  export AZURE_CLIENT_ID=your-client-id")
    print("  export AZURE_CLIENT_SECRET=your-client-secret")
    sys.exit(1)

def get_access_token():
    """Get access token using client credentials"""
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

def upload_file_to_sharepoint(local_path, remote_filename=None):
    """Upload a file to SharePoint"""
    if remote_filename is None:
        remote_filename = os.path.basename(local_path)

    access_token = get_access_token()

    # Build SharePoint URL
    site_url = f"https://{SHAREPOINT_HOSTNAME}{SITE_PATH}"
    drive_url = f"{site_url}/_api/web/GetFolderByServerRelativeUrl('{LIBRARY_NAME}{FOLDER_PATH}')/Files/add(url='{remote_filename}',overwrite=true)"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream"
    }

    with open(local_path, "rb") as f:
        content = f.read()

    response = requests.post(drive_url, headers=headers, data=content)
    if response.status_code in (200, 201):
        print(f"Successfully uploaded {remote_filename} to SharePoint")
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

    try:
        upload_file_to_sharepoint(file_path, remote_name)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
