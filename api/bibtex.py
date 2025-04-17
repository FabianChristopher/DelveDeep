import requests
from openai import OpenAI
import os
from config import get_openai_api_key

os.environ["OPENAI_API_KEY"] = get_openai_api_key()
client = OpenAI()

def format_bibtex_box(content):
    html = f"""
    <div class="citation-box">
        <h2>BibTeX References</h2>
        {content}
    </div>
    """
    return html

def get_bibtex(paper_ids, paper_title_map, papers=None):
    """
    Tries to retrieve BibTeX for each paper using the ID.
    If retrieval fails and papers are provided, sends paper info to GPT-4o to format a citation.
    """
    lookup_bibtex_url = "http://recommendpapers.xyz/api/bibtex"
    if not paper_ids:
        return "<div>No papers available.</div>"

    all_bibtex_html = ""
    for pid in paper_ids:
        paper_title = paper_title_map.get(pid, pid)
        url = f"{lookup_bibtex_url}?id=CorpusId:{pid}"
        try:
            resp = requests.get(url)
            data = resp.json()
            results = data.get("papers", [])
            if results:
                bibtex_text = results[0].get("bibtex", "No BibTeX found.")
            else:
                raise Exception("BibTeX not found in API response")
        except Exception as e:
            # If papers info is available, try GPT fallback
            if papers:
                matched = next((p for p in papers if str(p.get("id")) == str(pid)), None)
                if matched:
                    try:
                        prompt = f"""
Please generate a BibTeX citation entry for the following paper information:

Title: {matched.get("title", "Unknown Title")}
Authors: {", ".join(matched.get("authors", []))}
Citation Count: {matched.get("citations", 0)}
PDF URL: {matched.get("pdf", "N/A")}
External IDs: {matched.get("external_ids", {})}

Ensure it's well-structured and ready to be used in academic BibTeX format.
"""
                        completion = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{"role": "user", "content": prompt}]
                        )
                        bibtex_text = completion.choices[0].message.content
                    except Exception as gpt_e:
                        bibtex_text = f"❌ GPT Fallback failed: {str(gpt_e)}"
                else:
                    bibtex_text = f"❌ Error retrieving BibTeX for paper {pid}: {str(e)}"
            else:
                bibtex_text = f"❌ Error retrieving BibTeX for paper {pid}: {str(e)}"

        bibtex_html = f"<h3>BibTeX for {paper_title}</h3><pre>{bibtex_text}</pre><hr>"
        all_bibtex_html += bibtex_html

    return format_bibtex_box(all_bibtex_html)
