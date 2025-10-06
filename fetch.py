from dotenv import load_dotenv
from newsapi import NewsApiClient
from transformers import pipeline
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
import re
import schedule
import time
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

def clean_content(content):
    if not content:
        return ""
    # Remove HTML tags
    content = re.sub(r'<[^>]+>', '', content)
    # Remove the [+X chars] suffix from NewsAPI
    if '[+' in content:
        content = content.split('[+')[0].strip()
    # Clean up extra whitespace
    content = ' '.join(content.split())
    
    return content

def news_fetch():
    newsapi = NewsApiClient(api_key=os.getenv("NEWSAPI"))
    top_headlines = newsapi.get_top_headlines(category='business', language='en', country='us')
    summarizer = pipeline("summarization", model="t5-small")

    storeSummary = {}
    article_count = 0
    for index, article in enumerate(top_headlines['articles']):
        content = clean_content(article['content'])

        try:
            # Truncate if too long (T5-small has 512 token limit)
            max_input_length = 400
            if len(content) > max_input_length:
                content = content[:max_input_length]
            
            summary_result = summarizer(content, max_length=80, min_length=30, do_sample=False)
            storeSummary[article_count] = {
                'title': article['title'],
                'source': article['source']['name'],
                'summary': summary_result[0]['summary_text']
            }
            article_count += 1
            print(f"Successfully summarized article {article_count}: {article['title']}")
        except Exception as e:
            print(f"Error summarizing article {index}: {e}")
            continue
    
    print(f"\nTotal articles summarized: {article_count}")
    return storeSummary

def send_email(storeSummary):
    sender_email = "webhost@summary.com"
    receiver_email = "avimehta9@gmail.com"

    # Create email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Daily News Summary"
    msg["From"] = sender_email
    msg["To"] = receiver_email

    # Build plain text content from storeSummary
    text_content = "Daily News Summary\n\n"
    for index, article_data in storeSummary.items():
        text_content += f"Article {index + 1}:\n"
        text_content += f"Title: {article_data['title']}\n"
        text_content += f"Source: {article_data['source']}\n"
        text_content += f"Summary: {article_data['summary']}\n\n"

    # Build HTML content from storeSummary
    html_content = """
    <html>
    <body>
        <h2 style="color: #2c3e50;">Hourly News Summary</h2>
        <div style="font-family: Arial, sans-serif; max-width: 800px;">
    """
    
    for index, article_data in storeSummary.items():
        html_content += f"""
            <div style="border: 1px solid #ddd; margin: 20px 0; padding: 15px; border-radius: 8px; background-color: #f9f9f9;">
                <h3 style="color: #34495e; margin-top: 0;">Article {index + 1}</h3>
                <h4 style="color: #2980b9;">{article_data['title']}</h4>
                <p style="color: #7f8c8d; font-size: 14px;"><strong>Source:</strong> {article_data['source']}</p>
                <p style="color: #2c3e50; line-height: 1.6;">{article_data['summary']}</p>
            </div>
        """
    
    html_content += """
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    # Send without login (smtp4dev doesn’t require authentication)
    with smtplib.SMTP("localhost", 25) as server:
        server.send_message(msg)

    print("Email sent (check smtp4dev UI)!")

def job():
    """The scheduled job that runs every hour"""
    print(f"\n{'='*60}")
    print(f"Running scheduled job at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    try:
        # Fetch news and create summaries
        print("Fetching news articles...")
        summaries = news_fetch()
        
        # Send email with the summaries
        if summaries:
            print(f"\nSending email with {len(summaries)} articles...")
            send_email(summaries)
        else:
            print("No articles found to summarize")
    except Exception as e:
        print(f"Error in job: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("News Summary Agent Started!")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Will send news summaries every hour...")
    print("Press Ctrl+C to stop\n")

    job()

    # Schedule to run every hour
    schedule.every().hour.do(job)

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()