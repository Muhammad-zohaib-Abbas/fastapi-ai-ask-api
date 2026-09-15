import os
from dotenv import load_dotenv
from google import genai
import numpy as np
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY");

client = genai.Client(api_key=api_key)

text = "python is a programing language"



text = "How do I reset my password?"

result = client.models.embed_content(
    model= 'gemini-embedding-001',
    contents= text
)

embedding = result.embeddings[0].values

# print("Number of values:", len(embedding))
# print("First 10 values:", embedding[:10])



# text1 = "How do I reset my password?"
# text2 = "What is the process for changing my password?"
# text2 = "shutup"

# result1 = client.models.embed_content(
#     model="gemini-embedding-001",
#     contents=text1
# )

# result2 = client.models.embed_content(
#     model="gemini-embedding-001",
#     contents=text2
# )

# embedding1 = np.array(result1.embeddings[0].values)
# embedding2 = np.array(result2.embeddings[0].values)

# similarity = np.dot(embedding1, embedding2) / (
#     np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
# )

# print("Similarity:", similarity)


question = "How do I reset my password?"

texts = [
    "What is the process for changing my password?",
    "You can reset your account password from the security settings.",
    "The weather is sunny today.",
    "I like eating pizza.",
    "shutup"
]

# Create embedding for the question
question_result = client.models.embed_content(
    model="gemini-embedding-001",
    contents=question
)

question_embedding = np.array(
    question_result.embeddings[0].values
)

results = []

# Create embeddings and calculate similarity
for text in texts:

    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )

    embedding = np.array(
        result.embeddings[0].values
    )

    similarity = np.dot(question_embedding, embedding) / (
        np.linalg.norm(question_embedding)
        * np.linalg.norm(embedding)
    )

    results.append((similarity, text))

# Sort highest similarity first
results.sort(reverse=True)

for similarity, text in results:
    print(f"{similarity:.4f} → {text}")