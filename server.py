from flask import Flask, request, render_template, send_file
from twilio.twiml.messaging_response import MessagingResponse
from flask_sqlalchemy import SQLAlchemy
import os
import time
from datetime import datetime
import os, io 
from google.cloud import vision_v1
from google.cloud.vision_v1 import types
from io import BytesIO
from werkzeug.utils import secure_filename
from twilio.twiml.voice_response import VoiceResponse,Gather
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for
from flask import Flask, request, render_template, send_file
# ...



# 📁 server.py -----
import json
from os import environ as env
from urllib.parse import quote_plus, urlencode
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'token.json'

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")

oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
) 


# auth0 routes 

@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )

# create db for reminder  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reminders.db'
dbt = SQLAlchemy(app)

# db model 
class Exp(dbt.Model):
    id = dbt.Column(dbt.Integer, primary_key=True)
    filename = dbt.Column(dbt.String(50))
    data = dbt.Column(dbt.LargeBinary)
    date_created = dbt.Column(dbt.DateTime, nullable=False, default=datetime.utcnow)


    def __repr__(self):
            return f"Post('{self.title}', '{self.content}')"
with app.app_context():
        dbt.create_all()
        print('Created Database!')

# ...

@app.route("/")
def home():
    reminders = Exp.query.all()
    return render_template("index.html", reminders=reminders)

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if request.method == 'POST':
        file = request.files['file']
        filename = file.filename
        upload = Exp(filename=filename, data=file.read())
        dbt.session.add(upload)
        dbt.session.commit()
        # Perform text detection on the uploaded image

        client = vision_v1.ImageAnnotatorClient()

        # Read the image file
        image_content = file.read()

        # Create an instance of the Image class with the image content
        image = vision_v1.Image(content=image_content)

        # Define the features you want to extract from the image
        features = [
            types.Feature(type=vision_v1.Feature.Type.DOCUMENT_TEXT_DETECTION)
        ]

        # Create the request object with the image and features
        request_annotate= types.AnnotateImageRequest(image=image, features=features)

        # Send the request to the API and get the response
        response = client.annotate_image(request_annotate)

        texts = response.text_annotations

        for text in texts:
            for block in page.blocks:
                print(f'\nBlock confidence: {block.confidence}\n')

                for paragraph in block.paragraphs:
                    print('Paragraph confidence: {}'.format(
                        paragraph.confidence))

                    for word in paragraph.words:
                        word_text = ''.join([
                            symbol.text for symbol in word.symbols
                        ])
                        print('Word text: {} (confidence: {})'.format(
                            word_text, word.confidence))

                        for symbol in word.symbols:
                            print('\tSymbol: {} (confidence: {})'.format(
                                symbol.text, symbol.confidence))

        if response.error.message:
            raise Exception(
                '{}\nFor more info on error messages, check: '
                'https://cloud.google.com/apis/design/errors'.format(
                    response.error.message))

        # return f'Uploaded: {file.filename}
           
    reminders = Exp.query.all()
    return render_template("dashboard.html", reminders=reminders, session=session.get('user'), pretty=json.dumps(session.get('user'), indent=4))

#retrieve
@app.route("/image/<int:reminder_id>")
def get_image(reminder_id):
    reminder = Exp.query.get(reminder_id)
    return send_file(BytesIO(reminder.data), attachment_filename=reminder.filename, as_attachment=True)


@app.route("/")
def home():
    return render_template("index.html", session=session.get('user'), pretty=json.dumps(session.get('user'), indent=4))



    
       


#  store prescription
@app.route('/download/<upload_id>')
def download(upload_id):
    upload = Exp.query.filter_by(id=upload_id).first()
    return send_file(BytesIO(upload.data), download_name=upload.filename, as_attachment=True )

@app.route("/contact", methods=["GET", "POST"])
def contact():
        return render_template("contact.html")


@app.route("/sms", methods=['POST'])
def sms_reply():
    """Respond to incoming calls with a simple text message."""
    # Fetch the message
    msg = request.form.get('Body')

    # Create reply


    resp = MessagingResponse()
  
    resp.message(f"Hi! this a reminder to take your LOSARTAN 50 MILLIGRAM TABS, DISPENSE #30 \n TAKE ONE BY MOUTH DAILY IN THE MORNING FOR PRESSURE CONTROL")
    if msg == "yes": #based on incoming message, send different message
        resp.message(" pill confirmed!")
    elif msg == 'help'.lower():
         resp.message("commands \n YES - type yes a reminder to comfirm your medicine \n ")
    else:
        resp.message("Invalid response. Reply YES to confirm. Reply HELP for more options.")
    


    return str(resp)



if __name__ == "__main__":
    app.run(debug=True)