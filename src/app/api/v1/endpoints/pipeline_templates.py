import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/")
def list_pipeline_templates():
    """
    Lists all available pipeline templates.
    """
    templates = []
    template_dir = Path("src/app/engine_templates")
    for template_path in template_dir.glob("*.json"):
        with open(template_path, "r") as f:
            templates.append(json.load(f))
    return templates

@router.get("/{pipeline_name}")
def get_pipeline_template(pipeline_name: str):
    """
    Retrieves the content of a specific pipeline template.
    """
    try:
        template_path = Path("src/app/engine_templates") / f"{pipeline_name}.json"
        with open(template_path, "r") as f:
            pipeline_config = json.load(f)
        return pipeline_config
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Pipeline template '{pipeline_name}.json' not found.")