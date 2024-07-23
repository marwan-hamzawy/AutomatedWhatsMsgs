import os
import random
import time
import logging
import pandas as pd
import pywhatkit
from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = '72f3e6c06eb21597d642bc2113fc5dea'

# Set up logging
logging.basicConfig(filename='whatsapp_bulk_sender.log', level=logging.INFO, format='%(asctime)s - %(message)s')

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_skipped_contacts(skipped_contacts, total_numbers):
    now = pd.Timestamp.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f'skipped_contacts_{timestamp}.txt'

    with open(file_name, 'w') as f:
        skipped_count = len(skipped_contacts)
        percentage_skipped = (skipped_count / total_numbers) * 100
        f.write(f"Skipped phone numbers: {skipped_count}\n")
        for name, number in skipped_contacts:
            f.write(f"{name} -> {number}\n")
        f.write(f"Percentage skipped phone numbers: {percentage_skipped:.2f}%\n")

    return file_name

def send_bulk_messages(names, phone_numbers, message):
    skipped_contacts = []
    total_numbers = len(phone_numbers)
    sent_count = 0

    for name, number in zip(names, phone_numbers):
        if len(number[2:]) != 11:
            skipped_contacts.append((name, number))
            continue

        try:
            personalized_message = f"Hello {name}, {message}"

            pywhatkit.sendwhatmsg_instantly(number, personalized_message, wait_time=random.randint(10, 15), tab_close=True, close_time=random.randint(3, 5))
            logging.info(f"Message sent to {number}")
            sent_count += 1

            rand_num = random.randint(5, 10)
            time.sleep(rand_num)
        except Exception as e:
            logging.error(f"Failed to send message to {number}: {e}")
            continue

    file_name = save_skipped_contacts(skipped_contacts, total_numbers)
    return sent_count, file_name

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))

    file = request.files['file']
    message = request.form['message'].strip()

    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))

    if not message:
        flash('Please enter a message to send')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            df = pd.read_csv(file_path, header=None, names=['Name', 'Phone'])
            df['Phone'] = df['Phone'].apply(lambda x: "+2" + str(x).replace(" ", ""))
            names = df['Name'].tolist()
            phone_numbers = df['Phone'].tolist()

            sent_count, skipped_file = send_bulk_messages(names, phone_numbers, message)

            flash(f"Messages sent successfully! Sent count: {sent_count}. Skipped contacts saved to: {skipped_file}")
        except Exception as e:
            flash(f"An error occurred: {str(e)}")

        os.remove(file_path)  # Remove the uploaded file after processing

        return redirect(url_for('index'))

    flash('Invalid file type. Please upload a CSV file.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
