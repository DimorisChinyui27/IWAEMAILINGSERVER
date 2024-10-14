import io
from flask import Flask, request, jsonify
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import pandas as pd
from dotenv import load_dotenv
import os
import re

app = Flask(__name__)

# Load environment variables
load_dotenv()
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

def is_valid_email(email):
    # Email validation using regex
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def generate_greeting(nom_responsable, sexe_responsable, nom_entreprise):
    if nom_responsable and sexe_responsable and sexe_responsable != "NA":
        if sexe_responsable == 'F':
            return f"Chère {nom_responsable}, responsable de {nom_entreprise}"
        elif sexe_responsable == 'M':
            return f"Cher {nom_responsable}, responsable de {nom_entreprise}"
    return f"Cher(e) responsable de {nom_entreprise}"

def send_email(to_email, subject, html_content):
    message = Mail(
        from_email='info@iwalink.ch',
        to_emails=to_email,
        subject=subject,
        html_content=html_content)
    
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return response.status_code
    except Exception as e:
        print(str(e))
        return None

@app.route('/send-emails', methods=['POST'])
def send_emails():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and file.filename.endswith('.csv'):
        # Read the CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        df = pd.read_csv(stream)
        
        # Filter rows where 'Envoyé' is 'Faux'
        df_to_send = df[df['Envoyé'] == 'Faux']
        
        sent_count = 0
        invalid_emails = []

        for index, row in df_to_send.iterrows():
            email = row['email']
            if is_valid_email(email):
                greeting = generate_greeting(row['nom du responsable'], row['Sexe du Responsable'], row['nom de l\'entreprise'])
                
                # Read the HTML template
                with open('email_template.html', 'r', encoding='utf-8') as file:
                    html_content = file.read()
                
                # Replace the placeholder with the personalized greeting
                html_content = html_content.replace('{greeting}', greeting)
                
                # Send the email
                status_code = send_email(email, "Opportunité unique pour développer votre activité", html_content)
                
                if status_code == 202:
                    sent_count += 1
            else:
                invalid_emails.append(email)

        response = {
            'message': f'Emails sent successfully to {sent_count} recipients',
            'total_processed': len(df_to_send),
            'emails_sent': sent_count,
        }

        if invalid_emails:
            response['warning'] = 'Some emails were invalid and were not sent'
            response['invalid_emails'] = invalid_emails
            response['invalid_count'] = len(invalid_emails)

        return jsonify(response), 200
    else:
        return jsonify({'error': 'Invalid file format. Please upload a CSV file.'}), 400

if __name__ == '__main__':
    app.run(debug=True)