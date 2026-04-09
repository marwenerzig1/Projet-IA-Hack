import numpy as np
import nltk
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from transformers import pipeline
from bs4 import BeautifulSoup
import requests
from pytube import YouTube
nltk.download('stopwords')
# Load the CSV
df = pd.read_csv('howtoasanadatabase.csv', error_bad_lines=False)

# Convert to lowercase
df['Paragraph'] = df['Paragraph'].str.lower()

# Tokenization and stopword removal
stop_words = set(stopwords.words('french'))
df['Paragraph'] = df['Paragraph'].apply(word_tokenize)
df['Paragraph'] = df['Paragraph'].apply(lambda x: [word for word in x if word not in stop_words])

# Convert word lists to strings
df['Paragraph'] = df['Paragraph'].apply(' '.join)

# Calculate TF-IDF
tfidf = TfidfVectorizer(stop_words=stop_words)
tfidf_matrix = tfidf.fit_transform(df['Paragraph'])
cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)

# Create a text generation pipeline
generator = pipeline('text-generation', model="t5-base")

# Function to retrieve information based on a query
def retrieve_info(query):
    query_tfidf = tfidf.transform([query])
    cosine_sim_query = linear_kernel(query_tfidf, tfidf_matrix).flatten()
    related_docs_indices = cosine_sim_query.argsort()[:-2:-1]
    return df['Paragraph'].iloc[related_docs_indices].values[0], df['Link'].iloc[related_docs_indices].values[0]

# Function to get YouTube video title and duration
def get_youtube_info(url):
    response = requests.get(url)
    page = BeautifulSoup(response.text, 'html.parser')
    title = page.find('meta', property='og:title')['content']

    # Retrieve video duration
    yt = YouTube(url)
    duration = convert_seconds_to_minutes(yt.length)

    return title, duration

# Function to convert seconds to minutes
def convert_seconds_to_minutes(seconds):
    minutes, sec = divmod(seconds, 60)
    return f"{minutes} min {sec} sec"

def generate_output(question, context, max_length=200, num_return_sequences=1, temperature=0.7):
    formatted_input = f"question: {question} context: {context}"
    generated_text = generator(formatted_input, max_length=max_length, 
                               num_return_sequences=num_return_sequences, 
                               temperature=temperature, 
                               num_beams=5, 
                               early_stopping=True)[0]['generated_text']
    return generated_text

def process_query(query):
    context, url = retrieve_info(query)

    # Check if at least 30% of query terms exist in the documents
    query_terms = query.split()
    req_tfidf = tfidf.transform([query])
    query_tfidf_values = req_tfidf.toarray()[0]
    num_existing_terms = sum(tfidf_value != 0 for tfidf_value in query_tfidf_values)
    percentage_existing_terms = num_existing_terms / len(query_terms) * 100

    if percentage_existing_terms < 30:
        print("Je ne comprends pas!")
        return

    print("Query:", query)
    generated_text = generate_output(query, context, max_length=300)
    print("Response:")
    print(generated_text)
    title, duration = get_youtube_info(url)
    print("Title:", title)
    print("Duration:", duration)
    print("Link:", url)
    print("\n")
    print("Si malgré ces informations vous êtes toujours dans l'impasse, ne vous inquiétez pas, l'équipe d'iDO est là pour vous ! Cliquez simplement sur ce lien pour nous faire signe et ouvrir une demande de support.")
    print("https://form.asana.com/?k=Vzj6hGTjJfPQTCZzOZs-4A&d=1199168271926687")
    print("to reach out and open a support request.")
    print("\n")

queries = [
    "Quelles sont les options pour suivre le temps effectif dans Asana?",
    "Comment créer un portefeuille ?",
    "comment je peux créer un tableau kanban ?",
    "Qu'est-ce qu'un tableau Kanban dans Asana et dans quelles situations est-il utile de l'utiliser ?",
    "Quelle est l'utilité des @mentions dans les mises à jour de statut sur Asana ?",
    "Comment définir une plage de dates pour une tâche dans Asana ?",
    "Comment peut-on utiliser les intégrations de messagerie avec Asana ?",
    "Comment créer une tâche exemple sur Asana ?",
    "Comment ajoute-t-on des champs personnalisés à un projet sur Asana ?",
    "Comment je peux créer un chatbot ?"
]

for query in queries:
    process_query(query)

