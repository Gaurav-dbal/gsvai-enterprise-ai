import os
import oci
from dotenv import load_dotenv


load_dotenv()


def get_oci_config():
    """
    Return OCI authentication configuration.

    Local development:
        Uses ~/.oci/config.

    Production / OCI Compute:
        Uses Instance Principal authentication with
        a minimal OCI SDK configuration containing the region.
    """

    environment = os.getenv("GSVAI_ENV", "development").lower()

    if environment == "production":
        print("OCI authentication: Instance Principal")

        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()

        compartment_id = os.getenv("OCI_COMPARTMENT_ID")
        region = os.getenv("OCI_REGION")

        if not compartment_id:
            raise ValueError(
                "OCI_COMPARTMENT_ID must be configured in production."
            )

        if not region:
            raise ValueError(
                "OCI_REGION must be configured in production."
            )

        config = {
            "region": region
        }

        return config, signer, compartment_id

    print("OCI authentication: OCI config file")

    config = oci.config.from_file()

    compartment_id = config["tenancy"]

    return config, None, compartment_id
