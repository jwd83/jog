#!/usr/bin/env pypy

# flask imports
from flask import abort
from flask import flash
from flask import Flask
from flask import g
from flask import Markup
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for

# markdown imports
import markdown

# standard imports
import sqlite3
import time
import uuid
import os

# configuration
PUBLIC_URL_BASE = 'http://nginx.jwd.me'
DATABASE = 'jog.db'
DEBUG = True
if "JOG_SECRET_KEY" in os.environ:
    SECRET_KEY = JOG_SECRET_KEY
else:
    SECRET_KEY = 'DEFAULT_SECRET_KEY'
USERNAME = 'admin'
PASSWORD = 'default'

# initiate flask
app = Flask(
    __name__,
    static_folder='static',
    static_url_path='/static'
)
app.config.from_object(__name__)
app.config.from_envvar('JOG_SETTINGS', silent=True)

# check that the database exists
if not os.path.isfile(app.config['DATABASE']):
    sys.exit('Database: %s not found' % app.config['DATABASE'])

# database routines
def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

# create routes
@app.route("/")
def index():
    cur = g.db.execute('SELECT title, body, id, date_created FROM posts ORDER BY id desc')
    entries = [
        dict(
            title = row[0],
            body = Markup(markdown.markdown(row[1])),
            id = row[2],
            date_created = time.ctime(row[3])
        )
        for row in cur.fetchall()
    ]
    return render_template('index.html', entries=entries)

@app.route('/post/<int:post_id>')
def show_post(post_id):
    cur = g.db.execute('SELECT title, body, id, date_created FROM posts WHERE id = ?', [str(post_id)])
    row = cur.fetchone()
    entry = dict(
        title = row[0],
        body = Markup(markdown.markdown(row[1])),
        id = row[2],
        date_created = time.ctime(row[3])
    )
    return render_template('post.html', entry=entry, puburl = PUBLIC_URL_BASE + '/post/' + str(entry['id']))

@app.route('/edit/<int:post_id>')
def edit_post(post_id):
    if not session.get('logged_in'):
        flash('You must login before editing a post.')
        return redirect(url_for('index'))
    cur = g.db.execute('SELECT title, body, id, date_created FROM posts WHERE id = ?', str(post_id))
    row = cur.fetchone()
    entry = dict(
        title = row[0],
        body = row[1],
        id = row[2],
        date_created = row[3]
    )
    return render_template('edit.html', entry=entry)

@app.route('/edit_submit', methods=['POST'])
def edit_submit():
    if not session.get('logged_in'):
        flash('You must login before submitting an edited post.')
        return redirect(url_for('index'))
    g.db.execute(
        'UPDATE posts SET title = ?, body = ? WHERE id = ?', [
            request.form['title'],
            request.form['body'],
            request.form['id']
        ]
    )
    g.db.commit()
    flash('Your edit has been submitted.')
    return redirect(url_for('show_post', post_id = int(request.form['id'])))

@app.route("/delete")
def delete_post():
    if not session.get('logged_in'):
        flash('You must login before deleting a post.')
        return redirect(url_for('index'))

@app.route("/create")
def create_post():
    if not session.get('logged_in'):
        flash('You must login before posting.')
        return redirect(url_for('index'))
    return render_template('create.html')


@app.route('/add', methods=['POST'])
def add_post():
    if not session.get('logged_in'):
        abort(401)
    g.db.execute(
        'INSERT INTO posts (title, body, date_created) VALUES (?, ?, ?)', [
            request.form['title'],
            request.form['body'],
            int(time.time())
        ]
    )
    g.db.commit()
    flash('New post was successfully created.')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('index'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('index'))

# run application
if __name__ == "__main__":
    app.run()
