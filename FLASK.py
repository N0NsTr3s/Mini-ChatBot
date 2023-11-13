from flask import Flask, render_template, request, jsonify
from googletrans import Translator
from difflib import get_close_matches
import json
from flask_cors import CORS
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
def load_model(file_path: str) -> dict:
    with open(file_path, "r") as f:
        data: dict = json.load(f)
    return data
modelchatbot = load_model('moldechatbot.json')
translator = Translator()

def save_model(file_path: str, data: dict):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)


def find_best_match(user_question: str, questions: list[str]) -> str | None:
    matches: list = get_close_matches(user_question, questions, n=1, cutoff=0.66)
    return matches[0] if matches else None


def get_answer(question: str, modelchatbot: dict, translator: Translator) -> str | None:
    for q in modelchatbot["questions"]:
        if q["question"].lower() == question.lower():  # Case-insensitive comparison
            return translator.translate(q["answer"], src='en', dest=translator.detect(question).lang).text

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("user_input", "")
    response = get_chatbot_response(user_input)

    return jsonify(response)



@app.route("/update", methods=["POST"])
def update():
    user_input = request.json.get("user_input", "")
    new_answer = request.json.get("new_answer", "")
    updated_answer = update_model(user_input, new_answer)
    return jsonify({"answer": updated_answer, "model_updated": True})




def update_model(user_input, new_answer):
    new_answer_en = translator.translate(new_answer, dest='en').text
    modelchatbot["questions"].append({"question": user_input, "answer": new_answer_en})
    save_model('moldechatbot.json', modelchatbot)
    print("Bot: Model updated. I'll answer correctly next time!")

    return new_answer_en



def get_chatbot_response(user_input):
    detected_language = translator.detect(user_input).lang
    if detected_language != 'en':
        user_input = translator.translate(user_input, dest='en').text

    best_match: str | None = find_best_match(user_input, [q["question"] for q in modelchatbot["questions"]])

    if best_match:
        answer: str = get_answer(best_match, modelchatbot, translator)
        answer = translator.translate(answer, src='en', dest=detected_language).text
        return {"answer": answer, "more_info_needed": False}
    else:
        print("Bot: I do not know, let me search the internet for you.")
        try:
            internet_response = search_web_for_answer(user_input)

            if internet_response:
                # Update the model with the new answer from the internet
                update_model(user_input, internet_response)
                return {"answer": internet_response, "more_info_needed": False}
            else:
                return {"answer": "I couldn't find an answer on the internet. Please provide more information.", "more_info_needed": True}
        except IndexError:
            return {"answer": "An error occurred while processing the response. Please try again.", "more_info_needed": True}


def search_web_for_answer(query):
    headers = {
        'User-agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36'
    }

    html = requests.get(f'https://www.google.com/search?q="{query}"', headers=headers)
    soup = BeautifulSoup(html.text, 'html.parser')


    answer_element = soup.select_one('block-component')
    if answer_element:
        # Extract and clean up the text content
        answer = answer_element.text.strip()

        # Remove "Fragment recomandat de pe web" if present
        keywords = ["Fragment recomandat de pe web", "Recommandé par le Web", "Recomendado por la web", "Web에서 추천하는 내용"]

        for i in keywords:
            if answer.startswith(i):
                answer = answer[len(i):].strip()

        # Remove content after the keyword "Five Shark Tooth Facts"
        keyword = " - "
        index = answer.find(keyword)
        if index != -1:
            answer = answer[:index - 1].strip()

        return answer
    else:
        return None





if __name__ == "__main__":
    app.run(debug=True)
