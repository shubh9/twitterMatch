from datetime import datetime
import time
from twikit import TooManyRequests
from config import openai_client
import json
import os
from typing import List, Dict, Optional
import traceback
import asyncio
# Minimum number of tweets to scrape
MIN_TWEETS = 40

async def scrape_tweets(twitter_client, screen_name):
    all_tweets = []
    try:
        print(f"Getting user {screen_name}")
        user = await twitter_client.get_user_by_screen_name(screen_name)
        
        # Get the initial batch of tweets
        while len(all_tweets) < MIN_TWEETS:
            try:
                tweets_result = await user.get_tweets('Tweets', count=20)
                
                # Convert tweets to a list of dictionaries with the data we want
                for tweet in tweets_result:
                    tweet_data = {
                        'id': tweet.id,
                        'text': tweet.text,
                        'created_at': str(tweet.created_at),
                        'author': tweet.user.screen_name,
                        'likes': tweet.favorite_count,
                        'type': 'Tweets',
                        'retweets': tweet.retweet_count,
                        'replies': tweet.reply_count
                    }
                    all_tweets.append(tweet_data)
                
                # Fetch the next batch of tweets
                tweets_result = await tweets_result.next()
            except TooManyRequests:
                print("Rate limit exceeded, waiting for 3 seconds...")
                await asyncio.sleep(3)
                continue
        
        print(f"Scraped {len(all_tweets)} tweets")
    except Exception as e:
        print(f"Error scraping tweets: {str(e)}")
        raise e
        # Optionally, handle the error as needed

    return all_tweets

def get_embedding(text):
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            encoding_format="float"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {str(e)}")
        return []

def calculate_similarity_score(embedding1: List[float], embedding2: List[float], other_user_name: str, user_name: str) -> float:
    cosine = cosine_similarity(embedding1, embedding2)
    similarity = (cosine + 1) / 2 if user_name == other_user_name else cosine / 2
    return similarity

def cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    if len(embedding1) != len(embedding2):
        raise ValueError("Embeddings must have the same length")

    dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
    magnitude1 = sum(a * a for a in embedding1) ** 0.5
    magnitude2 = sum(b * b for b in embedding2) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0
    return dot_product / (magnitude1 * magnitude2)

async def process_and_save_tweets(tweets_list: List[Dict], twitter_handle: str, friend_json_path: str) -> List[Dict]:
    """
    Process tweets and return them with embeddings.
    
    Args:
        tweets_list: List of tweet dictionaries
    Returns:
        List of processed tweets with embeddings
    """
    processed_tweets = []
    
    total_tweets = len(tweets_list)
    print(f"Processing {total_tweets}")
    for i, tweet in enumerate(tweets_list, 1):
        print(f"Processing tweet {i} of {total_tweets}")
        print(tweet['text'])
        embedding = get_embedding(tweet['text'])
        processed_tweet = {
            'id': tweet['id'],
            'author': tweet['author'],
            'text': tweet['text'], 
            'tweet_type': tweet['type'],
            'embedding': embedding
        }
        processed_tweets.append(processed_tweet)

    if processed_tweets:           
        with open(friend_json_path, 'w', encoding='utf-8') as f:
            json.dump(processed_tweets, f, ensure_ascii=False, indent=2)
    print("scraped and processed tweets")            
    return processed_tweets

async def get_profile_description(twitter_client, twitter_handle):
    user = await twitter_client.get_user_by_screen_name(twitter_handle)
    print("user description", user.description)
    return user.description

