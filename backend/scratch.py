import asyncio
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        response = await model.generate_content_async("Return JSON with 'overall_risk_score': 0.5")
        print("Response text:", response.text)
    except Exception as e:
        print("Exception type:", type(e))
        print("Exception str:", str(e))

asyncio.run(main())

asyncio.run(main())
