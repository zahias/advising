# get_refresh_token.py

from google_auth_oauthlib.flow import InstalledAppFlow
import os

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

def main():
    # Ensure you have the 'credentials.json' file in the same directory
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    print(f"Refresh Token: {creds.refresh_token}")

if __name__ == '__main__':
    main()
