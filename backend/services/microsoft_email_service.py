import os
import requests
import msal


# ============================================================
# Microsoft Entra Configuration
# ============================================================

CLIENT_ID = "e7dac2e1-6065-4310-baf9-aef771ca0efe"
TENANT_ID = "53bb4a05-1c2f-4a35-a01a-dd99c32fb558"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

SCOPES = [
    "User.Read",
    "Mail.Read",
    "Mail.Send",
]

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", ".msal_token_cache.bin")


# ============================================================
# Microsoft Email Service
# ============================================================

class MicrosoftEmailService:
    """
    Handles Microsoft 365 mailbox authentication and
    Microsoft Graph email operations with persistent token caching.
    """

    def __init__(self):
        self.client_id = CLIENT_ID
        self.tenant_id = TENANT_ID
        self.authority = AUTHORITY
        self.cache_file = os.path.abspath(CACHE_FILE)
        self.cache = msal.SerializableTokenCache()

        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    self.cache.deserialize(f.read())
            except Exception as e:
                print(f"[MicrosoftEmailService] Warning: Could not read token cache: {e}")

        self.app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=self.authority,
            token_cache=self.cache,
        )

        self.access_token = None

    def _save_cache(self):
        """Persist refreshed or newly acquired tokens to disk."""
        if self.cache and self.cache.has_state_changed:
            try:
                with open(self.cache_file, "w") as f:
                    f.write(self.cache.serialize())
            except Exception as e:
                print(f"[MicrosoftEmailService] Warning: Could not save token cache: {e}")

    # ========================================================
    # Authentication
    # ========================================================

    def authenticate(self, allow_interactive: bool = True):
        """
        Authenticate the Microsoft 365 user.
        First tries silent token retrieval from cache; if needed, runs interactive login.
        """
        accounts = self.app.get_accounts()

        if accounts:
            result = self.app.acquire_token_silent(
                SCOPES,
                account=accounts[0],
            )

            if result and "access_token" in result:
                self.access_token = result["access_token"]
                self._save_cache()
                return self.access_token

        if not allow_interactive:
            raise RuntimeError(
                "Microsoft interactive authentication required. Please sign in via the browser."
            )

        print()
        print("Opening Microsoft login...")
        print()

        result = self.app.acquire_token_interactive(
            scopes=SCOPES,
        )

        if "access_token" not in result:
            error = result.get(
                "error_description",
                "Unknown authentication error",
            )
            raise RuntimeError(
                f"Microsoft authentication failed: {error}"
            )

        self.access_token = result["access_token"]
        self._save_cache()

        print()
        print("Microsoft authentication successful.")
        print()

        return self.access_token

    # ========================================================
    # Connection Health Check
    # ========================================================

    def check_connection(self) -> dict:
        """
        Check Microsoft 365 & Graph connectivity without forcing browser popup if possible.
        """
        mailbox_address = "GauravBhardwaj@GSVAIEnterpriseAI.onmicrosoft.com"
        try:
            accounts = self.app.get_accounts()
            if accounts:
                token = self.authenticate(allow_interactive=False)
                if token:
                    user = self.get_current_user()
                    email = user.get("mail") or user.get("userPrincipalName") or mailbox_address
                    return {
                        "connected": True,
                        "mailbox": email,
                        "display_name": user.get("displayName") or "Gaurav Bhardwaj",
                        "status": "connected",
                        "message": "Microsoft 365 & Microsoft Graph connected",
                    }
        except Exception as e:
            print(f"[MicrosoftEmailService] check_connection silent test: {e}")

        # If silent token is not currently available, report configured state
        return {
            "connected": True if bool(self.access_token) else False,
            "mailbox": mailbox_address,
            "display_name": "Gaurav Bhardwaj",
            "status": "connected" if bool(self.access_token) else "ready",
            "message": "Microsoft Graph configured for " + mailbox_address,
        }

    # ========================================================
    # Graph Headers
    # ========================================================

    def _headers(self):
        if not self.access_token:
            self.authenticate()

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    # ========================================================
    # Get Current User
    # ========================================================

    def get_current_user(self):
        url = f"{GRAPH_BASE_URL}/me"

        response = requests.get(
            url,
            headers=self._headers(),
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to get Microsoft user: "
                f"{response.status_code} "
                f"{response.text}"
            )

        return response.json()

    # ========================================================
    # Get Inbox Messages
    # ========================================================

    def get_inbox_messages(
        self,
        top: int = 10,
    ):
        """
        Retrieve the latest messages from the Inbox.
        """
        url = f"{GRAPH_BASE_URL}/me/mailFolders/inbox/messages"

        params = {
            "$top": top,
            "$orderby": "receivedDateTime DESC",
            "$select": (
                "id,"
                "subject,"
                "sender,"
                "toRecipients,"
                "ccRecipients,"
                "body,"
                "receivedDateTime,"
                "isRead,"
                "hasAttachments"
            ),
        }

        response = requests.get(
            url,
            headers=self._headers(),
            params=params,
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to read Microsoft inbox: "
                f"{response.status_code} "
                f"{response.text}"
            )

        return response.json().get("value", [])

    # ========================================================
    # Get Unread Inbox Messages
    # ========================================================

    def get_unread_messages(
        self,
        top: int = 10,
    ):
        """
        Retrieve unread messages from the Inbox.
        """
        url = f"{GRAPH_BASE_URL}/me/mailFolders/inbox/messages"

        params = {
            "$filter": "isRead eq false",
            "$top": top,
            "$orderby": "receivedDateTime DESC",
            "$select": (
                "id,"
                "subject,"
                "sender,"
                "toRecipients,"
                "ccRecipients,"
                "body,"
                "receivedDateTime,"
                "isRead,"
                "hasAttachments"
            ),
        }

        response = requests.get(
            url,
            headers=self._headers(),
            params=params,
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to read unread messages: "
                f"{response.status_code} "
                f"{response.text}"
            )

        return response.json().get("value", [])

    # ========================================================
    # Mark Email as Read
    # ========================================================

    def mark_as_read(
        self,
        message_id: str,
    ):
        """
        Mark a Microsoft 365 email as read.
        """
        url = (
            f"{GRAPH_BASE_URL}"
            f"/me/messages/{message_id}"
        )

        payload = {
            "isRead": True,
        }

        response = requests.patch(
            url,
            headers=self._headers(),
            json=payload,
            timeout=30,
        )

        if response.status_code not in (200, 202):
            raise RuntimeError(
                f"Failed to mark email as read: "
                f"{response.status_code} "
                f"{response.text}"
            )

        return True

    # ========================================================
    # Reply to Email
    # ========================================================

    def reply_to_email(
        self,
        message_id: str,
        reply_text: str,
    ):
        """
        Reply to the original email.
        This preserves the email conversation/thread.
        """
        url = (
            f"{GRAPH_BASE_URL}"
            f"/me/messages/{message_id}/reply"
        )

        payload = {
            "message": {
                "body": {
                    "contentType": "Text",
                    "content": reply_text,
                }
            }
        }

        response = requests.post(
            url,
            headers=self._headers(),
            json=payload,
            timeout=30,
        )

        if response.status_code not in (200, 202):
            raise RuntimeError(
                f"Failed to reply to email: "
                f"{response.status_code} "
                f"{response.text}"
            )

        return True