async def get_similar_tweets(friend_json_path):
    try:
        # Load shubh_mit tweets from JSON
        with open('data/shubh_mit_tweets.json', 'r', encoding='utf-8') as f:
            shubh_mit_tweets = json.load(f)

        with open(friend_json_path, 'r', encoding='utf-8') as f:
            friends_tweets = json.load(f)
        
        # Store similarity pairs
        similarity_pairs = []
        
        # Compare each friend tweet with each shubh_mit tweet
        for friend_tweet in friends_tweets:
            friend_text = friend_tweet.get('text', '')
            # Skip if tweet has less than 5 words
            if len(friend_text.split()) < 5:
                continue
                
            friend_embedding = friend_tweet.get('embedding', [])
            if not friend_embedding:
                continue
                
            for shubh_tweet in shubh_mit_tweets:
                shubh_text = shubh_tweet.get('text', '')
                # Skip if tweet has less than 5 words
                if len(shubh_text.split()) < 5:
                    print('shubh tweet was smaller than 5 words')
                    continue
                
                shubh_embedding = shubh_tweet.get('embedding', [])
                if not shubh_embedding:
                    continue
                
                # Calculate similarity score
                similarity = cosine_similarity(friend_embedding, shubh_embedding)
                
                similarity_pairs.append({
                    'similarity': similarity,
                    'friend_tweet': {
                        'text': friend_text,
                        'author': friend_tweet.get('author', 'friend')
                    },
                    'shubh_tweet': {
                        'text': shubh_text,
                        'author': shubh_tweet.get('author', 'shubh_mit')
                    }
                })
        
        # Sort by similarity score in descending order and get top 20
        top_pairs = sorted(similarity_pairs, key=lambda x: x['similarity'], reverse=True)[:20]
        
        # Print the similar pairs nicely
        print("\nTop 20 Similar Tweet Pairs:")
        print("=" * 80)
        for idx, pair in enumerate(top_pairs, 1):
            print(f"\nPair {idx} (Similarity Score: {pair['similarity']:.4f})")
            print(f"\nTweet by {pair['friend_tweet']['author']}:")
            print(f"→ {pair['friend_tweet']['text']}")
            print(f"\nTweet by {pair['shubh_tweet']['author']}:")
            print(f"→ {pair['shubh_tweet']['text']}")
            print("-" * 80)
            
        return top_pairs
        
    except Exception as e:
        print(f"Error in get_similar_tweets: {str(e)}")
        print(traceback.format_exc())
        raise e

async def get_common_interests(similar_tweets: List[Dict], twitter_handle: str, description: str) -> List[str]:
    """
    Use GPT to analyze similar tweets and user descriptions to identify common interests.
    
    Args:
        similar_tweets: List of similar tweet pairs
        twitter_handle: The friend's Twitter handle
        description: The friend's Twitter bio
    Returns:
        List of common interest points
    """
    try:
        # Prepare the prompt for GPT
        prompt = f"""
        I want to find common interests between two Twitter users:

        User 1 (@shubh_mit):
        - Bio: "Exploring projects that predict decisions people make - Prev Founded http://Seleste.co"

        User 2 (@{twitter_handle}):
        - Bio: "{description}"

        Here are some similar tweets they've posted:
        """

        # Add top 10 most similar tweet pairs to the prompt
        for pair in similar_tweets[:10]:
            prompt += f"""
            @{pair['friend_tweet']['author']}: {pair['friend_tweet']['text']}
            @{pair['shubh_tweet']['author']}: {pair['shubh_tweet']['text']}
            Similarity: {pair['similarity']:.4f}
            """

        prompt += """
        Based on these tweets and bios, identify specific common interests, topics, or themes shared between these users.
        Return the response as a JSON array of strings, where each string is a bullet point explaining a common interest.
        Focus on detailed specific interests

        Example response:
        ["Both of you have at some point worked out of the Founders Inc incubator", "Your both entreprenuers that have moved from Canada to San Francisco to build your startups", "You're both very into afrobeats music and have been to a lot of shows in the past year"]
        """

        print("PROMPT:", prompt)

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            response_format={ "type": "json" },
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes social media content to find genuine common interests between users. Return your response as a JSON array of strings."},
                {"role": "user", "content": prompt}
            ]
        )

        # Parse the JSON response
        common_interests = json.loads(response.choices[0].message.content)
        return common_interests

    except Exception as e:
        print(f"Error in get_common_interests: {str(e)}")
        print(traceback.format_exc())
        return []