import sys
with open("src/api/routes.py", "r") as f:
    content = f.read()

import_statement = "from src.generation.generator import get_llm\nfrom langchain_core.messages import HumanMessage\nfrom typing import Optional, List\n"
content = content.replace("from typing import List\n", import_statement)

# Replace the ingest_data definition
old_def = """@router.post("/ingest")
def ingest_data(
    domain: str = Form(...),
    file: UploadFile = File(...),
    user_context: dict = Depends(get_current_user_context)
):
    \"\"\"
    Task 4 boundary applied to data uploading/ingestion.
    Ensures an HR employee cannot upload documents into the IT namespace.
    Restricts data ingestion strictly to Admin users.

    Pipeline: load -> chunk -> embed -> upload to Qdrant -> verify.
    \"\"\"
    role = user_context.get("role")
    if role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Only Administrators can perform Data Ingestion."
        )

    allowed_domains = user_context.get("domains", [])
    if domain not in allowed_domains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Write Access Denied: Target namespace {domain} is not in your allowed domains."
        )"""

new_def = """@router.post("/ingest")
def ingest_data(
    file: UploadFile = File(...),
    user_context: dict = Depends(get_current_user_context),
    domain: Optional[str] = Form(None)
):
    \"\"\"
    Task 4 boundary applied to data uploading/ingestion.
    Ensures an HR employee cannot upload documents into the IT namespace.
    Restricts data ingestion strictly to Admin users.

    Pipeline: load -> classify -> chunk -> embed -> upload to Qdrant -> verify.
    \"\"\"
    role = user_context.get("role")
    if role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Only Administrators can perform Data Ingestion."
        )

    allowed_domains = user_context.get("domains", [])
"""
content = content.replace(old_def, new_def)

# Now insert classification right after document loading
old_load = """    if not docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No content extracted from {file.filename}."
        )"""

new_load = """    if not docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No content extracted from {file.filename}."
        )

    # Automatically classify domain using LLM
    try:
        sample_text = " ".join([d.page_content for d in docs])[:3000]
        llm = get_llm(use_local=False, temperature=0.0)
        prompt = f"Analyze the following document text and classify it into one of these domains: 'IT', 'HR', or 'OTHER'. Output EXACTLY one of these three words and nothing else.\\n\\nDocument Text:\\n{sample_text}"
        response = llm.invoke([HumanMessage(content=prompt)])
        detected_domain = response.content.strip().upper()
        
        if detected_domain not in ["IT", "HR"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document content is out of bounds (neither IT nor HR)."
            )
            
        if detected_domain not in allowed_domains:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Write Access Denied: Document classified as {detected_domain}, which is not in your allowed domains."
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM Classification failed: {str(e)}"
        )
"""
content = content.replace(old_load, new_load)

# Fix chunker call and return message
content = content.replace("domain=domain,", "domain=detected_domain,")
content = content.replace("f\"Ingested {file.filename} into namespace: {domain}\",", "f\"Automatically classified and ingested {file.filename} into namespace: {detected_domain}\",")

with open("src/api/routes.py", "w") as f:
    f.write(content)
