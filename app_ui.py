import gradio as gr
import requests
import os
import fitz  # PyMuPDF
from PIL import Image
import io
import base64

# --- Constants ---
API_URL = os.getenv("API_URL", "http://localhost:8000/api/process_pdf")
CHAT_API_URL = "http://api:8000/api/chat"
PIPELINE_TEMPLATES_URL = "http://api:8000/api/pipeline-templates"
MAX_PAGES = 50

# --- Backend API Functions ---

def get_pipeline_templates():
    """Fetches pipeline templates from the API."""
    try:
        response = requests.get(PIPELINE_TEMPLATES_URL)
        if response.status_code == 200:
            templates = response.json()
            return templates, gr.update(choices=[template['name'] for template in templates])
        else:
            gr.Warning(f"Failed to fetch pipeline templates. Status: {response.status_code}")
            return [], gr.update(choices=[])
    except requests.exceptions.RequestException as e:
        gr.Warning(f"Failed to connect to the API to get templates: {e}")
        return [], gr.update(choices=[])

def process_document(file, prompt_text, pipeline_steps, chatbot, *selected_pages):
    """Processes the selected PDF pages and sends them to the backend API."""
    if file is None:
        gr.Warning("Please upload a PDF file.")
        yield chatbot, gr.update(interactive=True), []
        return

    page_numbers = [i + 1 for i, selected in enumerate(selected_pages) if selected]
    if not page_numbers:
        gr.Warning("Please select at least one page to process.")
        yield chatbot, gr.update(interactive=True), []
        return

    files = {"pdf_file": (file.name, open(file.name, "rb"), "application/pdf")}
    data = {
        "text_prompt": prompt_text,
        "page_numbers": ",".join(map(str, page_numbers)),
        "pipeline_steps": ",".join(pipeline_steps),
    }

    chatbot = chatbot or []
    chatbot.append({"role": "user", "content": prompt_text})
    chatbot.append({"role": "assistant", "content": "Processing your document... Please wait."})
    yield chatbot, gr.update(interactive=False), []

    gallery_images = []
    try:
        response = requests.post(API_URL, files=files, data=data)
        response.raise_for_status()
        response_data = response.json()
        bot_message = response_data.get("response", "Sorry, I couldn't process that.")
        chatbot[-1] = {"role": "assistant", "content": bot_message} # Update the last message

        processing_results = response_data.get("processing_results", [])
        if processing_results:
            first_page_steps = processing_results[0]
            for step_result in first_page_steps:
                input_img_data = base64.b64decode(step_result['input_image'])
                output_img_data = base64.b64decode(step_result['output_image'])
                metadata = step_result['metadata']
                caption = (
                    f"**Step:** {metadata['step_name']}\n"
                    f"**Time:** {metadata['processing_time_ms']:.2f} ms\n"
                    f"**Params:** {metadata['parameters']}"
                )
                gallery_images.append((output_img_data, caption))

    except requests.exceptions.HTTPError as e:
        error_detail = e.response.json().get("detail", "An unknown error occurred.")
        chatbot[-1] = {"role": "assistant", "content": f"Error from API: {error_detail}"}
    except requests.exceptions.RequestException as e:
        chatbot[-1] = {"role": "assistant", "content": f"Failed to connect to the API: {e}"}
    except Exception as e:
        chatbot[-1] = {"role": "assistant", "content": f"An unexpected error occurred: {e}"}

    yield chatbot, gr.update(interactive=True), gallery_images

def chat_with_api(message, history):
    """Sends a chat message to the backend and gets a response."""
    history = history or []
    try:
        response = requests.post(CHAT_API_URL, json={"prompt": message})
        response.raise_for_status()
        response_data = response.json()
        bot_message = response_data.get("message", {}).get("content", "Sorry, I couldn't process that.")
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": bot_message})
    except requests.exceptions.HTTPError as e:
        error_detail = e.response.json().get("detail", "An unknown error occurred.")
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": f"Error from API: {error_detail}"})
    except requests.exceptions.RequestException as e:
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": f"Failed to connect to the API: {e}"})
    except Exception as e:
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": f"An unexpected error occurred: {e}"})
    return history, ""


# --- UI Helper Functions ---

