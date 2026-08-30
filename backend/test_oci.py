# pyrefly: ignore [missing-import]
import oci


print("=" * 60)
print("GSVAI - OCI AUTHENTICATION TEST")
print("=" * 60)

print("\nLoading OCI configuration...")

try:
    # Load OCI configuration from:
    # C:\Users\<username>\.oci\config
    config = oci.config.from_file()

    print("OCI configuration loaded successfully.")

    print(f"Region: {config['region']}")
    print(f"User: {config['user'][:25]}...")

    print("\nConnecting to OCI Identity service...")

    # Create OCI Identity client
    identity_client = oci.identity.IdentityClient(config)

    # Get current OCI user
    user = identity_client.get_user(
        config["user"]
    ).data

    print("\n" + "=" * 60)
    print("OCI AUTHENTICATION SUCCESSFUL")
    print("=" * 60)

    print(f"User Name : {user.name}")
    print(f"User OCID : {user.id}")
    print(f"Region    : {config['region']}")

    print("=" * 60)

except Exception as e:

    print("\n" + "=" * 60)
    print("OCI AUTHENTICATION FAILED")
    print("=" * 60)

    print(f"\nError: {e}")

    print("\nPlease check:")
    print("1. C:\\Users\\dbalounge\\.oci\\config exists")
    print("2. oci_api_key.pem exists")
    print("3. key_file path in config is correct")
    print("4. OCI API key was added successfully")
    print("5. OCI SDK is installed")

    print("=" * 60)