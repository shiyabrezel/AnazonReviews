from flask import Flask, render_template, request, jsonify, send_file
from pymongo import MongoClient
import pandas as pd
import re
from collections import Counter
import logging
from io import BytesIO
import pprint
import spacy

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = MongoClient('mongodb://localhost:27017/')
db = client['amazon_reviews']
collection = db['reviews']

nlp = spacy.load('en_core_web_sm')

LIMIT_REVIEWS = 100
LIMIT_TOP_WORDS = 100


def get_reviews(sentiment=None, page=1, page_size=10):
    try:
        logging.info("Starting to get reviews from MongoDB...")
        query = {}
        if sentiment:
            query = {'class': 2 if sentiment == 'positive' else 1}
        else:
            logging.info("No sentiment provided, querying all reviews")
            query = {'class': {'$in': [1, 2]}}

        skip = (page - 1) * page_size

        if skip + page_size > LIMIT_REVIEWS:
            page_size = max(0, LIMIT_REVIEWS - skip)

        reviews = collection.find(query).skip(skip).limit(page_size)
        count = min(collection.count_documents(query), LIMIT_REVIEWS)
        logging.info(f"Query executed: {query}, Number of reviews: {count}")

        df = pd.DataFrame(list(reviews))
        if '_id' in df.columns:
            df.drop(columns=['_id'], inplace=True)
        return df, count
    except Exception as e:
        logging.error(f"Error in get_reviews: {e}")
        raise


def remove_illegal_characters(text):
    try:
        return re.sub(r'[\x00-\x1F\x7F-\x9F\xAD]', '', text)
    except Exception as e:
        logging.error(f"Error cleaning text: {e}")
        return text


def get_top_words(sentiment, limit=10):
    query = {}
    if sentiment == 'positive':
        query = {'class': 2}
    elif sentiment == 'negative':
        query = {'class': 1}

    reviews = collection.find(query, {'title': 1, 'text': 1}).limit(LIMIT_TOP_WORDS)
    all_text = ' '.join([review['text'] for review in reviews])
    all_text = re.sub(r'[.,!?;:()\"\'\[\]{}]', '', all_text)
    words = all_text.lower().split()
    word_counts = Counter(words)
    top_words = word_counts.most_common(limit)
    top_words = [(word.capitalize(), count) for word, count in top_words]

    return top_words


def find_similar_words(word, reviews):
    logging.info(f"Finding similar words for: {word}")
    doc = nlp(word)
    similar_words = set()

    for review in reviews:
        review_text = review.get('text', '')
        review_title = review.get('title', '')
        review_doc = nlp(review_text + ' ' + review_title)
        for token in review_doc:
            if token.has_vector and token.vector_norm:
                similarity = doc.similarity(token)
                if similarity > 0.7:  # סף דמיון
                    similar_words.add(token.text.lower())

    return list(similar_words)



@app.route("/")
def home():
    return render_template('index.html')


@app.route("/reviews")
def reviews():
    try:
        sentiment = request.args.get('sentiment')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        logging.info(f"Received sentiment filter: {sentiment}, page: {page}, page_size: {page_size}")

        filtered_reviews, total_reviews = get_reviews(sentiment, page, page_size)

        filtered_reviews['text'] = filtered_reviews['text'].apply(remove_illegal_characters)


        reviews_list = filtered_reviews.to_dict(orient='records')
        response = {
            'reviews': reviews_list,
            'total_reviews': total_reviews,
            'page': page,
            'page_size': page_size
        }

        logging.info(f"Number of reviews after filtering: {len(reviews_list)}")
        return jsonify(response)
    except Exception as e:
        logging.error(f"Error in reviews route: {e}")
        return "Error processing reviews", 500


@app.route("/top_words")
def top_words():
    try:
        sentiment = request.args.get('sentiment')
        limit = int(request.args.get('limit', 10))
        limit = min(limit, LIMIT_TOP_WORDS)  # Ensure the limit does not exceed the predefined limit
        top_words = get_top_words(sentiment, limit)
        return jsonify(top_words)
    except Exception as e:
        logging.error(f"Error in top_words route: {e}")
        return "Error processing top words", 500


@app.route("/export_reviews")
def export_reviews():
    try:
        sentiment = request.args.get('sentiment')
        logging.info(f"Exporting reviews for sentiment: {sentiment}")

        query = {}
        if sentiment == 'positive':
            query = {'class': 2}
        elif sentiment == 'negative':
            query = {'class': 1}
        elif not sentiment:  # טיפול במקרה של ערך ריק או None
            logging.info("No sentiment provided, exporting all reviews")
            query = {'$or': [
                {'class': {'$exists': True}},
                {'title': {'$exists': True}},
                {'text': {'$exists': True}}
            ]}

        reviews = collection.find(query).limit(LIMIT_REVIEWS)
        df = pd.DataFrame(list(reviews))
        if '_id' in df.columns:
            df.drop(columns=['_id'], inplace=True)

        output = BytesIO()
        logging.info("Starting to write to Excel...")
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        output.seek(0)
        logging.info("Finished writing to Excel")

        return send_file(output, as_attachment=True, download_name=f"reviews.xlsx")
    except Exception as e:
        logging.error(f"Error in export_reviews route: {e}")
        return "Error exporting reviews", 500


@app.route("/similar_words")
def similar_words():
    try:
        word = request.args.get('word')
        sentiment = request.args.get('sentiment')
        logging.info(f"Finding similar words for: {word} with sentiment: {sentiment}")

        query = {}
        if sentiment == 'positive':
            query = {'class': 2}
        elif sentiment == 'negative':
            query = {'class': 1}

        reviews = collection.find(query, {'title': 1, 'text': 1}).limit(LIMIT_REVIEWS)
        similar_words = find_similar_words(word, reviews)
        return jsonify(similar_words)
    except Exception as e:
        logging.error(f"Error in similar_words route: {e}")
        return "Error processing similar words", 500



if __name__ == '__main__':
    app.run(debug=True, threaded=True, port=5001)















