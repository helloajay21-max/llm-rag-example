from PyPDF2 import PdfReader

def load_documents(files):
    docs = []

    for file in files:
        if file.name.endswith(".txt"):
            docs.append(file.read().decode("utf-8"))

        elif file.name.endswith(".pdf"):
            reader = PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            docs.append(text)

    return docs