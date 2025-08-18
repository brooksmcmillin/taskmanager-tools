import os
import subprocess
import tarfile
import urllib.request
from pathlib import Path

from ..papers.research_paper_util import analyze_paper_with_claude, generate_formatted_filename

RMAPI_URL = (
    "https://github.com/ddvk/rmapi/releases/latest/download/rmapi-linux-amd64.tar.gz"
)


class RMAPI:
    def __init__(self, config_path: str = "./.rmapi"):
        # Make sure the rmapi executable exists
        self.setup()

        # Set the path of the config
        os.environ["RMAPI_CONFIG"] = config_path

    def setup(self) -> None:
        """
        Download and unpack the lastest version of rmapi if needed
        """

        # Check if rmapi is already in the bin directory
        rmapi_path = Path("./bin/rmapi")
        if rmapi_path.exists():
            print("rmapi already exists in current directory")
            return

        # If not, download and unpack it
        print("Downloading rmapi...")
        tarball_path = "rmapi.tar.gz"

        try:
            # Download the tarball
            urllib.request.urlretrieve(RMAPI_URL, tarball_path)
            print(f"Downloaded rmapi to {tarball_path}")

            # Extract the tarball
            print("Extracting rmapi...")
            with tarfile.open(tarball_path, "r:gz") as tar:
                tar.extractall("./bin")
            print("Extracted rmapi successfully")

            # Make rmapi executable
            if rmapi_path.exists():
                os.chmod(rmapi_path, 0o755)
                print("Made rmapi executable")

            # Clean up the tarball
            os.remove(tarball_path)
            print("Cleaned up tarball")

        except Exception as e:
            print(f"Error setting up rmapi: {e}")
            # Clean up partial download if it exists
            if os.path.exists(tarball_path):
                os.remove(tarball_path)
            raise

    def ensure_directory(self, classification: str) -> bool:
        """
        Ensure the directory structure papers/<classification> exists on reMarkable.
        Returns True if successful, False otherwise.

        TODO: Make this function be able to check for any generic directory
        """
        try:
            # First, check if papers directory exists
            result = subprocess.run(
                ["./bin/rmapi", "ls", "/"], capture_output=True, text=True, check=False
            )

            # Create papers directory if it doesn't exist
            if "papers" not in result.stdout:
                print("Creating /papers directory...")
                subprocess.run(
                    ["./bin/rmapi", "mkdir", "/papers"],
                    capture_output=True,
                    text=True,
                    check=True,
                )

            # Check if classification subdirectory exists
            result = subprocess.run(
                ["./bin/rmapi", "ls", "/papers"],
                capture_output=True,
                text=True,
                check=False,
            )

            # Create classification directory if it doesn't exist
            if classification not in result.stdout:
                print(f"Creating /papers/{classification} directory...")
                subprocess.run(
                    ["./bin/rmapi", "mkdir", f"/papers/{classification}"],
                    capture_output=True,
                    text=True,
                    check=True,
                )

            return True

        except subprocess.CalledProcessError as e:
            print(f"Error creating directory structure: {e}")
            return False

    def upload_paper(
        self,
        paper_path: str,
        title: str | None = None,
        classification: str | None = None,
        output_file_name: str | None = None,
        dry_run: bool = False
    ) -> bool:
        """
        Upload a research paper to reMarkable with classification.
        Returns True if successful, False otherwise.
        """

        if not os.path.exists(paper_path):
            print(f"Error: Paper file '{paper_path}' not found")
            return False

        print(f"Analyzing paper: {paper_path}")

        # Get classification and title from Claude if they are not included
        if not title or not classification:
            c, t = analyze_paper_with_claude(paper_path)
            if not title:
                title = t
            if not classification:
                classification = c
            print(f"Classification: {classification}")
            print(f"Title: {title}")

        # Generate formatted filename
        if not output_file_name:
            output_file_name = generate_formatted_filename(title)
            print(f"Formatted filename: {output_file_name}")

        # Ensure directory structure exists
        if not self.ensure_directory(classification):
            return False

        # Upload the file to reMarkable
        target_path = f"/papers/{classification}/{output_file_name}"
        print(f"Uploading to: {target_path}")

        try:
            # Upload the file
            if not dry_run: 
                result = subprocess.run(
                    ["./bin/rmapi", "put", paper_path, f"/papers/{classification}/"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode != 0:
                    print(f"Upload failed: {result.stderr}")
                    return False

            # Rename the file to the formatted name if needed
            original_name = Path(paper_path).name
            if original_name != output_file_name:
                print("Renaming to formatted filename...")
                if not dry_run:
                    subprocess.run(
                        [
                            "./bin/rmapi",
                            "mv",
                            f"/papers/{classification}/{original_name.replace('.pdf', '')}",
                            f"/papers/{classification}/{output_file_name.replace('.pdf', '')}",
                        ],
                        capture_output=True,
                        text=True,
                        check=True,
                    )

            print(f"Successfully uploaded paper to {target_path}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"Error uploading paper: {e}")
            return False
