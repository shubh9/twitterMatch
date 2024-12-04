import os
from twikit import Client as TwitterClient
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Client initializations
twitter_client = TwitterClient(language='en-US')

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


# test login
# async def main():
#     await twitter_client.login(auth_info_1="shubhctw@gmail.com", password="a_95MSQ4Jz3Vh.-")
#     print("logged in")
# import asyncio
# asyncio.run(main())