import os
import secrets
from datetime import timedelta
from pathlib import Path
from flask import Flask, jsonify, request, session, g, send_from_directory
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv
from .models import Base

def create_app(config=None):
    load_dotenv()
    root = Path(__file__).resolve().parent.parent
    app = Flask(__name__, static_folder=str(root/'public'), static_url_path='')
    hosted = bool(os.environ.get('VERCEL'))
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=hosted, PERMANENT_SESSION_LIFETIME=timedelta(hours=12), MAX_CONTENT_LENGTH=32768, HOSTED=hosted)
    if config:
        app.config.update(config)
    url = app.config.get('DATABASE_URL') or os.environ.get('DATABASE_URL')
    if not url and not hosted:
        url = 'sqlite:///' + str(root/'local.db')
    if url and url.startswith('mysql://'):
        url = url.replace('mysql://', 'mysql+pymysql://', 1)
    app.config['DATABASE_AVAILABLE'] = bool(url) and (not hosted or bool(os.environ.get('SECRET_KEY')))
    if url:
        options = dict(pool_pre_ping=True, pool_recycle=280)
        if url.startswith('mysql') and os.environ.get('DATABASE_SSL', 'true') == 'true':
            options['connect_args'] = {'ssl': {'check_hostname': True}, 'connect_timeout': 10}
        engine = create_engine(url, **options)
        app.extensions['db_factory'] = sessionmaker(engine, expire_on_commit=False)
        app.extensions['engine'] = engine
        if not hosted:
            Base.metadata.create_all(engine)

    @app.before_request
    def before():
        if request.path.startswith('/api/'):
            if request.method in ['POST','PATCH','DELETE'] and not request.path.startswith('/api/public/'):
                expected = session.get('csrf')
                if not expected or not secrets.compare_digest(expected, request.headers.get('X-CSRF-Token', '')):
                    return jsonify(error='Your session expired. Refresh the page and try again.'), 403
            if app.config['DATABASE_AVAILABLE']:
                g.db = app.extensions['db_factory']()

    @app.teardown_request
    def teardown(error):
        if hasattr(g,'db'):
            g.db.close()

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Content-Security-Policy']="default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; font-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        if request.path.startswith('/api/'):
            response.headers['Cache-Control']='no-store'
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(SQLAlchemyError)
    def db_error(error):
        if hasattr(g,'db'): g.db.rollback()
        app.logger.error('Database request failed: %s', type(error).__name__)
        return jsonify(error='The database is temporarily unavailable. Please try again shortly.'), 503

    @app.cli.command('init-db')
    def init_db():
        Base.metadata.create_all(app.extensions['engine'])
        print('Database schema initialized.')

    @app.get('/')
    @app.get('/s/<slug>')
    def index(slug=None):
        return send_from_directory(root/'templates','index.html')

    from .routes import api
    app.register_blueprint(api, url_prefix='/api')
    return app
