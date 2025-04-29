import requests
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import os

services_token = os.getenv("SERVICES_TOKEN")
email_sender = os.getenv("EMAIL_SENDER")
email_password = os.getenv("EMAIL_PASSWORD")
email_recipient = os.getenv("EMAIL_RECIPIENT")

monitored_keywords = [
    "oferty pracy it",
    "praca it",
    "praca w branży it",
    "praca w it"
]

url = 'https://api.semstorm.com/api-v3/monitoring/monitoring-campaign/get-data.json'
campaign_id = 70156

def fetch_keyword_data(campaign_id, services_token):
    payload = {"id": campaign_id, "services_token": services_token}
    response = requests.post(url, json=payload)
    return response.json() if response.status_code == 200 else None

def send_email(html_content, subject, to_email, from_email, password):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    part = MIMEText(html_content, 'html')
    msg.attach(part)
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(from_email, password)
            server.send_message(msg)
    except Exception as e:
        print(f" Błąd podczas wysyłki maila: {e}")

def process_and_display_data(data, days=7):
    try:
        results = []
        domains = data.get("results", {})
        for domain_data in domains.values():
            for keywords in domain_data.values():
                for keyword_block in keywords.values():
                    keyword_title = keyword_block.get("keyword", {}).get("title", "")
                    if keyword_title not in monitored_keywords:
                        continue
                    date_data = keyword_block.get("data", {})
                    if not date_data:
                        continue
                    for date_str in sorted(date_data.keys(), reverse=True)[:days]:
                        all_positions = []
                        for engine_data in date_data.get(date_str, {}).values():
                            for device_data in engine_data.values():
                                for pos_data in device_data.values():
                                    pos = pos_data.get("position")
                                    if pos is not None:
                                        all_positions.append(pos)
                        if all_positions:
                            avg_position = round(sum(all_positions) / len(all_positions), 2)
                            results.append({
                                "Słowo kluczowe": keyword_title,
                                "Data": date_str,
                                "Pozycja": avg_position
                            })
        df = pd.DataFrame(results)
        if not df.empty:
            df["Data"] = pd.to_datetime(df["Data"]).dt.date
            df = df.sort_values(by=["Słowo kluczowe", "Data"])
            pivot_df = df.pivot(index="Słowo kluczowe", columns="Data", values="Pozycja")
            pivot_df = pivot_df.sort_index()

            html_table = pivot_df.to_html(border=1, justify="center", classes="styled", index=True)

            html_content = f"""
            <html>
                <head>
                    <style>
                        table {{
                            width: 100%;
                            border-collapse: collapse;
                        }}
                        th, td {{
                            padding: 5px 2px;
                            text-align: center;
                            border: 1px solid #ddd;
                        }}
                        th {{
                            background-color: #f2f2f2;
                        }}
                    </style>
                </head>
                <body>
                    <h2>SEMSTORM Monitoring – Pozycje dla theprotocol.it</h2>
                    {html_table}
                </body>
            </html>
            """

            subject = f"Pozycje theprotocol.it – Pozycje z ostatnich {days} dni"
            send_email(html_content, subject, email_recipient, email_sender, email_password)
        else:
            print("Brak danych.")
    except Exception as e:
        print(f"Błąd: {e}")

data = fetch_keyword_data(campaign_id, services_token)
if data:
    process_and_display_data(data)
