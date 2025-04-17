import gradio as gr
import requests
import os
import fitz  # PyMuPDF for PDFs
import docx

from api.citations import get_citations  # Import our get_citations function
from api.bibtex import get_bibtex  # Import the get_bibtex function
from api.compare import compare_papers
from api.summarizer import summarize_papers
from api.literature_review import generate_literature_review
from api.keyword_extraction import extract_main_keyword

# Global variables to store search result data.
paper_ids = []             # List of paper IDs.
paper_title_map = {}       # Mapping: paper_id -> paper title.

result_titles_list = []       # List of paper titles to show in checkboxes
paper_id_by_title = {}        # Map from title → paper ID (for reverse lookup)

paper_citations = {}  # paper_id → citations HTML
paper_bibtex = {}     # paper_id → bibtex HTML

def validate_selection(selected_titles, min_required):
    if not selected_titles or len(selected_titles) < min_required:
        return False, f"❌ Please select at least {min_required} paper(s)."
    return True, ""

def extract_text_from_file(file_path):
    """
    Extracts text from a given file (.txt, .docx, .pdf).
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_extension == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        
        elif file_extension == ".docx":
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        
        elif file_extension == ".pdf":
            pdf_document = fitz.open(file_path)
            text = "\n".join([page.get_text() for page in pdf_document])
            return text if text else "No extractable text found in the PDF."
        
        else:
            return "Unsupported file format."
    
    except Exception as e:
        return f"Error extracting text: {str(e)}"

def search_and_update(query, file):
    """
    Extracts the main topic keyword from the query (or uploaded file content),
    then passes the extracted keyword to the paper search API.
    """
    global paper_ids, paper_title_map, result_titles_list, paper_id_by_title
    paper_ids = []
    paper_title_map = {}
    result_titles_list = []
    paper_id_by_title = {}

    #Adding loading animation
    loading_spinner_html = """
        <div class="loader"></div>
        <div id="loading-text">Wiz is researching, please wait...</div>
        """

    #Show loading animation
    yield (
        gr.update(value=loading_spinner_html, visible=True),
        gr.update(visible=False),
        gr.update(choices=[], value=[], visible=False)
    )

    # If a file is uploaded, extract its content and append it to the query
    if file is not None:
        file_text = extract_text_from_file(file.name)
        if "Error" in file_text:
            yield (
                gr.update(visible=False),
                gr.update(value=file_text, visible=True),
                gr.update(choices=[], value=[], visible=False)
            )
            return
        
        query += " " + file_text  # Append extracted content to query

    # Extract the main topic keyword from the query
    keyword = extract_main_keyword(query)
    print(f"Extracted Keyword: {keyword}")  # Debugging log

    url = "http://127.0.0.1:5000/chatbot"
    headers = {"Content-Type": "application/json"}
    data = {"message": keyword}  # Send extracted keyword instead of full query

    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            response_data = response.json()
            markdown_text = response_data.get("response", "No response received")
            papers = response_data.get("papers", [])

            # Build global paper_ids and mapping from id to title.
            for paper in papers:
                if isinstance(paper, dict):
                    pid = str(paper.get("id", "N/A"))

                    # preload citations and bibtex
                    paper_citations[pid] = get_citations([pid], paper_title_map)
                    paper_bibtex[pid] = get_bibtex([pid], paper_title_map)

                    title = paper.get("title", "Unknown Title")
                    paper_ids.append(pid)
                    paper_title_map[pid] = title

                    result_titles_list.append(title)
                    paper_id_by_title[title] = pid

                    yield (
                        gr.update(visible=False),
                        gr.update(value=markdown_text, visible=True),
                        gr.update(choices=result_titles_list, value=result_titles_list[:1], visible=True)
                    )
                else:
                    yield (
                        gr.update(visible=False),
                        gr.update(value=f"Error: {response.status_code}", visible=True)
                    )
    except Exception as e:
        yield (
            gr.update(visible=False),
            gr.update(value=f"Request failed: {str(e)}", visible=True),
            gr.update(choices=[], value=[], visible=False)
        )

# For now, we leave other action functions as placeholders.
def action_placeholder():
    return "Other actions not implemented yet."

def handle_get_citations(selected_titles, visible_tabs_value):

    if "Citations" not in visible_tabs_value:
        visible_tabs_value.append("Citations")

    tabs = render_tabs("Citations", visible_tabs_value)

    yield (
        gr.update(value="<div class='loader'></div><div id='loading-text'>Wiz is researching, please wait...</div>", visible=True),
        gr.update(value=""),  # Clear tabs_html
        gr.update(value=""),  # Clear tab_output_html
        gr.update(value=""),  # Clear state_citations
        gr.update(value=""),  # Clear state_summary
        gr.update(value=""),  # Clear state_bibtex
        gr.update(value=""),  # Clear state_compare
        gr.update(value=""),   # Clear active_tab
        gr.update(value="")
    )

    # Retrieve citation content
    result = on_get_citations(selected_titles)
    content = result["value"]

    # Update states and display content
    yield (
        gr.update(visible=""),       # Hide loading spinner
        gr.update(value=tabs),       # Update details_html
        gr.update(value=content),          # Update tabs_html
        gr.update(value=content),       # Update tab_output_html
        gr.update(value=""),       # Update state_citations
        gr.update(value=""),            # Clear state_summary
        gr.update(value=""),            # Clear state_bibtex
        gr.update(value="Citations"),    # Set active_tab
        gr.update(value=visible_tabs_value)
    )

def handle_summarize(selected_titles, visible_tabs_value):

    if "Summary" not in visible_tabs_value:
        visible_tabs_value.append("Summary")

    tabs = render_tabs("Summary", visible_tabs_value)

    yield (
        gr.update(value="<div class='loader'></div><div id='loading-text'>Wiz is researching, please wait...</div>", visible=True),
        gr.update(visible=False),  # tab_output
        gr.update(value=""),       # tabs_html
        gr.update(value=""),       # tab_output
        gr.update(value=""),       # state_citations
        gr.update(value=""),       # state_summary
        gr.update(value=""),       # state_bibtex
        gr.update(value=""),       # state_compare
        gr.update(value=""),       # active_tab
        gr.update(value=visible_tabs_value)
    )

    result = on_summarize(selected_titles)
    content = result["value"]

    yield (
        gr.update(visible=False),       # loading
        gr.update(value=content),       # tab_output
        gr.update(value=tabs),          # tabs_html
        gr.update(value=content),       # tab_output again
        gr.update(value=""),            # state_citations
        gr.update(value=content),       # state_summary
        gr.update(value=""),            # state_bibtex
        gr.update(value=""),            # state_compare
        gr.update(value="Summary"),     # active_tab
        gr.update(value=visible_tabs_value)
    )

def handle_bibtex(selected_titles, visible_tabs_value):

    if "BibTeX" not in visible_tabs_value:
        visible_tabs_value.append("BibTeX")

    tabs = render_tabs("BibTeX", visible_tabs_value)

    yield (
        gr.update(value="<div class='loader'></div><div id='loading-text'>Wiz is researching, please wait...</div>", visible=True),
        gr.update(visible=False),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=visible_tabs_value)
    )

    result = on_bibtex(selected_titles)
    content = result["value"]

    yield (
        gr.update(visible=False),
        gr.update(value=content),
        gr.update(value=tabs),
        gr.update(value=content),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=content),
        gr.update(value=""),
        gr.update(value="BibTeX"),
        gr.update(value=visible_tabs_value)
    )

def handle_compare(selected_titles, visible_tabs_value):

    if "Compare" not in visible_tabs_value:
        visible_tabs_value.append("Compare")

    tabs = render_tabs("Compare", visible_tabs_value)

    yield (
        gr.update(value="<div class='loader'></div><div id='loading-text'>Wiz is researching, please wait...</div>", visible=True),
        gr.update(visible=False),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=visible_tabs_value)
    )

    result = on_compare(selected_titles)
    content = result["value"]

    yield (
        gr.update(visible=False),
        gr.update(value=content),
        gr.update(value=tabs),
        gr.update(value=content),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=content),
        gr.update(value="Compare"),
        gr.update(value=visible_tabs_value)
    )

def render_tabs(active, available_tabs):
    buttons = '<div class="tab-container">'
    for label in available_tabs:
        cls = "tab-btn active" if label == active else "tab-btn"
        buttons += f'''
        <button class="{cls}" onclick="
            const tracker = document.querySelector('textarea[name=__tab_state__]');
            if (tracker) {{
                tracker.value = '{label}';
                tracker.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        ">
            {label}
        </button>
        '''
    buttons += '</div>'
    return buttons

def switch_tab(tab_name, c, s, b, cmp, vis_tabs):
    content = {
        "Citations": c,
        "Summary": s,
        "BibTeX": b,
        "Compare": cmp
    }.get(tab_name, "")
    print(f"[SWITCH] Tab: {tab_name} | Content preview: {content[:100]}")
    return vis_tabs, content, tab_name
    

with gr.Blocks(css="""

    * {
        box-sizing: border-box;
    }

    body, html, .gradio-container, .gradio-app {
        margin: 0;
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(to bottom, #0f172a, #312e81) !important;
        color: #e2e8f0; !important;
        min-height: 100vh;
        padding: 20px;
    }
               
    .gr-block, .gr-box, .gr-button, .gr-textbox, .gr-markdown {
        background-color: transparent !important;
        color: #e2e8f0 !important;
    }
           
    /* ---- App UI Styling ---- */
    html {
        scroll-behavior: smooth;
    }
               
    .gr-button,
    button {
      background-color: #3B82F6 !important;
      color: white !important;
      border: none !important;
      font-weight: bold;
      border-radius: 8px;
      padding: 10px 20px;
      transition: all 0.2s ease-in-out;
    }
    
    /* Hover effect */
    .gr-button:hover,
    button:hover {
      background-color: #2563EB !important;
      box-shadow: 0 0 10px rgba(59, 130, 246, 0.7);
      transform: scale(1.05);
      cursor: pointer;
    }
    
    #centered-form {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 70vh;
    }
    #input-section {
        background: linear-gradient(135deg, #151C3C 0%, #1E2A57 100%); /* Glassy tint */
        backdrop-filter: blur(12px); /* Frosted blur */
        -webkit-backdrop-filter: blur(12px); /* Safari fix */
        padding: 30px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
        width: 100%;
        max-width: 1000px;
        transition: all 0.3s ease;
    }
    #subtitle-text {
        text-align: center;
        font-size: 22px;
        font-weight: bold;
        color: #ffffff !important; 
        background: linear-gradient(90deg, #60a5fa, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
    }
               
    #query-box {
        background: linear-gradient(90deg,rgba(92, 70, 156, 1) 0%, rgba(204, 37, 123, 1) 100%);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
        padding: 12px;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        min-height: 180px;
        max-height: 200px;
        color: #0A0F2C;     
    }
               
    #query-box textarea {
      background: #151C3C !important;
      color: #C3C7D1 !important;
      border: none !important;
      font-size: 14px !important;
      min-height: 150px;
      max-height: 170px;
    }

    #query-box textarea::placeholder {
      color: #C3C7D1 !important;
      font-style: italic;
    }
               
    #query-box input {
        background: transparent !important;
        color: #F2F3F5 !important;
        font-size: 14px;
    }
               
    #query-box input::placeholder {
        color: #FFFFFF;         
    }
               
    #upload-box {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(237, 83, 181, 0.0.15);
        border-radius: 10px;
        min-height: 40px;
        max-height: 60px;
        backdrop-filter: blur(6px);
        color: #e2e8f0;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;             
    }
               
    #upload-box svg {
      /*display: none !important;*/
      height:16px;
      width:16px;
    }

    #upload-box p {
      display: none !important;
    }
               
    #upload-box label {
      font-size: 12px;
    }
               
    #upload-box .wrap:hover {
        border-color: #60a5fa;
    }
               
    #upload-box .wrap.svelte-* {
        max-height: 100px;
        overflow: hidden;
    }
               
    .svelte-12ioyct { /* Target the "Click to upload" span if needed */
        font-size: 0px; /* Hide the "Click to upload" text */
    }
               
    .svelte-12ioyct .icon-wrap svg {
        width: 18px !important; /* Increase the width of the icon */
        height: 18px !important; /* Increase the height of the icon */
    }
               
    .svelte-1rvzbk6 {
        padding-right: 30px;           
    }
               
    #search-btn {
        margin-top: 12px;
    }
               
    #results-box {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      padding: 20px;
      border-radius: 12px;
      /*box-shadow: 0 0 12px rgba(92, 70, 156, 0.3);*/
      box-shadow: 0 0 12px rgba(237, 83, 181, 0.45), 0 0 24px rgba(237, 83, 181, 0.25);
      margin-top: 20px;
      color: #e2e8f0;
    }
               
    #paper-checkboxes {
      background: #151C3C !important;
      border: 1px solid rgba(255, 255, 255, 0.06) !important;
      border-radius: 12px !important;
      box-shadow: 0 0 12px rgba(237, 83, 181, 0.45), 0 0 24px rgba(237, 83, 181, 0.25) !important;
      padding: 20px;
      /*box-shadow: 0 0 12px rgba(59, 130, 246, 0.2);  bluish glow */
    }

    /* Style each checkbox label */
    #paper-checkboxes label {
      display: inline-block;
      margin: 6px;
      padding: 10px 16px;
      background: rgba(255, 255, 255, 0.04);
      border-radius: 8px;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.3s ease;
      font-size: 14px;
      color: #e2e8f0;
    }

    /* Hide the default checkbox */
    #paper-checkboxes input[type="checkbox"] {
      display: none;
    }

    /* Hover effect */
    #paper-checkboxes label:hover {
      border: 1px solid #3B82F6;
      background: rgba(59, 130, 246, 0.15);
    }

    /* ✅ When checkbox is selected */
    #paper-checkboxes label:has(input:checked) {
      background-color: #3B82F6;
      color: white;
      font-weight: 600;
      box-shadow: 0 0 10px rgba(59, 130, 246, 0.4);
      border: 1px solid #3B82F6;
    }
               
    /* --- Radio Tab Switching --- */
               
    #tab-bar-container {
        display: flex; /* To contain and potentially align the tab bar */
        justify-content: center; /* Center the tab bar horizontally */
        width: 100%; /* Make it take the full width of its container */
        max-width: 1000px; /* Limit the maximum width */
        margin: 20px auto; /* Add some top/bottom margin and center horizontally */       
    }
               
    .tab-container-wrapper {
       width: 60%;
    }
               
    #tab-bar {
      display: flex;
      justify-content: center;
      gap: 12px;
      padding: 10px;
      width: 100%;
      min-width:0;
      max-width: 1000px;
      background: #151C3C;
      border-radius: 12px;
      box-shadow: 0 0 5px rgba(59, 130, 246, 0.1);
    }

    #tab-bar label {
      background: rgba(255, 255, 255, 0.05);
      color: #e2e8f0;
      padding: 10px 18px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.3s ease;
      border: 1px solid transparent;
      font-weight: 500;
      font-size: 14px;
    }

    #tab-bar label:hover {
      background: rgba(59, 130, 246, 0.2);
      border-color: rgba(59, 130, 246, 0.6);
    }

    #tab-bar input[type="radio"] {
      display: none;
    }

    /* Active tab highlight (Gradio injects .selected) */
    #tab-bar input[type="radio"]:checked + label,
    #tab-bar .selected {
      background: #3B82F6;
      color: white;
      font-weight: 600;
      border: 1px solid #3B82F6;
      box-shadow: 0 0 8px rgba(59, 130, 246, 0.4);
    }
               
    #tab-output {
      animation: fadeIn 0.4s ease-in-out;
    }
               
    @keyframes fadein {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    /* --- loading animation --- */
               
    .gradio-progress-bar, .gradio-loading-bar {
        background:  rgba(237, 83, 181, 0.74) 100% !important;  
    }

               
    .loader{
      width: 40px;
      aspect-ratio: 1;
      --c:no-repeat linear-gradient(#000 0 0);
      background: 
        var(--c) 0    0,
        var(--c) 0    100%, 
        var(--c) 50%  0,  
        var(--c) 50%  100%, 
        var(--c) 100% 0, 
        var(--c) 100% 100%;
      background-size: 8px 50%;
      animation: l7-0 1s infinite;
      position: relative;
      overflow: hidden;
    }

    .loader:before {
      content: "";
      position: absolute;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #ec2eaf;
      top: calc(50% - 4px);
      left: calc(50% -4px);
      animation: inherit;
      animation-name: l7-1;
    }

    @keyframes l7-0 {
     16.67% {background-size:8px 30%, 8px 30%, 8px 50%, 8px 50%, 8px 50%, 8px 50%}
     33.33% {background-size:8px 30%, 8px 30%, 8px 30%, 8px 30%, 8px 50%, 8px 50%}
     50%    {background-size:8px 30%, 8px 30%, 8px 30%, 8px 30%, 8px 30%, 8px 30%}
     66.67% {background-size:8px 50%, 8px 50%, 8px 30%, 8px 30%, 8px 30%, 8px 30%}
     83.33% {background-size:8px 50%, 8px 50%, 8px 50%, 8px 50%, 8px 30%, 8px 30%}
    }

    @keyframes l7-1 {
        0% { left: calc(50% - 4px); }   /* Start at the center */
        20% { left: 0px; }              /* Move to the left */
        40% { left: calc(50% - 4px); }   /* Move back to the center */
        60% { left: calc(100% - 8px); }  /* Move to the right */
        80%, 100% { left: calc(50% - 4px); } /* Move back to the center */
    }

    /* Style for the text */
    #loading-text {
      font-size: 18px;
      color: #3B82F6;
      margin-top: 10px;
      font-weight: bold;
      text-align: center;
    }

    h2, h3 {
        color: #ffffff;
    }
    .section-card {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    .custom-button {
        background-color: #3B82F6 !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        margin-top: 8px !important;
    }
    .custom-button:hover {
        background-color: #2563EB !important;
    }
    #action-output-container {
        width: 100%;
        max-width: 1000px;
    }
    #details_html {
        padding: 20px;
        background-color: #1e293b;
        border-radius: 12px;
        margin-top: 20px;
        color: #e2e8f0;
        overflow-x: auto;
    }
    .output-box {
        background-color: #1e293b;
        padding: 15px;
        border-radius: 10px;
        color: #e2e8f0;
        font-size: 16px;
        overflow-y: auto;
        max-height: 70vh;
    }
    .gr-button {
        margin-right: 10px;
    }
               
   .citation-box pre {
        white-space: pre-wrap;
        word-wrap: break-word;
        overflow-x: auto;
        font-family: 'Consolas', monospace; /* A more modern monospace font */
        font-size: 14px;
        color: #d4dae0; /* A lighter, more modern gray */
        background-color: #151C3C; /* Darker background to blend better */
        padding: 12px; /* Add some padding inside the pre tag */
        border-radius: 6px; /* Slightly rounded corners for the text block */
        border: 1px solid #334155; /* Subtle border */
    }

    .citation-box {
        margin-bottom: 20px;
        background-color: #151C3C; /* Match pre background or slightly lighter */
        border-radius: 8px;
        border: 1px solid #334155; /* Consistent border */
        padding: 16px;
    }

    .citation-divider {
        border-bottom: 1px solid #334155; /* Consistent divider color */
        margin: 12px 0;
    }

    .citation-block {
        margin-bottom: 10px; /* Slightly increased margin */
    }

    .single-citation {
        line-height: 1.5; /* Improved readability */
        color: #cbd5e1; /* Lighter text color */
    }

    .citation-content {
        padding-left: 16px;
        color: #94a3b8; /* Slightly darker secondary text color */
    }
               
    #tab-bar .gr-radio {
        display: flex;
        justify-content: center;
        gap: 12px;
    }
    #tab-bar .gr-radio label {
        background-color: #1e293b;
        color: #e2e8f0;
        border: 1px solid #3B82F6;
        padding: 10px 20px;
        border-radius: 8px;
        cursor: pointer;
        transition: 0.2s ease-in-out;
    }
    #tab-bar .gr-radio input:checked + label {
        background-color: #3B82F6;
        color: white;
        font-weight: bold;
    }
    #tab-bar .gr-radio label:hover {
        background-color: #334155;
    }
    #tab_selector label {
      background-color: #1e293b;
      color: #e2e8f0;
      border: 1px solid #3B82F6;
      border-radius: 6px;
      margin-right: 10px;
      padding: 6px 12px;
      cursor: pointer;
    }
    
    #tab_selector input[type="radio"]:checked + label {
      background-color: #3B82F6;
      color: white;
    }
    """) as demo:
  
    state_citations = gr.State("")
    state_summary = gr.State("")
    state_bibtex = gr.State("")
    state_compare = gr.State("")
    active_tab = gr.State("")
    visible_tabs = gr.State([])

    tab_tracker = gr.Textbox(visible=False, elem_id="__tab_state__")

    gr.HTML(
    """
    <style>

        
    
        /*--------ScholarWiz Logo Animation ---------*/

        .logo-row{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 14px;
            margin-top: 1px;
        }

        #logo{
            position: relative;
            display: inline-block;
            margin: 0;
            max-width: 300px;
            animation: fill 0.5s ease forwards 2.5s;
        }

        #logo path {
            stroke-dasharray: 836px;
            stroke-dashoffset: 836px;
            animation: line-anim 2.5s forwards;
        }

        @keyframes line-anim {
            to {
                stroke-dashoffset: 0;
            }
        }

        @keyframes fill {
            from {
                fill: transparent;
            }
            to {
                fill: #3B82F6;
            }
        }

        .fade-logo {
            opacity: 0;
            animation: fadeIn 1s ease-in forwards 2.5s;
        }

        @keyframes fadeIn {
            to{
                opacity: 1;
            }
        }
    </style>

    <div style="margin-top: 1px; text-align: center;">
        <div class="logo-row">
            <img src="data:image/png;base64,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" class="fade-logo" width="80" height="80" alt="ScholarWiz Logo" />

            <svg id="logo" width="597" height="104" viewBox="0 0 597 104" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M556.08 97.08C556.08 96.6533 556.08 96.312 556.08 96.056C556.165 95.7147 556.251 95.4587 556.336 95.288C556.421 95.032 556.592 94.6907 556.848 94.264C557.104 93.8373 557.36 93.4533 557.616 93.112C557.872 92.7707 558.256 92.216 558.768 91.448C559.365 90.5946 559.92 89.8266 560.432 89.144C576.048 66.616 583.856 54.712 583.856 53.432C583.856 53.0053 582.875 52.792 580.912 52.792C579.888 52.792 577.243 52.9627 572.976 53.304C568.795 53.56 566.235 53.688 565.296 53.688C563.76 53.7733 562.437 54.4133 561.328 55.608C560.304 56.8027 559.493 57.9973 558.896 59.192C558.299 60.3867 557.787 60.984 557.36 60.984C556.677 60.984 556.336 60.5146 556.336 59.576C556.336 58.04 556.421 56.4613 556.592 54.84C556.848 53.2186 557.147 51.5546 557.488 49.848C557.829 48.056 558 47.032 558 46.776C558.171 45.24 559.024 44.472 560.56 44.472C560.816 44.472 561.541 44.5146 562.736 44.6C563.931 44.6853 565.552 44.7707 567.6 44.856C569.648 44.856 571.867 44.856 574.256 44.856C576.901 44.856 580.272 44.8133 584.368 44.728C588.464 44.5573 591.365 44.472 593.072 44.472C594.096 44.472 594.608 44.8986 594.608 45.752C594.608 46.3493 594.352 47.032 593.84 47.8C593.413 48.4827 592.859 49.2506 592.176 50.104C591.493 50.872 591.067 51.384 590.896 51.64C587.312 57.1867 583.259 63.16 578.736 69.56C574.299 75.8746 571.056 80.568 569.008 83.64C567.045 86.6267 566.064 88.632 566.064 89.656C566.064 90.424 568.155 90.808 572.336 90.808C573.275 90.808 574.469 90.808 575.92 90.808C577.371 90.7226 578.267 90.68 578.608 90.68C580.827 90.68 582.704 90.552 584.24 90.296C585.776 89.9546 586.928 89.4853 587.696 88.888C588.549 88.2053 589.147 87.6507 589.488 87.224C589.829 86.712 590.171 85.944 590.512 84.92C590.939 83.896 591.237 83.2133 591.408 82.872C592.005 81.6773 592.731 81.08 593.584 81.08C594.949 81.08 595.632 81.6773 595.632 82.872C595.632 83.384 594.608 85.9867 592.56 90.68C592.304 91.2773 592.005 92.1306 591.664 93.24C591.408 94.3493 591.152 95.288 590.896 96.056C590.725 96.7387 590.427 97.3786 590 97.976C589.659 98.488 589.189 98.744 588.592 98.744H574C573.488 98.744 572.123 98.7867 569.904 98.872C567.771 98.872 566.021 98.872 564.656 98.872H562.48C561.029 98.872 560.005 98.9147 559.408 99H558.512C556.891 99 556.08 98.36 556.08 97.08Z" stroke=#3B82F6 stroke-width="2"/>
                        <path d="M521.753 50.232C521.753 49.8053 521.838 49.464 522.009 49.208C522.265 48.952 522.692 48.696 523.289 48.44C523.972 48.0987 524.654 47.8427 525.337 47.672C526.02 47.416 527.001 47.0747 528.281 46.648C529.646 46.136 530.926 45.624 532.121 45.112C533.06 44.6853 533.913 44.3013 534.681 43.96C535.534 43.6187 536.089 43.4053 536.345 43.32C536.601 43.1493 536.9 43.0213 537.241 42.936C537.582 42.8507 538.009 42.808 538.521 42.808C539.801 42.808 540.441 43.6187 540.441 45.24C540.441 45.6667 540.313 46.6053 540.057 48.056C539.801 49.5067 539.673 50.616 539.673 51.384V86.456C539.673 89.016 540.057 91.0213 540.825 92.472C541.678 93.9227 542.532 94.8187 543.385 95.16C544.324 95.5013 545.476 95.7147 546.841 95.8C547.865 95.8853 548.548 95.9707 548.889 96.056C549.23 96.056 549.614 96.184 550.041 96.44C550.468 96.696 550.681 97.1227 550.681 97.72C550.681 99.1707 549.956 99.896 548.505 99.896C548.334 99.896 548.036 99.8533 547.609 99.768C547.182 99.768 546.841 99.768 546.585 99.768C544.708 99.768 543.129 99.7253 541.849 99.64C540.569 99.5547 539.118 99.512 537.497 99.512C535.449 99.512 533.529 99.5547 531.737 99.64C529.945 99.7253 528.836 99.768 528.409 99.768C524.996 99.768 523.289 99.2133 523.289 98.104C523.289 96.9093 523.929 96.0987 525.209 95.672C525.294 95.672 525.465 95.6293 525.721 95.544C527.684 94.8613 528.878 94.008 529.305 92.984C530.073 91.2773 530.457 84.4933 530.457 72.632V61.368C530.457 58.8933 530.158 56.9307 529.561 55.48C528.964 54.0293 528.409 53.1333 527.897 52.792C527.385 52.4507 526.489 52.1947 525.209 52.024C524.014 51.768 523.289 51.5973 523.033 51.512C522.18 51.1707 521.753 50.744 521.753 50.232ZM529.049 23.48C529.049 22.456 529.774 21.048 531.225 19.256C532.761 17.3787 534.169 16.44 535.449 16.44C536.814 16.44 538.137 17.336 539.417 19.128C540.697 20.8347 541.337 22.3707 541.337 23.736C541.337 25.1013 540.526 26.6373 538.905 28.344C537.284 29.9653 536.089 30.776 535.321 30.776C533.614 30.776 532.121 29.88 530.841 28.088C529.646 26.296 529.049 24.76 529.049 23.48Z" stroke=#3B82F6 stroke-width="2"/>
                        <path d="M387.515 10.04C387.515 8.84534 388.667 8.24801 390.971 8.24801C391.483 8.24801 393.104 8.33334 395.835 8.50401C398.651 8.58935 401.723 8.63201 405.051 8.63201C407.44 8.63201 409.83 8.58935 412.219 8.50401C414.608 8.33334 415.888 8.24801 416.059 8.24801C416.827 8.24801 417.296 8.37601 417.467 8.63201C417.723 8.80268 417.851 9.18668 417.851 9.78401C417.851 10.296 416.912 11.0213 415.035 11.96C413.243 12.8987 412.347 14.1787 412.347 15.8C412.347 16.568 412.518 17.5067 412.859 18.616C413.2 19.7253 413.883 21.4747 414.907 23.864C415.931 26.2533 416.998 28.728 418.107 31.288C419.302 33.848 421.094 37.816 423.483 43.192C425.872 48.4827 428.219 53.7733 430.523 59.064C431.12 60.4293 431.974 62.4773 433.083 65.208C434.278 67.8533 435.216 70.0293 435.899 71.736C436.667 73.4427 437.478 75.2773 438.331 77.24C439.184 79.1173 439.867 80.5253 440.379 81.464C440.976 82.4027 441.403 82.872 441.659 82.872C442 82.872 443.366 80.2267 445.755 74.936C448.144 69.6453 450.278 64.6533 452.155 59.96C452.496 59.192 452.88 58.3387 453.307 57.4C453.819 56.4613 454.16 55.6933 454.331 55.096C454.587 54.4133 454.715 53.7307 454.715 53.048C454.715 52.024 452.155 45.7947 447.035 34.36C441.915 22.84 438.63 16.2693 437.179 14.648C436.838 14.2213 436.496 13.88 436.155 13.624C435.814 13.368 435.472 13.1547 435.131 12.984C434.875 12.728 434.619 12.5573 434.363 12.472C434.192 12.3013 433.936 12.216 433.595 12.216C433.254 12.1307 432.998 12.088 432.827 12.088C432.742 12.088 432.486 12.088 432.059 12.088C431.718 12.0027 431.504 11.96 431.419 11.96C429.03 11.704 427.579 11.4907 427.067 11.32C426.555 11.064 426.299 10.5947 426.299 9.91201C426.299 8.71734 427.536 8.12001 430.011 8.12001C430.523 8.12001 432.187 8.20535 435.003 8.37601C437.819 8.54668 440.848 8.63201 444.091 8.63201C444.262 8.63201 445.414 8.54668 447.547 8.37601C449.68 8.20535 451.344 8.12001 452.539 8.12001C455.099 8.12001 456.379 8.46134 456.379 9.14401C456.379 9.65601 455.91 10.168 454.971 10.68C454.032 11.192 453.094 11.8747 452.155 12.728C451.302 13.496 450.875 14.4773 450.875 15.672C450.875 17.2933 452.198 21.0907 454.843 27.064C455.014 27.4053 455.568 28.8133 456.507 31.288C457.531 33.7627 458.427 35.8533 459.195 37.56C459.963 39.1813 460.518 39.992 460.859 39.992C461.542 39.992 463.248 36.28 465.979 28.856C468.71 21.3467 470.075 16.9093 470.075 15.544C470.075 14.008 469.435 12.9413 468.155 12.344C466.875 11.6613 465.595 11.192 464.315 10.936C463.035 10.5947 462.395 10.0827 462.395 9.40001C462.395 8.46134 463.334 7.99201 465.211 7.99201C465.723 7.99201 467.003 8.03468 469.051 8.12001C471.099 8.20534 472.55 8.24801 473.403 8.24801H475.579C476.774 8.24801 479.035 8.12001 482.363 7.86401H483.515C484.624 7.86401 485.179 8.29068 485.179 9.14401C485.179 9.99734 484.368 10.68 482.747 11.192C481.126 11.704 480.016 12.2587 479.419 12.856C478.054 14.2213 476.859 16.184 475.835 18.744C474.043 23.096 471.91 28.1733 469.435 33.976C466.875 39.9493 465.382 43.5333 464.955 44.728C464.528 45.9227 464.315 46.9893 464.315 47.928C464.315 48.6107 466.918 54.7547 472.123 66.36C477.328 77.9654 480.4 83.768 481.339 83.768C482.363 83.768 487.312 73.016 496.187 51.512C505.147 29.9227 509.627 18.0613 509.627 15.928C509.627 14.5627 509.115 13.5387 508.091 12.856C507.152 12.088 506.086 11.6613 504.891 11.576C503.696 11.4053 502.587 11.192 501.563 10.936C500.624 10.5947 500.155 10.0827 500.155 9.40001C500.155 8.80268 500.283 8.46135 500.539 8.37601C500.795 8.20535 501.478 8.12001 502.587 8.12001C502.843 8.12001 503.824 8.16268 505.531 8.24801C507.238 8.24801 508.944 8.24801 510.651 8.24801C512.187 8.24801 513.894 8.20534 515.771 8.12001C517.734 8.03468 519.824 7.99201 522.043 7.99201C523.75 7.99201 524.603 8.58935 524.603 9.78401C524.603 10.3813 524.347 10.8507 523.835 11.192C523.408 11.5333 522.726 11.96 521.787 12.472C520.848 12.984 520.038 13.5813 519.355 14.264C518.928 14.6907 518.544 15.1173 518.203 15.544C517.947 15.9707 517.648 16.5253 517.307 17.208C516.966 17.8053 516.667 18.3173 516.411 18.744C516.24 19.1707 515.899 19.9387 515.387 21.048C514.96 22.072 514.619 22.8827 514.363 23.48C507.792 38.1573 500.454 54.6267 492.347 72.888C485.862 87.6507 482.022 96.2694 480.827 98.744C479.632 101.219 478.694 102.456 478.011 102.456C477.584 102.456 477.072 101.901 476.475 100.792C475.878 99.768 475.024 98.0187 473.915 95.544C472.891 92.984 472.294 91.4907 472.123 91.064C471.27 89.1867 470.118 86.584 468.667 83.256C467.302 79.928 466.107 77.112 465.083 74.808C464.144 72.504 463.163 70.1573 462.139 67.768C461.115 65.3787 460.262 63.5867 459.579 62.392C458.896 61.112 458.427 60.472 458.171 60.472C457.318 60.472 454.416 66.36 449.467 78.136C444.603 89.912 442 96.4827 441.659 97.848C441.574 98.1893 441.446 98.5307 441.275 98.872C441.19 99.2134 441.104 99.512 441.019 99.768C440.934 100.024 440.848 100.28 440.763 100.536C440.678 100.792 440.592 101.005 440.507 101.176C440.422 101.347 440.336 101.517 440.251 101.688C440.251 101.859 440.208 101.987 440.123 102.072C440.038 102.243 439.952 102.371 439.867 102.456C439.782 102.541 439.696 102.584 439.611 102.584C439.526 102.669 439.44 102.712 439.355 102.712C439.27 102.797 439.142 102.84 438.971 102.84C438.203 102.84 437.264 101.603 436.155 99.128C435.046 96.7387 433.04 92.0027 430.139 84.92C427.238 77.752 424.294 70.8827 421.307 64.312C416.358 53.4747 411.11 41.2293 405.563 27.576C403.942 23.48 402.192 20.28 400.315 17.976C398.438 15.5867 396.774 14.0933 395.323 13.496C393.872 12.8987 392.55 12.5573 391.355 12.472C390.16 12.3867 389.222 12.216 388.539 11.96C387.856 11.704 387.515 11.064 387.515 10.04Z" stroke=#3B82F6 stroke-width="2"/>
                        <path d="M351.206 50.36C351.206 49.4213 351.761 48.7387 352.87 48.312C354.065 47.8 356.198 47.0747 359.27 46.136C362.427 45.112 365.371 43.96 368.102 42.68C368.955 42.3387 369.553 42.168 369.894 42.168C371.003 42.168 371.558 43.0213 371.558 44.728C371.558 45.0693 371.515 45.624 371.43 46.392C371.43 47.16 371.43 47.7573 371.43 48.184C371.43 49.976 371.473 51.256 371.558 52.024C371.643 52.792 371.729 53.2613 371.814 53.432C371.985 53.6027 372.198 53.688 372.454 53.688C372.625 53.688 373.265 52.8347 374.374 51.128C375.483 49.4213 377.062 47.7147 379.11 46.008C381.158 44.216 383.419 43.32 385.894 43.32C387.43 43.32 389.435 44.1307 391.91 45.752C393.702 46.9467 394.598 48.184 394.598 49.464C394.598 51 394.257 52.3653 393.574 53.56C392.891 54.7547 392.209 55.5653 391.526 55.992C390.929 56.4187 390.502 56.632 390.246 56.632C389.563 56.632 388.326 56.12 386.534 55.096C384.827 54.072 382.822 53.56 380.518 53.56C378.214 53.56 376.038 54.4987 373.99 56.376C372.027 58.2533 371.046 59.96 371.046 61.496V74.808C371.046 77.88 371.046 80.3973 371.046 82.36C371.131 84.2373 371.174 85.432 371.174 85.944C371.174 86.3707 371.174 86.7547 371.174 87.096C371.259 87.4373 371.302 87.8213 371.302 88.248C371.302 90.04 371.899 91.576 373.094 92.856C374.289 94.136 375.697 94.904 377.318 95.16C377.83 95.2453 378.47 95.3307 379.238 95.416C380.006 95.5013 380.603 95.5867 381.03 95.672C381.457 95.672 381.926 95.7573 382.438 95.928C382.95 96.0133 383.291 96.184 383.462 96.44C383.718 96.696 383.846 96.9947 383.846 97.336C383.846 98.7013 383.334 99.384 382.31 99.384C380.859 99.384 378.897 99.256 376.422 99C373.947 98.8293 372.283 98.744 371.43 98.744C368.699 98.744 365.883 98.8293 362.982 99C360.081 99.256 358.459 99.384 358.118 99.384C357.265 99.384 356.625 99.2987 356.198 99.128C355.771 98.9573 355.515 98.7867 355.43 98.616C355.345 98.4453 355.302 98.1893 355.302 97.848C355.302 96.7387 355.857 96.0133 356.966 95.672C359.185 95.16 360.507 94.0933 360.934 92.472C361.446 90.7653 361.702 87.1813 361.702 81.72C361.702 76.1733 361.659 71.608 361.574 68.024C361.574 64.44 361.574 62.1787 361.574 61.24C361.574 60.216 361.531 59.4053 361.446 58.808C361.446 58.2107 361.446 57.6987 361.446 57.272C361.446 56.3333 361.318 55.5653 361.062 54.968C360.806 54.3707 360.166 53.816 359.142 53.304C358.203 52.792 356.838 52.536 355.046 52.536C354.961 52.536 354.747 52.536 354.406 52.536C354.065 52.4507 353.809 52.408 353.638 52.408C352.017 52.408 351.206 51.7253 351.206 50.36Z" stroke=#3B82F6 stroke-width="2"/>
                        <path d="M299.844 88.12C299.844 85.048 300.484 82.488 301.764 80.44C303.044 78.3067 304.964 76.6853 307.524 75.576C310.169 74.3813 312.9 73.4427 315.716 72.76C318.532 72.0773 321.945 71.3947 325.956 70.712C326.468 70.6267 326.852 70.584 327.108 70.584C327.364 70.4987 327.705 70.456 328.132 70.456C328.559 70.3707 328.943 70.2853 329.284 70.2C329.881 70.1147 330.265 70.0293 330.436 69.944C330.692 69.8587 330.905 69.688 331.076 69.432C331.332 69.0907 331.46 68.664 331.46 68.152C331.46 67.2987 331.503 66.1467 331.588 64.696C331.673 63.16 331.716 62.0933 331.716 61.496C331.716 56.632 330.308 53.1333 327.492 51C324.676 48.7813 321.945 47.672 319.3 47.672C313.156 47.672 310.084 50.232 310.084 55.352C310.084 56.0347 310.169 56.888 310.34 57.912C310.511 58.936 310.596 59.6187 310.596 59.96C310.596 61.6667 309.828 62.52 308.292 62.52C307.78 62.52 307.14 62.4773 306.372 62.392C305.604 62.2213 304.708 62.008 303.684 61.752C302.745 61.4107 301.935 60.8987 301.252 60.216C300.655 59.448 300.356 58.552 300.356 57.528C300.356 54.2 302.575 51.0427 307.012 48.056C311.535 44.984 316.484 43.448 321.86 43.448C325.529 43.448 328.644 43.8747 331.204 44.728C333.764 45.5813 335.641 46.5627 336.836 47.672C338.116 48.696 339.097 50.104 339.78 51.896C340.463 53.6027 340.847 54.968 340.932 55.992C341.017 56.9307 341.06 58.1253 341.06 59.576C341.06 65.72 340.932 70.584 340.676 74.168C340.505 77.6667 340.42 80.7387 340.42 83.384C340.42 86.5413 340.761 89.0587 341.444 90.936C342.127 92.728 342.937 93.88 343.876 94.392C344.815 94.904 345.753 95.2027 346.692 95.288C347.631 95.3733 348.441 95.544 349.124 95.8C349.807 96.056 350.148 96.568 350.148 97.336C350.148 99.128 347.46 100.024 342.084 100.024C339.865 100.024 337.945 99.4267 336.324 98.232C334.788 97.0373 333.679 95.8853 332.996 94.776C332.313 93.5813 331.929 92.984 331.844 92.984C331.759 92.984 331.417 93.2827 330.82 93.88C330.223 94.392 329.369 95.032 328.26 95.8C327.236 96.568 326.041 97.336 324.676 98.104C323.396 98.872 321.86 99.512 320.068 100.024C318.361 100.621 316.655 100.92 314.948 100.92C309.487 100.92 305.519 99.64 303.044 97.08C300.911 94.9467 299.844 91.96 299.844 88.12ZM309.828 86.2C309.828 89.1013 310.681 91.448 312.388 93.24C314.095 94.9467 316.527 95.8 319.684 95.8C321.903 95.8 323.78 95.4587 325.316 94.776C326.937 94.0933 328.132 93.3253 328.9 92.472C329.668 91.6187 330.265 90.5093 330.692 89.144C331.119 87.6933 331.332 86.584 331.332 85.816C331.417 85.048 331.46 84.024 331.46 82.744V73.528C331.46 72.76 331.161 72.376 330.564 72.376C330.393 72.376 330.18 72.4187 329.924 72.504C329.668 72.5893 329.455 72.632 329.284 72.632C327.321 72.9733 326.084 73.1867 325.572 73.272C325.06 73.3573 323.865 73.6133 321.988 74.04C320.111 74.4667 318.788 74.8507 318.02 75.192C317.337 75.5333 316.313 76.088 314.948 76.856C313.668 77.5387 312.729 78.3067 312.132 79.16C311.62 79.928 311.108 80.952 310.596 82.232C310.084 83.4267 309.828 84.7493 309.828 86.2Z" stroke=#3B82F6 stroke-width="2"/>
                        <path d="M263.07 10.296C263.07 9.78399 263.113 9.39999 263.198 9.144C263.369 8.888 263.667 8.67466 264.094 8.504C264.521 8.248 264.99 8.07733 265.502 7.992C266.099 7.82133 266.995 7.56533 268.19 7.224C269.385 6.79733 270.579 6.32799 271.774 5.81599C272.457 5.56 273.523 5.09067 274.974 4.408C276.425 3.72533 277.662 3.21333 278.686 2.87199C279.795 2.44533 280.734 2.23199 281.502 2.23199C282.526 2.23199 283.038 3.04266 283.038 4.66399C283.038 5.00533 282.953 6.02933 282.782 7.73599C282.611 9.35733 282.441 11.6613 282.27 14.648C282.099 17.5493 282.014 20.7067 282.014 24.12V31.288C282.014 35.2987 281.971 38.712 281.886 41.528C281.801 44.2587 281.758 46.52 281.758 48.312V86.456C281.758 88.248 281.886 89.7413 282.142 90.936C282.483 92.0453 283.465 93.1547 285.086 94.264C286.793 95.288 289.139 95.8 292.126 95.8C292.553 95.8 292.937 96.0133 293.278 96.44C293.619 96.8667 293.79 97.2933 293.79 97.72C293.79 98.9147 292.467 99.512 289.822 99.512C289.054 99.512 287.049 99.3413 283.806 99C280.649 98.744 278.345 98.616 276.894 98.616C274.675 98.616 272.542 98.7867 270.494 99.128C268.531 99.4693 267.209 99.64 266.526 99.64C265.929 99.64 265.417 99.4693 264.99 99.128C264.649 98.872 264.478 98.616 264.478 98.36C264.478 97.6773 264.649 97.208 264.99 96.952C265.417 96.6107 266.057 96.3547 266.91 96.184C267.849 95.928 268.489 95.7147 268.83 95.544C270.281 94.8613 271.219 93.9227 271.646 92.728C272.073 91.5333 272.286 89.6987 272.286 87.224C272.286 86.8827 272.243 86.3707 272.158 85.688C272.158 84.92 272.158 84.3227 272.158 83.896V74.424C272.158 71.2667 272.243 62.904 272.414 49.336C272.585 35.6827 272.67 25.912 272.67 20.024C272.67 18.0613 272.329 16.312 271.646 14.776C271.049 13.1547 270.366 12.1733 269.598 11.832C268.83 11.4907 267.123 11.32 264.478 11.32C263.539 11.32 263.07 10.9787 263.07 10.296Z" stroke=#3B82F6 stroke-width="2"/>
                        <path d="M198.687 73.016C198.687 65.1653 201.332 58.3387 206.623 52.536C211.999 46.7333 219.423 43.832 228.895 43.832C236.916 43.832 243.871 46.3493 249.759 51.384C255.732 56.4187 258.719 63.3733 258.719 72.248C258.719 81.2933 255.647 88.4187 249.503 93.624C243.444 98.744 236.276 101.304 227.999 101.304C218.783 101.304 211.572 98.5307 206.367 92.984C201.247 87.352 198.687 80.696 198.687 73.016ZM208.799 68.664C208.799 77.4533 211.146 84.4507 215.839 89.656C220.532 94.8613 225.866 97.464 231.839 97.464C236.703 97.464 240.799 95.6293 244.127 91.96C247.455 88.2053 249.119 82.9147 249.119 76.088C249.119 68.5787 247.071 61.9227 242.975 56.12C238.879 50.232 233.162 47.288 225.823 47.288C221.386 47.288 217.418 49.0373 213.919 52.536C210.506 56.0347 208.799 61.4107 208.799 68.664Z" stroke=#3B82F6 stroke-width="2"/>
                        <path d="M124.94 9.78401C124.94 9.10134 125.367 8.54668 126.22 8.12001C127.159 7.60801 128.439 7.13868 130.06 6.71201C131.767 6.28535 133.004 5.90135 133.772 5.56001C139.148 3.17068 142.22 1.97601 142.988 1.97601C144.097 1.97601 144.652 2.95735 144.652 4.92001C144.652 5.34668 144.481 6.37068 144.14 7.99201C143.884 9.61334 143.756 11.2347 143.756 12.856C143.671 20.536 143.543 27.064 143.372 32.44C143.287 37.7307 143.201 41.3147 143.116 43.192C143.031 44.984 142.945 46.4773 142.86 47.672C142.86 48.8667 142.86 49.8053 142.86 50.488C142.86 52.1093 143.201 52.92 143.884 52.92C144.055 52.92 144.908 52.152 146.444 50.616C148.065 48.9947 150.241 47.416 152.972 45.88C155.788 44.2587 158.775 43.448 161.932 43.448C168.844 43.448 174.22 45.496 178.06 49.592C181.9 53.688 183.82 60.0453 183.82 68.664V87.224C183.82 88.0773 183.905 89.016 184.076 90.04C184.247 90.9787 184.673 91.96 185.356 92.984C186.039 94.008 186.935 94.5627 188.044 94.648C192.652 95.0747 194.956 95.9707 194.956 97.336C194.956 98.7013 193.633 99.384 190.988 99.384C190.561 99.384 188.897 99.256 185.996 99C183.18 98.8293 181.26 98.744 180.236 98.744C179.468 98.744 177.676 98.8293 174.86 99C172.129 99.0853 170.636 99.128 170.38 99.128C168.417 99.128 167.436 98.7013 167.436 97.848C167.436 96.9093 167.777 96.312 168.46 96.056C169.228 95.7147 170.039 95.544 170.892 95.544C171.745 95.544 172.513 95.0747 173.196 94.136C173.964 93.1974 174.348 91.7467 174.348 89.784C174.348 89.4427 174.348 89.016 174.348 88.504C174.433 87.992 174.476 87.3093 174.476 86.456C174.476 85.5173 174.476 83.512 174.476 80.44C174.561 77.368 174.604 73.4 174.604 68.536C174.604 63.3307 173.025 58.8507 169.868 55.096C166.711 51.256 162.999 49.336 158.732 49.336C154.721 49.336 150.583 51 146.316 54.328C144.78 55.5227 143.799 57.4854 143.372 60.216C142.945 62.8614 142.732 68.792 142.732 78.008V80.952C142.732 84.792 143.031 87.9067 143.628 90.296C144.311 92.6 145.719 94.2214 147.852 95.16C148.535 95.416 149.473 95.5867 150.668 95.672C151.863 95.7573 152.759 95.928 153.356 96.184C154.039 96.3547 154.38 96.7813 154.38 97.464C154.38 98.488 153.911 99 152.972 99L149.644 98.872C147.425 98.7867 145.164 98.7013 142.86 98.616C140.641 98.4453 139.447 98.36 139.276 98.36C138.679 98.36 137.185 98.488 134.796 98.744C132.407 98.9147 130.871 99 130.188 99C129.079 99 128.225 98.9574 127.628 98.872C127.116 98.7014 126.817 98.5733 126.732 98.488C126.732 98.3173 126.732 98.0613 126.732 97.72C126.732 96.8667 127.244 96.312 128.268 96.056C130.743 95.3733 132.321 94.3067 133.004 92.856C133.772 91.32 134.156 89.1013 134.156 86.2L134.668 42.552V36.28C134.668 23.3947 134.327 15.928 133.644 13.88C133.047 12.088 131.596 11.192 129.292 11.192C128.524 11.192 127.969 11.192 127.628 11.192L127.116 11.064C125.665 11.064 124.94 10.6373 124.94 9.78401Z" stroke=#3B82F6 stroke-width="2"/>
                        <path d="M72.682 74.424C72.682 66.232 75.4127 59.1493 80.874 53.176C86.4207 47.1173 93.5887 44.088 102.378 44.088C105.365 44.088 108.565 44.5147 111.978 45.368C115.477 46.2213 117.269 47.2027 117.354 48.312C117.525 50.36 117.61 52.3654 117.61 54.328C117.61 58.0827 117.141 59.96 116.202 59.96C115.69 59.96 115.221 59.7893 114.794 59.448C114.453 59.0213 114.026 58.424 113.514 57.656C113.087 56.888 112.575 56.2907 111.978 55.864C110.101 54.2427 107.541 52.7067 104.298 51.256C101.141 49.8053 98.026 49.08 94.954 49.08C94.3567 49.08 93.5887 49.2507 92.65 49.592C91.7113 49.848 90.602 50.488 89.322 51.512C88.1273 52.4507 87.018 53.688 85.994 55.224C84.97 56.6747 84.074 58.7227 83.306 61.368C82.6233 64.0133 82.282 67 82.282 70.328C82.282 76.984 84.3727 82.7867 88.554 87.736C92.8207 92.6 98.026 95.032 104.17 95.032C107.157 95.032 109.93 94.4773 112.49 93.368C115.05 92.2587 117.013 91.1493 118.378 90.04C119.829 88.9307 120.725 88.376 121.066 88.376C122.005 88.376 122.474 88.8027 122.474 89.656C122.474 89.912 122.175 90.4667 121.578 91.32C121.066 92.1733 120.17 93.1973 118.89 94.392C117.695 95.5867 116.245 96.7387 114.538 97.848C112.831 98.872 110.613 99.768 107.882 100.536C105.151 101.304 102.25 101.688 99.178 101.688C91.1567 101.688 84.714 99.256 79.85 94.392C75.0713 89.528 72.682 82.872 72.682 74.424Z" stroke=#3B82F6 stroke-width="2"/>
                        <path d="M1.552 75.064C1.552 73.272 2.14934 72.376 3.344 72.376C4.45334 72.376 5.136 72.8027 5.392 73.656C6.24534 75.704 7.01334 77.496 7.696 79.032C8.464 80.4827 9.65867 82.3173 11.28 84.536C12.9013 86.6693 14.6507 88.4613 16.528 89.912C18.4053 91.2773 20.7947 92.472 23.696 93.496C26.6827 94.52 29.9253 95.032 33.424 95.032C39.824 95.032 44.944 93.368 48.784 90.04C52.7093 86.6267 54.672 82.1893 54.672 76.728C54.672 72.7173 53.3493 69.3893 50.704 66.744C48.0587 64.0133 45.0293 62.0933 41.616 60.984C38.2027 59.7893 33.8507 58.2533 28.56 56.376C23.3547 54.4133 19.088 52.4507 15.76 50.488C7.99467 45.88 4.112 39.608 4.112 31.672C4.112 24.0773 6.84267 18.0187 12.304 13.496C17.8507 8.88799 25.0187 6.58398 33.808 6.58398C37.0507 6.58398 40.8907 7.30932 45.328 8.75999C49.8507 10.1253 52.1547 10.808 52.24 10.808C52.496 10.808 52.9653 10.6373 53.648 10.296C54.3307 9.95466 54.8427 9.78399 55.184 9.78399C56.2933 9.78399 56.9333 10.1253 57.104 10.808C58.896 21.1333 59.792 26.936 59.792 28.216C59.792 30.6053 59.1947 31.8 58 31.8C57.232 31.8 56.6347 31.2027 56.208 30.008C55.184 27.5333 54.16 25.528 53.136 23.992C52.1973 22.456 51.5147 21.4747 51.088 21.048C50.6613 20.6213 49.552 19.5973 47.76 17.976C43.152 13.88 37.5627 11.832 30.992 11.832C25.7013 11.832 21.264 13.112 17.68 15.672C14.096 18.232 12.304 21.688 12.304 26.04C12.304 29.88 13.328 33.0373 15.376 35.512C17.5093 37.9867 20.3253 39.9067 23.824 41.272C27.3227 42.6373 30.992 43.9173 34.832 45.112C38.672 46.3067 42.7253 47.9707 46.992 50.104C51.344 52.2373 54.928 54.7973 57.744 57.784C61.1573 61.4533 62.864 66.0187 62.864 71.48C62.864 80.44 60.0053 87.5653 54.288 92.856C48.5707 98.0613 41.488 100.664 33.04 100.664C27.152 100.664 22.416 100.323 18.832 99.64C15.248 99.0427 11.5787 97.7627 7.824 95.8C6.71467 95.1173 5.392 91.7893 3.856 85.816C2.32 79.8427 1.552 76.2587 1.552 75.064Z" stroke=#3B82F6 stroke-width="2"/>
                        </svg>
        </div>
    </div>
    """
    )

    with gr.Row(elem_id="centered-form"):
        # Left Column: Search and action buttons.
        with gr.Column(scale=1, elem_id="input-section"):
            gr.Markdown("### <span style='color:#3B82F6;'>Hey fellow researcher!</span> - Your AI powered research assistant is here to help!", elem_id="subtitle-text")
            query_input = gr.Textbox(label="How can I help with your research today?", placeholder="Try writing something like 'Find research papers on Quantum Computing'", lines=1, elem_id="query-box")
            upload_file = gr.File(label="Upload Document - .pdf, .docx, .txt (optional)", elem_id="upload-box")
            search_button = gr.Button("Search", elem_id="search-btn")

            #results_md = gr.Markdown(label="Search Results")
            gr.HTML("<div id='results-anchor'></div>")
            loading_html = gr.HTML(visible=False)
            results_md = gr.Markdown(visible=False, elem_id="results-box")

            selection = gr.CheckboxGroup(label="Select papers from above that you want to work with", choices=[], visible=False, elem_id="paper-checkboxes")
            
            with gr.Row(elem_id="action-btn-row"):
                btn_citations = gr.Button("Get Citations", elem_classes="action-btn")
                btn_summary = gr.Button("Explain Papers", elem_classes="action-btn")
                btn_bibtex = gr.Button("Get BibTeX Reference", elem_classes="action-btn")
                btn_compare = gr.Button("Compare Papers", elem_classes="action-btn")

    
    gr.HTML("<div id='action-output-anchor'></div>")
    with gr.Column(elem_id="action-output-container"):
        tabs_html = gr.HTML()
        tab_output_html = gr.HTML()
        #details_html = gr.HTML(visible=True)
        tab_output = gr.HTML(visible=True)

    with gr.Row():
        with gr.Column(elem_id="tab-bar-container", scale=1, min_width=0, elem_classes="tab-row-container"):       
            switch_tabs_text = gr.HTML("<span style='color:#e2e8f0; background-color:#151C3C; padding: 5px 10px; border-radius: 8px; margin-right: 10px;'>Switch Tabs from here:</span>")
            tab_selector = gr.Radio(
                choices=["Summary", "Citations", "BibTeX", "Compare"],
                value="Summary",
                interactive=True,
                elem_id="tab-bar",
                label=""
            )

    tab_output = gr.HTML(visible=True, elem_id="tab-output")

    tab_selector.change(
    fn=switch_tab,
    inputs=[tab_selector, state_citations, state_summary, state_bibtex, state_compare, visible_tabs],
    outputs=[tabs_html, tab_output, active_tab]
    )

    tab_tracker.change(
    switch_tab,
    inputs=[tab_tracker, state_citations, state_summary, state_bibtex, state_compare, visible_tabs],
    outputs=[tabs_html, tab_output, active_tab]
    )

    # Wire up the search button.
    search_button.click(
        search_and_update,
        inputs=[query_input, upload_file],
        outputs=[loading_html, results_md, selection]
    )

    def on_get_citations(selected_titles):
        valid, msg = validate_selection(selected_titles, 1)
        if not valid:
            return msg

        selected_ids = [paper_id_by_title[title] for title in selected_titles]
        html_output = "".join([paper_citations.get(pid, "❌ No citations cached.") for pid in selected_ids])
        return html_output
    
    
    def handle_citations_click(selected_titles):
        html = on_get_citations(selected_titles)  # <- returns plain HTML string
        print(f"[DEBUG] Citations Output: {html[:100]}")
        return html, "Citations"

    btn_citations.click(
        fn=handle_citations_click,
        inputs=[selection],
        outputs=[state_citations, tab_selector]
    ).then(
    fn=switch_tab,
    inputs=[tab_selector, state_citations, state_summary, state_bibtex, state_compare, visible_tabs],
    outputs=[tabs_html, tab_output, active_tab]
    )

    # ✅ Now add Summarize here:
    def on_summarize(selected_titles):
        valid, msg = validate_selection(selected_titles, 1)
        if not valid:
            return msg

        selected_ids = [paper_id_by_title[title] for title in selected_titles]
        result_html = summarize_papers(selected_ids, paper_title_map)
        return result_html

    def handle_summary_click(selected_titles):
        html = on_summarize(selected_titles)  # <- returns plain HTML string
        print(f"[DEBUG] Summary Output: {html[:100]}")
        return html, "Summary"

    btn_summary.click(
        fn=handle_summary_click,
        inputs=[selection],
        outputs=[state_summary, tab_selector]
    ).then(
    fn=switch_tab,
    inputs=[tab_selector, state_citations, state_summary, state_bibtex, state_compare, visible_tabs],
    outputs=[tabs_html, tab_output, active_tab]
    )

    # ... btn_summary logic

    def on_bibtex(selected_titles):
        valid, msg = validate_selection(selected_titles, 1)
        if not valid:
            return msg

        selected_ids = [paper_id_by_title[title] for title in selected_titles]
        html_output = "".join([paper_bibtex.get(pid, "❌ No BibTeX cached.") for pid in selected_ids])
        return html_output
    
    def handle_bibtex_click(selected_titles):
        html = on_bibtex(selected_titles)  # <- returns plain HTML string
        print(f"[DEBUG] BibTeX Output: {html[:100]}")
        return html, "BibTeX"

    btn_bibtex.click(
        fn=handle_bibtex_click,
        inputs=[selection],
        outputs=[state_bibtex, tab_selector]
    ).then(
    fn=switch_tab,
    inputs=[tab_selector, state_citations, state_summary, state_bibtex, state_compare, visible_tabs],
    outputs=[tabs_html, tab_output, active_tab]
    )

    def on_compare(selected_titles):
        valid, msg = validate_selection(selected_titles, 2)
        if not valid:
            return msg

        selected_ids = [paper_id_by_title[title] for title in selected_titles]
        result_html = compare_papers(selected_ids, paper_title_map)
        return result_html
    
    def handle_compare_click(selected_titles):
        html = on_compare(selected_titles)  # <- returns plain HTML string
        print(f"[DEBUG] Compare Output: {html[:100]}")
        return html, "Compare"

    btn_compare.click(
        fn=handle_compare_click,
        inputs=[selection],
        outputs=[state_compare, tab_selector]
    ).then(
    fn=switch_tab,
    inputs=[tab_selector, state_citations, state_summary, state_bibtex, state_compare, visible_tabs],
    outputs=[tabs_html, tab_output, active_tab]
    )

    def update_tab_content(selected_tab):
        if selected_tab == "Citations":
            return "<h3>📚 Citation Output Appears Here</h3>"
        elif selected_tab == "Summary":
            return "<h3>📝 Summary Output Appears Here</h3>"
        elif selected_tab == "BibTeX":
            return "<h3>🔖 BibTeX Reference Output Appears Here</h3>"
        elif selected_tab == "Compare":
            return "<h3>📊 Comparison Output Appears Here</h3>"
        else:
            return "<p>Select a tab to view content.</p>"
    

demo.launch(share=True)
