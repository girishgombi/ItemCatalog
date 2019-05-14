import json
import random
import string
import httplib2
import requests

from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from flask import make_response
from flask import session as login_session

from oauth2client.client import FlowExchangeError
from oauth2client.client import flow_from_clientsecrets

from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker

from database_setup import Base, Category, Item, User

app = Flask(__name__)

CLIENT_ID = json.loads(
        open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item Catalog Application"

# Connect to Database and create database session.
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/login')
def showLogin():
    '''
    Creates anti-forgery state token and passes that token to be used in Facebook or Google login.

    :return: Renders html template for Facebook and Google login.
    '''
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


################################################################################
# Facebook and Google logins
################################################################################


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    '''
    Connect to Facebook.

    :return: Renders html template with user's Facebook picture and username.
    '''
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
            open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    # strip expire tag from access token
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout.
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture.
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # Check to see if the user exists.
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/gconnect', methods=['POST'])
def gconnect():
    '''
    Connect to Google Plus.

    :return: Renders html template with user's Google+ picture and username.
    '''
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
                json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
                json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
                json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['credentials'] = credentials.to_json()
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


################################################################################
# Facebook and Google logouts
################################################################################


@app.route('/disconnect')
def disconnect():
    '''
    Depending on the account the user used to login- Google or Facebook,
    disconnect uses gdisconnect or fbdisconnect respectively.
    Delete the user data from the login session once the user has logged out.

    :return: Renders html template with catalog home page.
    '''
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCatalog'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCatalog'))


@app.route('/fbdisconnect')
def fbdisconnect():
    '''
    Logout helper method used by the disconnect method to log user out of their Facebook account.

    :return: Returns a string message to notify the user that they have been logged out.
    '''
    facebook_id = login_session['facebook_id']

    # Include the access token to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "You have been logged out"


