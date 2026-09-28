"""PubMed ingestion via NCBI E-utilities (esearch + efetch)."""
import xml.etree.ElementTree as ET
from typing import Any

import requests

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
TIMEOUT = 30


class PubMedIngestor:
    """Search PubMed and fetch article metadata + abstracts."""

    def search_articles(self, query: str, max_results: int = 20) -> list[str]:
        url = f"{BASE_URL}esearch.fcgi"
        params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": max_results, "sort": "relevance"}
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("esearchresult", {}).get("idlist", [])

    def fetch_article_details(self, pmid_list: list[str]) -> list[dict[str, Any]]:
        if not pmid_list:
            return []
        url = f"{BASE_URL}efetch.fcgi"
        params = {"db": "pubmed", "id": ",".join(pmid_list), "retmode": "xml"}
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        articles: list[dict[str, Any]] = []
        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            title_el = article.find(".//ArticleTitle")
            pmid = pmid_el.text if pmid_el is not None else "unknown"
            title = "".join(title_el.itertext()).strip() if title_el is not None else "Untitled"

            abstract_parts = [
                "".join(a.itertext()).strip()
                for a in article.findall(".//Abstract/AbstractText")
            ]
            abstract = "\n".join(p for p in abstract_parts if p) or "No abstract available"

            year_el = article.find(".//Journal/JournalIssue/PubDate/Year")
            medline_el = article.find(".//Journal/JournalIssue/PubDate/MedlineDate")
            year = year_el.text if year_el is not None else (
                medline_el.text[:4] if medline_el is not None and medline_el.text else "Unknown"
            )
            journal_el = article.find(".//Journal/Title")
            journal = journal_el.text if journal_el is not None else "Unknown journal"
            authors = [
                f"{a.findtext('LastName', '')} {a.findtext('Initials', '')}".strip()
                for a in article.findall(".//AuthorList/Author")[:5]
            ]

            articles.append({
                "source": "PubMed",
                "source_id": pmid,
                "title": title,
                "text": abstract,
                "publication_year": year,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "journal": journal,
                "authors": [a for a in authors if a],
            })
        return articles

    def ingest(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        pmids = self.search_articles(query, max_results=max_results)
        return self.fetch_article_details(pmids)
