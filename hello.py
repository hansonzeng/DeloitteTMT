from cloudant import Cloudant
from flask import Flask, render_template, request, jsonify, flash
import atexit
import cf_deployment_tracker
import os
import json
import pandas as pd
from watson_developer_cloud import VisualRecognitionV3
from flask_uploads import UploadSet, IMAGES, configure_uploads
from classifyAssociation import(classify, lookup)

# Emit Bluemix deployment event
cf_deployment_tracker.track()

app = Flask(__name__)

db_name = 'mydb'
client = None
db = None

classifier = ["Hikesandbikesnewattempt_1294533937", "default"]
api_key = "72468179b79518522ff0c2d981522827378c8dd4"
#two instances created in this app
visual_recognition = VisualRecognitionV3('2016-05-20', api_key=api_key)

if 'VCAP_SERVICES' in os.environ:
    vcap = json.loads(os.getenv('VCAP_SERVICES'))
    print('Found VCAP_SERVICES')
    if 'cloudantNoSQLDB' in vcap:
        creds = vcap['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
        client = Cloudant(user, password, url=url, connect=True)
        db = client.create_database(db_name, throw_on_exists=False)
elif os.path.isfile('vcap-local.json'):
    with open('vcap-local.json') as f:
        vcap = json.load(f)
        print('Found local VCAP_SERVICES')
        creds = vcap['services']['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
        client = Cloudant(user, password, url=url, connect=True)
        db = client.create_database(db_name, throw_on_exists=False)

# On Bluemix, get the port number from the environment variable PORT
# When running this app on the local machine, default the port to 8000
port = int(os.getenv('PORT', 9000))

photos = UploadSet('photos', IMAGES)
app.config['UPLOADED_PHOTOS_DEST'] = 'static/img'
configure_uploads(app, photos)

#https://www.youtube.com/watch?v=Exf8RbgKmhM
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST' and 'file' in request.files:
        filename = photos.save(request.files['file'])
        flash("Photo saved.")
        return filename
    return render_template('index.html')

@app.route("/results", methods=['POST'])
def recognise_image():
    result_items = list()
    x = visual_recognition
    imgurl = request.form['imgurl']
    # print imgurl
    img = x.classify(images_url=imgurl, classifier_ids=classifier)
    classes = img['images'][0]['classifiers'][0]['classes']
    custom_classes = img['custom_classes']
    images_processed = img['images_processed']
    if img['images'][0]['source_url']:
        source_url = img['images'][0]['source_url']
    else:
        source_url = ''
    if img['images'][0]['resolved_url']:
        resolved_url = img['images'][0]['resolved_url']
    else:
        resolved_url = ''
    complete_response = json.dumps(img, sort_keys = True, indent = 4, separators = (',', ': '))
    return render_template('show_results.html', json_resp=classes, custom_classes=custom_classes,
        images_processed=images_processed, source_url=source_url, resolved_url=resolved_url, complete_response=complete_response)

@app.route("/mba_results", methods=['GET','POST'])
def mba_results():
    cat = "http://www.readersdigest.ca/wp-content/uploads/2011/01/4-ways-cheer-up-depressed-cat.jpg"
    list = os.listdir('static/img')
    num_imgs = len(list)
    if 'classify_image' in request.files:
        save_path = 'static/img/classify_%s.jpg' % num_imgs
        print(type(request.files['classify_image']))
        request.files['classify_image'].save(save_path)
    passed_image = open(save_path, 'rb')
    classification_result = classify(images_file=passed_image, classifier=classifier, min_score=0.4, api_key=api_key)

    print("image classified as ")
    print(classification_result)

    # added cars because bikes isn't one of the groups in the MBA - still awaiting group confirmation from Kate
    # This will also simulate if multiple classifications are returned
    classification_result.append('Cars')

    print("Determining association rules")

    # parameter used to run this
    lookup_values = classification_result

    # Shows how to get some of the output
    for interest in lookup_values:
        print(interest)
        print("looking up")
        print("top two association rules are...")

        # gets rule set from rules table
        rules = lookup(interest, rules_to_return=2)

        # checks if lookup worked
        if isinstance(rules, pd.DataFrame):

            # prints raw dataframe return and then stores values for below example
            print("the rules are")
            print(rules)

            # for use outside the loop
            car_rules = rules

        # prints the invalid return
        else:
            print
            rules

    # Print the top rules from a rule set
    print(car_rules['str_a'][0])

    return render_template('show_results_2.html', passed_image=save_path, top_2_rules=rules)

@app.route('/photo/<id>')
def show(id):
    photo = Photo.load(id)
    if photo is None:
        abort(404)
    url = photos.url(photo.filename)
    return render_template('show.html', url=url, photo=photo)

@app.route('/')
def home():
    return render_template('index.html')

# /* Endpoint to greet and add a new visitor to database.
# * Send a POST request to localhost:8000/api/visitors with body
# * {
# *     "name": "Bob"
# * }
# */
@app.route('/api/visitors', methods=['GET'])
def get_visitor():
    if client:
        return jsonify(list(map(lambda doc: doc['name'], db)))
    else:
        print('No database')
        return jsonify([])

# /**
#  * Endpoint to get a JSON array of all the visitors in the database
#  * REST API example:
#  * <code>
#  * GET http://localhost:8000/api/visitors
#  * </code>
#  *
#  * Response:
#  * [ "Bob", "Jane" ]
#  * @return An array of all the visitor names
#  */
@app.route('/api/visitors', methods=['POST'])
def put_visitor():
    user = request.json['name']
    if client:
        data = {'name':user}
        db.create_document(data)
        return 'Hello %s! I added you to the database.' % user
    else:
        print('No database')
        return 'Hello %s!' % user

@atexit.register
def shutdown():
    if client:
        client.disconnect()

if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'

    app.run(host='0.0.0.0', port=port, debug=True)
