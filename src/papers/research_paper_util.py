import base64
import io
import json
import os
import re
from pathlib import Path

import anthropic
import PyPDF2
from anthropic.types import TextBlock


def analyze_paper_with_claude(paper_path: str) -> tuple[str, str]:
    """
    Use Claude API to analyze the paper and get classification and title.
    Returns: (classification, formatted_title)
    """
    # Get API key from environment variable
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found in environment variables")
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

    # Create prompt
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
        if isinstance(message.content[0], TextBlock):
            response_text = message.content[0].text.strip()
            result = json.loads(response_text)

            return result["classification"], result["title"]
        else:
            return "", ""

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


def shorten_title_for_filename(title: str, max_words: int = 6) -> str:
    """
    Shorten a title to a maximum number of words for use in a filename.
    Removes common words and focuses on key terms.
    """
    # Common words to skip
    stop_words = {
        "a",
        "an",
        "the",
        "of",
        "for",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "from",
        "by",
        "with",
        "via",
        "using",
        "through",
    }

    # Split into words and filter
    words = title.split()
    key_words = []

    for word in words:
        # Remove punctuation from word
        clean_word = re.sub(r"[^\w\s-]", "", word)
        if clean_word.lower() not in stop_words and clean_word:
            key_words.append(clean_word)
            if len(key_words) >= max_words:
                break

    # If we have too few key words, add some stop words back
    if len(key_words) < 3 and len(words) > len(key_words):
        for word in words:
            clean_word = re.sub(r"[^\w\s-]", "", word)
            if clean_word and clean_word not in key_words:
                key_words.append(clean_word)
                if len(key_words) >= 4:
                    break

    return " ".join(key_words)


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
