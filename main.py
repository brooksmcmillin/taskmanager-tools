import argparse
import base64
import json
import os
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Tuple
import io

import anthropic
from dotenv import load_dotenv
import PyPDF2

# Load environment variables from .env file
load_dotenv()

os.environ["RMAPI_CONFIG"] = "./.rmapi"


def setup_rmapi() -> None:
    """
    Download and unpack the lastest version of rmapi if needed
    """
    url = "https://github.com/ddvk/rmapi/releases/latest/download/rmapi-linux-amd64.tar.gz"

    # Check if rmapi is already in the current directory
    rmapi_path = Path("./rmapi")
    if rmapi_path.exists():
        print("rmapi already exists in current directory")
        return

    # If not, download and unpack it
    print("Downloading rmapi...")
    tarball_path = "rmapi.tar.gz"

    try:
        # Download the tarball
        urllib.request.urlretrieve(url, tarball_path)
        print(f"Downloaded rmapi to {tarball_path}")

        # Extract the tarball
        print("Extracting rmapi...")
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(".")
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


def extract_first_page(paper_path: str) -> bytes:
    """
    Extract only the first page of a PDF.
    Returns the first page as a new PDF in bytes.
    """
    with open(paper_path, "rb") as f:
        pdf_reader = PyPDF2.PdfReader(f)

        # Create a new PDF with just the first page
        pdf_writer = PyPDF2.PdfWriter()
        if len(pdf_reader.pages) > 0:
            pdf_writer.add_page(pdf_reader.pages[0])

        # Write to bytes
        output_buffer = io.BytesIO()
        pdf_writer.write(output_buffer)
        output_buffer.seek(0)
        return output_buffer.read()


def analyze_paper_with_claude(paper_path: str) -> Tuple[str, str]:
    """
    Use Claude API to analyze the paper and get classification and title.
    Returns: (classification, formatted_title)
    """
    # Get API key from environment variable
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "Error: ANTHROPIC_API_KEY not found in environment variables or .env file"
        )
        raise ValueError("Missing ANTHROPIC_API_KEY")

    client = anthropic.Anthropic(api_key=api_key)

    # Extract only the first page of the PDF
    try:
        pdf_content = extract_first_page(paper_path)
        print("Extracted first page for analysis")
    except Exception as e:
        print(f"Warning: Could not extract first page, using full PDF: {e}")
        # Fallback to full PDF if extraction fails
        with open(paper_path, "rb") as f:
            pdf_content = f.read()

    # Create a prompt for Claude
    prompt = """Analyze this research paper and provide:
1. A short classification category (one or two words, e.g., "MachineLearning", "Quantum", "Biology", "Mathematics", etc.)
2. A short, succinct title (4-6 words maximum) that captures the essence of the paper

Respond in JSON format:
{
    "classification": "CategoryName",
    "title": "Short Succinct Title"
}

Important: 
- Classification should be a single category without spaces (use CamelCase if needed)
- Title should be brief and descriptive
- Only respond with the JSON, no other text"""

    try:
        # Send to Claude API
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": base64.b64encode(pdf_content).decode("utf-8"),
                            },
                        },
                    ],
                }
            ],
        )

        # Parse the response
        response_text = message.content[0].text.strip()
        result = json.loads(response_text)

        return result["classification"], result["title"]

    except Exception as e:
        print(f"Error analyzing paper with Claude: {e}")
        # Fallback to generic classification and filename
        return "Uncategorized", Path(paper_path).stem


def generate_formatted_filename(title: str) -> str:
    """
    Generate filename in format: YYYY-MM - Short Succinct Title.pdf
    """
    # current_date = datetime.now().strftime("%Y-%m")
    # Clean the title for filename
    safe_title = "".join(
        c for c in title if c.isalnum() or c in (" ", "-", "_")
    ).strip()
    safe_title = " ".join(safe_title.split())  # Normalize whitespace

    return f"{safe_title}.pdf"


def ensure_remarkable_directory(classification: str) -> bool:
    """
    Ensure the directory structure papers/<classification> exists on reMarkable.
    Returns True if successful, False otherwise.
    """
    try:
        # First, check if papers directory exists
        result = subprocess.run(
            ["./rmapi", "ls", "/"], capture_output=True, text=True, check=False
        )

        # Create papers directory if it doesn't exist
        if "papers" not in result.stdout:
            print("Creating /papers directory...")
            subprocess.run(
                ["./rmapi", "mkdir", "/papers"],
                capture_output=True,
                text=True,
                check=True,
            )

        # Check if classification subdirectory exists
        result = subprocess.run(
            ["./rmapi", "ls", "/papers"], capture_output=True, text=True, check=False
        )

        # Create classification directory if it doesn't exist
        if classification not in result.stdout:
            print(f"Creating /papers/{classification} directory...")
            subprocess.run(
                ["./rmapi", "mkdir", f"/papers/{classification}"],
                capture_output=True,
                text=True,
                check=True,
            )

        return True

    except subprocess.CalledProcessError as e:
        print(f"Error creating directory structure: {e}")
        return False


def upload_paper_to_remarkable(paper_path: str) -> bool:
    """
    Upload a research paper to reMarkable with classification.
    Returns True if successful, False otherwise.
    """
    if not os.path.exists(paper_path):
        print(f"Error: Paper file '{paper_path}' not found")
        return False

    print(f"Analyzing paper: {paper_path}")

    # Get classification and title from Claude
    classification, title = analyze_paper_with_claude(paper_path)
    print(f"Classification: {classification}")
    print(f"Title: {title}")

    # Generate formatted filename
    formatted_filename = generate_formatted_filename(title)
    print(f"Formatted filename: {formatted_filename}")

    # Ensure directory structure exists
    if not ensure_remarkable_directory(classification):
        return False

    # Upload the file to reMarkable
    target_path = f"/papers/{classification}/{formatted_filename}"
    print(f"Uploading to: {target_path}")

    try:
        # Upload the file
        result = subprocess.run(
            ["./rmapi", "put", paper_path, f"/papers/{classification}/"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"Upload failed: {result.stderr}")
            return False

        # Rename the file to the formatted name if needed
        original_name = Path(paper_path).name
        if original_name != formatted_filename:
            print("Renaming to formatted filename...")
            subprocess.run(
                [
                    "./rmapi",
                    "mv",
                    f"/papers/{classification}/{original_name.replace('.pdf', '')}",
                    f"/papers/{classification}/{formatted_filename.replace('.pdf', '')}",
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload research papers to reMarkable with automatic classification"
    )
    parser.add_argument("paper", nargs="?", help="Path to the PDF paper to upload")
    parser.add_argument(
        "--setup", action="store_true", help="Setup rmapi (download if needed)"
    )

    args = parser.parse_args()

    # Always ensure rmapi is set up
    setup_rmapi()

    if args.paper:
        # Upload the specified paper
        success = upload_paper_to_remarkable(args.paper)
        sys.exit(0 if success else 1)
    elif not args.setup:
        parser.print_help()


if __name__ == "__main__":
    main()
