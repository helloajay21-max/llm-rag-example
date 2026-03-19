# vector_store.py

import faiss
import numpy as np

class VectorStore:
    def __init__(self, dim=1536):
        self.index = faiss.IndexFlatL2(dim)
        self.texts = []

    def add(self, embeddings, texts):
        if len(embeddings) == 0:
            return
        self.index.add(np.array(embeddings).astype("float32"))
        self.texts.extend(texts)

    def search(self, query_embedding, k=3):
        if len(self.texts) == 0:
            return []

        D, I = self.index.search(
            np.array([query_embedding]).astype("float32"), k
        )

        results = []
        for i in I[0]:
            if i < len(self.texts):
                results.append(self.texts[i])

        return results