def render_pdf_preview(pdf_file):
    """Renders PDF pages and returns a list of Gradio component updates."""
    updates = []
    if not pdf_file:
        for _ in range(MAX_PAGES):
            updates.append(gr.update(visible=False)) # Column
            updates.append(gr.update(visible=False)) # Checkbox
            updates.append(gr.update(visible=False)) # Image
        return updates

    try:
        with open(pdf_file.name, "rb") as f:
            doc = fitz.open(stream=f.read(), filetype="pdf")
        page_count = len(doc)

        for i in range(MAX_PAGES):
            if i < page_count:
                page = doc.load_page(i)
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                updates.append(gr.update(visible=True)) # Column
                updates.append(gr.update(label=f"Page {i+1}", value=True, visible=True)) # Checkbox
                updates.append(gr.update(value=img, visible=True)) # Image
            else:
                updates.append(gr.update(visible=False))
                updates.append(gr.update(value=False, visible=False))
                updates.append(gr.update(visible=False))
        doc.close()
    except Exception as e:
        gr.Warning(f"Failed to render PDF preview: {e}")
        for i in range(MAX_PAGES):
            updates.append(gr.update(visible=False))
            updates.append(gr.update(visible=False))
            updates.append(gr.update(visible=False))
    return updates

def update_pipeline_from_template(template_name, templates_store):
    """Updates the pipeline selection based on the chosen template."""
    for template in templates_store:
        if template['name'] == template_name:
            return gr.update(value=template['steps'])
    return gr.update(value=[])


# --- Gradio Interface Definition ---

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Document Intelligence & Chat")

    # --- Data Stores ---
    pipeline_templates_store = gr.State([])
    
    with gr.Tabs():
        with gr.TabItem("Document Analysis", id=0):
            with gr.Row(equal_height=True):
                with gr.Column(scale=1):
                    pdf_upload = gr.File(label="Upload PDF", file_types=[".pdf"])
                    prompt = gr.Textbox(label="Prompt", placeholder="e.g., Summarize the key findings for the selected pages...")
                    
                    template_dropdown = gr.Dropdown(label="Pipeline Template", info="Select a template to pre-configure the pipeline.")
                    pipeline_selection = gr.CheckboxGroup(
                        choices=["deskew", "to_grayscale", "enhance_contrast", "binarize_adaptive", "denoise"],
                        label="Image Preprocessing Pipeline",
                        value=["deskew", "to_grayscale", "enhance_contrast", "binarize_adaptive"],
                    )
                    submit_btn = gr.Button("Process Document", variant="primary")
                    
                    gr.Markdown("### Page Preview & Selection")
                    page_previews = []
                    for i in range(MAX_PAGES):
                        with gr.Column(visible=False, min_width=160) as col:
                            cb = gr.Checkbox(label=f"Page {i+1}", value=True, visible=False)
                            img = gr.Image(label=f"Page {i+1} Preview", visible=False, interactive=False)
                            page_previews.extend([col, cb, img])

                with gr.Column(scale=2):
                    doc_chatbot = gr.Chatbot(label="Document Analysis Chat", type='messages', height=600)
                    pipeline_gallery = gr.Gallery(label="Processing Steps", show_label=True, elem_id="gallery", columns=4, height=400)

        with gr.TabItem("General Chat", id=1):
            gr.Markdown("## General Purpose Chat")
            chat_interface = gr.ChatInterface(
                chat_with_api,
                chatbot=gr.Chatbot(
                    type='messages',
                    height=700,
                    avatar_images=(
                        (os.path.join(os.path.dirname(__file__), "assets/avatar_user.png")),
                        (os.path.join(os.path.dirname(__file__), "assets/avatar_bot.png")),
                    )
                ),
                title="Document Assistant",
                description="Ask me anything.",
                type='messages'
            )

    # --- Event Handlers ---
    
    # Document Analysis Tab
    pdf_upload.change(
        fn=render_pdf_preview,
        inputs=pdf_upload,
        outputs=page_previews
    )
    
    checkboxes = [p for p in page_previews if isinstance(p, gr.Checkbox)]
    submit_btn.click(
        fn=process_document,
        inputs=[pdf_upload, prompt, pipeline_selection, doc_chatbot] + checkboxes,
        outputs=[doc_chatbot, submit_btn, pipeline_gallery]
    )

    # Load templates on page load for both tabs
    demo.load(
        fn=get_pipeline_templates,
        inputs=[],
        outputs=[pipeline_templates_store, template_dropdown]
    )

    template_dropdown.change(
        fn=update_pipeline_from_template,
        inputs=[template_dropdown, pipeline_templates_store],
        outputs=[pipeline_selection]
    )

if __name__ == "__main__":
    # Create dummy asset files if they don't exist to prevent Gradio errors
    os.makedirs("assets", exist_ok=True)
    if not os.path.exists("assets/avatar_user.png"):
        Image.new('RGB', (100, 100), color = 'red').save('assets/avatar_user.png')
    if not os.path.exists("assets/avatar_bot.png"):
        Image.new('RGB', (100, 100), color = 'blue').save('assets/avatar_bot.png')
        
    demo.launch(server_name="0.0.0.0", server_port=7860)