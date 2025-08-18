import argparse
import sys

from dotenv import load_dotenv

from .arxiv_fetcher import ArxivFetcher, InvalidArxivId
from .research_paper_util import shorten_title_for_filename
from ..remarkable.rmapi import RMAPI

# Load environment variables from .env file
load_dotenv()


def handle_arxiv_paper(handler: ArxivFetcher, rmapi: RMAPI, dry_run: bool = False) -> bool:
    """
    Handle an arXiv paper: download, classify, and upload to reMarkable.
    Returns True if successful, False otherwise.
    """
    print(f"Processing arXiv paper: {handler.document_id}")

    # Fetch metadata from arXiv
    title, category = handler.get_metadata()

    if not title:
        print("Error: Could not fetch paper metadata from arXiv")
        return False

    print(f"Title: {title}")
    print(f"Category: {category if category else 'Unknown'}")

    # Download the paper
    output_path = handler.download_paper()

    # Shorten the title for filename
    short_title = shorten_title_for_filename(title)
    print(f"Short title: {short_title}")

    rmapi.upload_paper(output_path, title, category, dry_run=dry_run)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload research papers to reMarkable with automatic classification"
    )
    parser.add_argument(
        "paper",
        nargs="?",
        help="Path to PDF file or arXiv ID/URL (e.g., '2301.12345', 'arxiv:2301.12345', 'https://arxiv.org/abs/2301.12345')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If dry-run is set, don't actually upload the paper.",
    )
    args = parser.parse_args()

    rmapi = RMAPI()

    if args.paper:
        # Check if input is an arXiv ID/URL or a file path
        try:
            handler = ArxivFetcher(args.paper)
            # Handle arXiv paper
            success = handle_arxiv_paper(handler, rmapi, args.dry_run)
        except InvalidArxivId:
            # Handle local file
            success = rmapi.upload_paper(args.paper, dry_run=args.dry_run)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
