import hashlib
import re
import secrets
from datetime import timedelta
from functools import wraps
from flask import Blueprint, abort, current_app, g, jsonify, request, session, Response
from sqlalchemy import select, delete, update
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Business, Survey, Review, Action, RateLimit, now
from .reporting import summarize, csv_export
from .demo import demo_data

api = Blueprint('api', __name__)

def body():
    data = request.get_json(silent=True)
    if not isinstance(data,dict): abort(400, 'Please send a JSON object.')
    return data

def field(data, key, minimum=1, maximum=150, default=None):
    value=data.get(key, default)
    if not isinstance(value,str) or not minimum <= len(value.strip()) <= maximum:
        abort(400, f'{key.replace("_", " ").capitalize()} must be between {minimum} and {maximum} characters.')
    return value.strip()

def database():
    if not current_app.config['DATABASE_AVAILABLE']:
        abort(503,'Live workspaces are not configured yet. You can explore the sample workspace.')

def auth(fn):
    @wraps(fn)
    def wrapper(*args,**kwargs):
        database()
        if not session.get('user_id'): abort(401,'Please sign in to continue.')
        return fn(*args,**kwargs)
    return wrapper

def business(bid):
    record=g.db.scalar(select(Business).where(Business.id==bid, Business.owner_id==session['user_id']))
    if not record: abort(404,'Business not found.')
    return record

def serialize(row):
    result={c.name:getattr(row,c.name) for c in row.__table__.columns if c.name not in ('password','submission_key','owner_id')}
    if 'created_at' in result: result['created_at']=result['created_at'].isoformat()+'Z'
    return result

def rate_limit(scope, limit):
    # Server-side storage works across serverless instances. Only Vercel's trusted header is used there.
    ip=request.headers.get('x-vercel-forwarded-for',request.remote_addr) if current_app.config['HOSTED'] else request.remote_addr
    bucket=int(now().timestamp())//600
    key=hashlib.sha256(f'{scope}:{ip}:{bucket}'.encode()).hexdigest()
    g.db.execute(delete(RateLimit).where(RateLimit.expires_at < now()))
    try:
        with g.db.begin_nested():
            g.db.add(RateLimit(key=key,count=0,expires_at=now()+timedelta(minutes=11)))
            g.db.flush()
    except IntegrityError:
        pass
    result=g.db.execute(update(RateLimit).where(RateLimit.key==key,RateLimit.count<limit).values(count=RateLimit.count+1))
    g.db.commit()
    if result.rowcount != 1: abort(429,'Too many attempts. Please try again in 10 minutes.')

@api.get('/session')
def get_session():
    session.setdefault('csrf',secrets.token_hex(32))
    user=g.db.get(User,session.get('user_id')) if hasattr(g,'db') and session.get('user_id') else None
    return jsonify(csrf=session['csrf'],user=serialize(user) if user else None,available=current_app.config['DATABASE_AVAILABLE'])

@api.post('/auth/register')
def register():
    database()
    rate_limit('register',10)
    data=body()
    email=field(data,'email',3,254).lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): abort(400,'Enter a valid email address.')
    user=User(name=field(data,'name',2,100),email=email,password=generate_password_hash(field(data,'password',12,128)))
    g.db.add(user)
    try: g.db.flush()
    except IntegrityError:
        g.db.rollback()
        abort(409,'An account with that email already exists. Please sign in.')
    biz=Business(owner_id=user.id,name=field(data,'business',2,120),industry=field(data,'industry',1,60,'Restaurant'))
    g.db.add(biz)
    g.db.flush()
    categories=['Food quality','Service','Atmosphere','Value for money'] if biz.industry=='Restaurant' else ['Product quality','Service','Experience','Value for money']
    g.db.add(Survey(business_id=biz.id,title='Your experience matters',slug=secrets.token_urlsafe(18),categories=categories))
    g.db.commit()
    session.clear()
    session.update(user_id=user.id,csrf=secrets.token_hex(32))
    session.permanent=True
    return jsonify(user=serialize(user),csrf=session['csrf']),201

@api.post('/auth/login')
def login():
    database()
    rate_limit('login',20)
    data=body()
    user=g.db.scalar(select(User).where(User.email==field(data,'email',3,254).lower()))
    password=field(data,'password',1,128)
    if not user or not check_password_hash(user.password,password): abort(401,'Email or password is incorrect.')
    session.clear()
    session.update(user_id=user.id,csrf=secrets.token_hex(32))
    session.permanent=True
    return jsonify(user=serialize(user),csrf=session['csrf'])

@api.post('/auth/logout')
def logout():
    session.clear()
    return jsonify(ok=True)

