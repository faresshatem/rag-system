import sys
with open("src/api/routes.py", "r") as f:
    content = f.read()

# Add import
if "from src.ingestion.classifier import DocumentClassifier" not in content:
    content = content.replace("from src.ingestion.doc_loader import DocumentLoader\n", "from src.ingestion.doc_loader import DocumentLoader\nfrom src.ingestion.classifier import DocumentClassifier\n")

old_code = """    # Automatically classify domain using LLM
    try:
        sample_text = " ".join([d.page_content for d in docs])[:3000]
        llm = get_llm(use_local=False, temperature=0.0)
        prompt = f"Analyze the following document text and classify it into one of these domains: 'IT', 'HR', or 'OTHER'. Output EXACTLY one of these three words and nothing else.\\n\\nDocument Text:\\n{sample_text}"
        response = llm.invoke([HumanMessage(content=prompt)])
        detected_domain = response.content.strip().upper()"""

new_code = """    # Automatically classify domain using LLM (via new dedicated ingestion module)
    try:
        full_text = " ".join([d.page_content for d in docs])
        detected_domain = DocumentClassifier.classify(full_text)"""

content = content.replace(old_code, new_code)

with open("src/api/routes.py", "w") as f:
    f.write(content)