@app.route('/gdisconnect')
def gdisconnect():
    '''
    Logout helper method used by the disconnect method to log user out of their Google account.
    This method revokes a current user's token and resets their login_session.

    :return: Returns a response object if an error occurs while logout.
    '''
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
                json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = json.loads(credentials)['access_token']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # In case the given token was invalid.
        response = make_response(
                json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


################################################################################
# User Helper Functions
################################################################################


def createUser(login_session):
    '''
    Create a new user and add to database.

    :param login_session: session object.
    :return: returns the user ID.
    '''
    newUser = User(name=login_session['username'], email=login_session[
        'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUser(user_id):
    '''
    Fetch the user from the database with user id.

    :param user_id: The id of the user.
    :return: return the user object for the user id.
    '''
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    '''
    Fetch the user id from email.

    :param email: The user email.
    :return: return the user with the email.
    '''
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def getImageUrl(item):
    """Get URL for an image file.
    If no file is specified, returns a URL for a place holder image.
    """
    if item.image is not None:
        return item.image
    else:
        return "http://www.wonderslist.com/wp-content/uploads/2013/01/Most-Beautiful-Flowers.jpg"


################################################################################
# JSON APIs to view Catalog/Category/Item Information
################################################################################


@app.route('/catalog/categories/JSON')
def getCategoriesJSON():
    '''
    Fetch json for all categories in catalog.

    :return: Returns the json data for all categories.
    '''
    categories = session.query(Category).all()
    return jsonify(categories=[r.serialize for r in categories])


@app.route('/catalog/<string:category_name>/items/JSON')
def getCategoryItemsJSON(category_name):
    '''
    Fetch json for all items in category with category_name.

    :return: Returns the json data for all items in the category.
    '''
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(Item).filter_by(
            category_id=category.id).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/catalog.json')
def getCatalogJSON():
    '''
    Fetch json for all categories and all items in catalog.

    :return: Returns the json data for all categories and all items in catalog.
    '''
    categories = session.query(Category).all()
    items = session.query(Item).all()
    return jsonify(categories=[c.serialize for c in categories],
                   items=[i.serialize for i in items])


@app.route('/catalog/<string:item_name>/JSON')
def getItemJSON(item_name):
    '''
    Fetch json for item in catalog.

    :return: Returns the json data for item.
    '''
    item = session.query(Item).filter_by(name=item_name).one()
    return jsonify(item=item.serialize)


################################################################################
# APIs to view Catalog/Category/Item
################################################################################

@app.route('/')
@app.route('/catalog/')
def showCatalog():
    '''
    Show all categories with latest items.

    :return: Renders html template with all categories and items.
    '''
    categories = session.query(Category).order_by(asc(Category.name))
    latest_items = session.query(Item).order_by(desc(Item.updated)).limit(12)
    if 'username' not in login_session:
        return render_template('publicCatalog.html', categories=categories, latest_items=latest_items)
    else:
        return render_template('catalog.html', categories=categories, latest_items=latest_items)


@app.route('/catalog/<string:category_name>/items')
def showCategory(category_name):
    '''
    Show the category with the category_name and the items in that category.

    :return: Renders html template with all categories and items.
    '''
    categories = session.query(Category).order_by(asc(Category.name))
    category = session.query(Category).filter_by(name=category_name).one()
    category_items = session.query(Item).filter_by(category_id=category.id).all()
    category_name = category.name
    return render_template('categoryItems.html', categories=categories, category_items=category_items,
                           category_name=category_name)


@app.route('/catalog/<string:category_name>/<string:item_name>')
def showItem(category_name, item_name):
    '''
    Show the item with name item_name and in category with category_name.

    :return: Renders html template for the item information.
    '''
    item = session.query(Item).filter_by(name=item_name).one()
    if 'username' in login_session and item.user_id == login_session['user_id']:
        return render_template('item.html', item=item)
    return render_template('publicItem.html', item=item)


################################################################################
# APIs to Create/Edit/Delete Item
################################################################################


@app.route('/catalog/item/new/', methods=['GET', 'POST'])
def newItem():
    '''
    Create a new item.

    :return: Template to add a new item to any category.
    '''
    if 'username' not in login_session:
        return redirect('/login')
    # Fetch all the categories
    categories = session.query(Category).all()
    if request.method == 'POST':
        newItem = Item(name=request.form['name'], description=request.form['description'],
                       category_id=request.form['category'], image=request.form['image'],
                       user_id=login_session['user_id'])
        newItem.image = getImageUrl(newItem)
        session.add(newItem)
        session.commit()
        flash('New Menu %s Item Successfully Created' % (newItem.name))
        return redirect(url_for('showCatalog'))
    return render_template('newItem.html', categories=categories)


@app.route('/catalog/<string:item_name>/edit', methods=['GET', 'POST'])
def editItem(item_name):
    '''
    Edit a category item. Only a logged in user and the item creator can perform this action.

    :param item_name: The item name.
    :return: Renders html template for editing item.
    '''
    if 'username' not in login_session:
        return redirect('/login')
    item = session.query(Item).filter_by(name=item_name).one()
    categories = session.query(Category).all()
    if request.method == 'POST':
        if request.form['name']:
            item.name = request.form['name']
        if request.form['description']:
            item.description = request.form['description']
        if request.form['image']:
            item.image = request.form['image']
        if request.form['category']:
            item.category_id = request.form['category']
        session.add(item)
        session.commit()
        flash('Item Successfully Edited')
        return redirect(url_for('showCatalog'))
    else:
        return render_template('editItem.html', item=item, categories=categories)


@app.route('/catalog/<string:item_name>/delete', methods=['GET', 'POST'])
def deleteItem(item_name):
    '''
    Delete a menu item. Only a logged in user and the item creator can perform this action.

    :param item_name: The name of the item.
    :return: Renders the html template to delete item.
    '''
    if 'username' not in login_session:
        return redirect('/login')
    item = session.query(Item).filter_by(name=item_name).one()
    if request.method == 'POST':
        session.delete(item)
        session.commit()
        flash('Menu Item Successfully Deleted')
        return redirect(url_for('showCatalog'))
    else:
        return render_template('deleteItem.html', item=item)


@app.route('/catalog/new/', methods=['GET', 'POST'])
def newCategory():
    '''
    Create a new category.

    :return: Renders html template to add new category.
    '''
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newCategory = Category(
                name=request.form['name'], user_id=login_session['user_id'])
        session.add(newCategory)
        flash('New Category %s Successfully Created' % newCategory.name)
        session.commit()
        return redirect(url_for('showCatalog'))
    else:
        return render_template('newCategory.html')


################################################################################
# Main function that starts the server and listens to port 8000.
################################################################################


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