@api.get('/businesses')
@auth
def businesses():
    return jsonify([serialize(r) for r in g.db.scalars(select(Business).where(Business.owner_id==session['user_id']))])

@api.post('/businesses')
@auth
def create_business():
    data=body()
    row=Business(owner_id=session['user_id'],name=field(data,'name',2,120),industry=field(data,'industry',1,60,'Restaurant'))
    g.db.add(row); g.db.commit()
    return jsonify(serialize(row)),201

@api.patch('/businesses/<int:bid>')
@auth
def update_business(bid):
    row=business(bid); data=body()
    row.name=field(data,'name',2,120)
    row.industry=field(data,'industry',1,60)
    g.db.commit()
    return jsonify(serialize(row))

def filtered(rows):
    days=request.args.get('days','30')
    if days not in ['7','30','90','365','all']: abort(400,'Invalid date range.')
    if days!='all':
        cutoff=(now()-timedelta(days=int(days))).isoformat()
        rows=[r for r in rows if r['created_at']>=cutoff]
    query=request.args.get('q','').strip().lower()[:150]
    category=request.args.get('category','')
    status=request.args.get('status','')
    rating=request.args.get('rating','')
    if rating and rating not in ['1','2','3','4','5','negative','positive']: abort(400,'Invalid rating filter.')
    if query: rows=[r for r in rows if query in (r['comment']+' '+r['name']+' '+r['category']).lower()]
    if category: rows=[r for r in rows if r['category']==category]
    if status: rows=[r for r in rows if r['status']==status]
    if rating=='negative': rows=[r for r in rows if r['rating']<=2]
    elif rating=='positive': rows=[r for r in rows if r['rating']>=4]
    elif rating: rows=[r for r in rows if r['rating']==int(rating)]
    return rows

def dataset(bid):
    biz=business(bid)
    statement=select(Review).where(Review.business_id==bid).order_by(Review.created_at.desc())
    days=request.args.get('days','30')
    if days not in ['7','30','90','365','all']: abort(400,'Invalid date range.')
    if days!='all': statement=statement.where(Review.created_at>=now()-timedelta(days=int(days)))
    return dict(business=serialize(biz),reviews=[serialize(r) for r in g.db.scalars(statement)],surveys=[serialize(r) for r in g.db.scalars(select(Survey).where(Survey.business_id==bid))],actions=[serialize(r) for r in g.db.scalars(select(Action).where(Action.business_id==bid).order_by(Action.created_at.desc()))])

@api.get('/demo')
def demo():
    data=demo_data()
    data['reviews']=filtered(data['reviews'])
    data['summary']=summarize(data['reviews'])
    return jsonify(data)

@api.get('/businesses/<int:bid>/dashboard')
@auth
def dashboard(bid):
    data=dataset(bid)
    data['reviews']=filtered(data['reviews'])
    data['summary']=summarize(data['reviews'])
    return jsonify(data)

