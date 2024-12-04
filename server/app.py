from flask import Flask, jsonify
from flask_cors import CORS
from config import twitter_client
from configparser import ConfigParser
from twitter_service import scrape_tweets, process_and_save_tweets, get_profile_description, get_similar_tweets, get_common_interests
import os
import json
import traceback

app = Flask(__name__)

# Allow CORS for all domains on all routes
CORS(app, resources={r"/*": {"origins": "*"}})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

@app.route("/", methods=["GET"])
def hello_world():
    return {"message": "Server dice hola"}

@app.route("/compare/<twitter_handle>", methods=["GET"])
async def compare_likes(twitter_handle):
    try:
        # Check if JSON file exists and has content
        await login_twitter()
        print("logged in")
        friend_json_path = f'data/{twitter_handle}_tweets.json'
        if not os.path.exists(friend_json_path) or os.path.getsize(friend_json_path) == 0:
            all_tweets = await scrape_tweets(twitter_client, twitter_handle)
            await process_and_save_tweets(all_tweets, twitter_handle, friend_json_path)
        profile_description = await get_profile_description(twitter_client, twitter_handle)
        similar_tweets = await get_similar_tweets(friend_json_path)
        common_interests = await get_common_interests(profile_description, similar_tweets)
        return jsonify({"common_interests": 'como estas?'})
    except Exception as e:
        print(f"Error in compare_likes: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

async def login_twitter():
    try:
        # config = ConfigParser()
        # config.read('config.ini')    
        # await twitter_client.login(auth_info_1="shubhctw@gmail.com", password="a_95MSQ4Jz3Vh.-")
        # twitter_client.save_cookies('cookies.json')
        twitter_client.load_cookies('cookies.json')
    except Exception as e:
        print(f"Error logging in: {str(e)}")
        raise e

if __name__ == "__main__":
    app.run(debug=True, port=5000)
