import re
import urllib.request
import xml.etree.ElementTree as ET


class InvalidArxivId(Exception):
    pass


class ArxivFetcher:
    def __init__(self, input_str: str) -> None:
        self.document_id = self.parse_id(input_str)

        if self.document_id is None:
            raise InvalidArxivId(f"Unable to parse an arXiv ID from {input_str}")

    def parse_id(self, input_str: str) -> str | None:
        """
        Parse an arXiv ID from various input formats.
        Accepts: 2301.12345, arXiv:2301.12345, https://arxiv.org/abs/2301.12345, etc.
        Returns the normalized ID (e.g., "2301.12345") or None if invalid.
        """
        # Remove common prefixes and extract the ID
        patterns = [
            r"(?:https?://)?(?:www\.)?arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)",
            r"(?:arxiv:)?([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)",
            r"^([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, input_str.lower())
            if match:
                return match.group(1)
        return None

    def get_metadata(self) -> tuple[str | None, str | None]:
        """
        Fetch metadata from arXiv API.
        Returns: (title, primary_category) or (None, None) if failed.
        """
        api_url = f"http://export.arxiv.org/api/query?id_list={self.document_id}"

        try:
            with urllib.request.urlopen(api_url) as response:
                xml_data = response.read().decode("utf-8")

            # Parse XML
            root = ET.fromstring(xml_data)
            print(root)

            # Define namespaces
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }

            # Find the entry
            entry = root.find("atom:entry", ns)
            if entry is None:
                return None, None

            # Extract title
            title_elem = entry.find("atom:title", ns)
            title = title_elem.text.strip() if title_elem is not None else None

            # Clean up title - remove newlines and extra spaces
            if title:
                title = " ".join(title.split())

            # Extract primary category
            primary_cat = entry.find("arxiv:primary_category", ns)
            if primary_cat is not None:
                category = primary_cat.get("term", "").split(".")[0]
                # Map arXiv categories to simpler names
                category_map = {
                    "cs": "ComputerScience",
                    "math": "Mathematics",
                    "physics": "Physics",
                    "q-bio": "QuantumBiology",
                    "q-fin": "QuantumFinance",
                    "stat": "Statistics",
                    "eess": "Engineering",
                    "econ": "Economics",
                    "astro-ph": "Astrophysics",
                    "cond-mat": "CondensedMatter",
                    "gr-qc": "GeneralRelativity",
                    "hep-ex": "HighEnergyPhysics",
                    "hep-lat": "HighEnergyPhysics",
                    "hep-ph": "HighEnergyPhysics",
                    "hep-th": "HighEnergyPhysics",
                    "math-ph": "MathematicalPhysics",
                    "nlin": "NonlinearSciences",
                    "nucl-ex": "NuclearPhysics",
                    "nucl-th": "NuclearPhysics",
                    "quant-ph": "QuantumPhysics",
                }
                category = category_map.get(category, category.replace("-", ""))
            else:
                category = None

            return title, category

        except Exception as e:
            print(f"Error fetching arXiv metadata: {e}")
            return None, None

    def download_paper(self, output_path: str | None = None) -> str | None:
        """
        Download a paper from arXiv.
        Returns the path the file was saved to if successful, None otherwise.
        """
        # If no output path was specified, just create it in a tmp directory

        if not output_path and self.document_id:
            output_path = f"/tmp/arxiv_{self.document_id.replace('/', '_')}.pdf"

        pdf_url = f"https://arxiv.org/pdf/{self.document_id}.pdf"

        try:
            print(f"Downloading paper from arXiv: {self.document_id}")
            urllib.request.urlretrieve(pdf_url, output_path)
            return output_path
        except Exception as e:
            print(f"Error downloading arXiv paper: {e}")
            return None
