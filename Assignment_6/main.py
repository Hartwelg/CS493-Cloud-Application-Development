# from flask import Flask, request
import flask
import json
import requests
import secrets

app = flask.Flask(__name__)

import uuid
app.secret_key = str(uuid.uuid4())
app.debug = True

CLIENT_ID = '829825311795-rj47rh7omodu76gu6t1lt7t7ukomn9ao.apps.googleusercontent.com'
CLIENT_SECRET = 'wEgyBDrUQbKK_FFl-NOU4Uiv'
# SCOPE = 'https://www.googleapis.com/auth/drive.metadata.readonly'
SCOPE = 'https://www.googleapis.com/auth/userinfo.profile'
REDIRECT_URI = 'https://hartwelg-hw6-gae.wl.r.appspot.com/oauth2callback'
# REDIRECT_URI = request.url_root + '/oauth2callback'
STATE = secrets.token_urlsafe(16)

@app.route('/')
def index():
    html = "<head><link rel='stylesheet' href='https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css'></head>"
    html += "<body><div class='jumbotron text-center'><h4>This is the index page. This is used to redirect the user to another page that will lead to the google login page. This is the first step in an oauth2 implementation.</h4></div>"
    html += "<button><a href='/getCreds'>Login</a></button></body>"
    return (html)

@app.route('/getCreds')
def getCreds():
    if 'credentials' not in flask.session:
        return flask.redirect(flask.url_for('oauth2callback'))
    credentials = json.loads(flask.session['credentials'])
    if credentials['expires_in'] <= 0:
        return flask.redirect(flask.url_for('oauth2callback'))
    else:
        headers = {'Authorization': 'Bearer {}'.format(credentials['access_token']), 'State': '{}'.format(STATE)}
        request_uri = 'https://people.googleapis.com/v1/people/me?personFields=names'
        request = requests.get(request_uri, headers=headers)
        name = json.loads(request.text)
        html = "<head><link rel='stylesheet' href='https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css'></head>"
        html += "<body><div class='jumbotron text-center'><h4>This is the splash page. This is used to display the user's first and last name. This is the final stage in an oauth2 implementation.</h4></div>"
        html += "<div class='row'><div class='jumbotron text-center'><h5>Given Name: '" + name["names"][0]["givenName"] + "', Family Name: '" + name["names"][0]["familyName"] + "'</h5></div></div>"
        return (html)

@app.route('/oauth2callback')
def oauth2callback():
    if 'code' not in flask.request.args:
        authorization_uri = ('https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={}&redirect_uri={}&scope={}&state={}').format(CLIENT_ID, REDIRECT_URI, SCOPE, STATE)
        return flask.redirect(authorization_uri)
    else:
        authorization_code = flask.request.args.get('code')
        data = {'code': authorization_code, 'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'redirect_uri': REDIRECT_URI, 'grant_type': 'authorization_code', 'State': STATE}
        if (data['State'] == STATE):
            request = requests.post('https://oauth2.googleapis.com/token', data=data)
            flask.session['credentials'] = request.text
            return flask.redirect(flask.url_for('getCreds'))
        else:
            return ("Could not verify state")

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)