@api.get('/demo/export')
def export_demo():
    return Response(csv_export(filtered(demo_data()['reviews'])),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=esurvey-sample-reviews.csv'})

@api.get('/businesses/<int:bid>/export')
@auth
def export(bid):
    return Response(csv_export(filtered(dataset(bid)['reviews'])),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=esurvey-reviews.csv'})

def categories(data):
    values=data.get('categories')
    if not isinstance(values,list) or not 1<=len(values)<=8 or any(not isinstance(x,str) or not 1<=len(x.strip())<=80 for x in values): abort(400,'Choose between 1 and 8 categories, each up to 80 characters.')
    return list(dict.fromkeys(x.strip() for x in values))

@api.post('/businesses/<int:bid>/surveys')
@auth
def create_survey(bid):
    business(bid); data=body()
    row=Survey(business_id=bid,title=field(data,'title',2,150),description=field(data,'description',0,1000,''),categories=categories(data),slug=secrets.token_urlsafe(18))
    g.db.add(row);g.db.commit()
    return jsonify(serialize(row)),201

def owned(model, bid, rid):
    business(bid)
    row=g.db.scalar(select(model).where(model.id==rid,model.business_id==bid))
    if not row: abort(404,'Record not found.')
    return row

@api.patch('/businesses/<int:bid>/surveys/<int:rid>')
@auth
def update_survey(bid,rid):
    row=owned(Survey,bid,rid);data=body()
    if 'title' in data: row.title=field(data,'title',2,150)
    if 'description' in data: row.description=field(data,'description',0,1000)
    if 'categories' in data: row.categories=categories(data)
    if 'status' in data:
        if data['status'] not in ['active','paused']: abort(400,'Invalid survey status.')
        row.status=data['status']
    g.db.commit();return jsonify(serialize(row))

@api.delete('/businesses/<int:bid>/surveys/<int:rid>')
@auth
def delete_survey(bid,rid):
    row=owned(Survey,bid,rid)
    if g.db.scalar(select(Review.id).where(Review.survey_id==rid).limit(1)):
        abort(409,'This survey has responses. Pause it to preserve your reports.')
    g.db.delete(row);g.db.commit();return jsonify(ok=True)

@api.patch('/businesses/<int:bid>/reviews/<int:rid>')
@auth
def review_status(bid,rid):
    row=owned(Review,bid,rid);status=body().get('status')
    if status not in ['new','reviewing','resolved']: abort(400,'Invalid review status.')
    row.status=status;g.db.commit();return jsonify(serialize(row))

@api.post('/businesses/<int:bid>/actions')
@auth
def create_action(bid):
    business(bid);data=body()
    priority=data.get('priority','medium')
    if priority not in ['high','medium','low']: abort(400,'Invalid priority.')
    row=Action(business_id=bid,title=field(data,'title',3,180),category=field(data,'category',1,80),priority=priority)
    g.db.add(row);g.db.commit();return jsonify(serialize(row)),201

@api.patch('/businesses/<int:bid>/actions/<int:rid>')
@auth
def update_action(bid,rid):
    row=owned(Action,bid,rid);data=body()
    if 'title' in data: row.title=field(data,'title',3,180)
    if 'status' in data:
        if data['status'] not in ['planned','in_progress','done']: abort(400,'Invalid action status.')
        row.status=data['status']
    g.db.commit();return jsonify(serialize(row))

@api.delete('/businesses/<int:bid>/actions/<int:rid>')
@auth
def delete_action(bid,rid):
    row=owned(Action,bid,rid);g.db.delete(row);g.db.commit();return jsonify(ok=True)

@api.get('/public/surveys/<slug>')
def public_survey(slug):
    if slug in ['demo-dining','demo-brunch']:
        data=demo_data();row=next(s for s in data['surveys'] if s['slug']==slug)
        return jsonify(**row,business=data['business']['name'],demo=True)
    database()
    row=g.db.scalar(select(Survey).where(Survey.slug==slug))
    if not row: abort(404,'This survey could not be found.')
    if row.status!='active': abort(410,'This survey is not currently accepting feedback.')
    return jsonify(**serialize(row),business=g.db.get(Business,row.business_id).name,demo=False)

@api.post('/public/surveys/<slug>/responses')
def submit(slug):
    if slug in ['demo-dining','demo-brunch']: abort(400,'This is a sample survey. Create a workspace to collect real responses.')
    database()
    data=body()
    if data.get('website'): abort(400,'Unable to accept this response.')
    row=g.db.scalar(select(Survey).where(Survey.slug==slug).with_for_update())
    if not row: abort(404,'Survey not found.')
    if row.status!='active': abort(410,'This survey is not currently accepting feedback.')
    rating=data.get('rating')
    if type(rating) is not int or not 1<=rating<=5: abort(400,'Choose a rating between 1 and 5.')
    category=field(data,'category',1,80)
    if category not in row.categories: abort(400,'Choose a category from this survey.')
    key=field(data,'submission_key',16,64)
    existing=g.db.scalar(select(Review).where(Review.survey_id==row.id,Review.submission_key==key))
    if existing: return jsonify(ok=True,id=existing.id),200
    comment=field(data,'comment',5,3000)
    name=field(data,'name',0,100,'') or 'Anonymous'
    if data.get('consent') is not True: abort(400,'Please consent to sharing your feedback with this business.')
    survey_id,bid=row.id,row.business_id
    rate_limit('submit:'+slug,15)
    # Recheck after committing the rate-limit transaction.
    row=g.db.scalar(select(Survey).where(Survey.id==survey_id).with_for_update().execution_options(populate_existing=True))
    if row.status!='active': abort(410,'This survey is not currently accepting feedback.')
    review=Review(business_id=bid,survey_id=survey_id,rating=rating,category=category,comment=comment,name=name,submission_key=key)
    g.db.add(review)
    try: g.db.commit()
    except IntegrityError:
        g.db.rollback()
        existing=g.db.scalar(select(Review).where(Review.survey_id==survey_id,Review.submission_key==key))
        if existing: return jsonify(ok=True,id=existing.id),200
        raise
    return jsonify(ok=True,id=review.id),201

@api.get('/health')
def health():
    return jsonify(status='ok',database_configured=current_app.config['DATABASE_AVAILABLE'])
