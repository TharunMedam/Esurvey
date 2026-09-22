import pandas as pd

def summarize(reviews):
    if not reviews:
        return dict(total=0, average=0, positive=0, attention=0, categories=[], trend=[], distribution=[0]*5)
    df = pd.DataFrame(reviews)
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    df = df.dropna(subset=['rating'])
    df['date'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d')
    categories = []
    for category, group in df.groupby('category'):
        categories.append(dict(name=category, average=round(float(group.rating.mean()), 1), count=len(group), negative=int((group.rating <= 2).sum())))
    categories.sort(key=lambda x: x['average'])
    daily = df.groupby('date').agg(count=('rating', 'count'), average=('rating', 'mean')).reset_index()
    return dict(total=len(df), average=round(float(df.rating.mean()), 1), positive=round(float((df.rating >= 4).mean()*100)), attention=int(((df.rating <= 2) & (df.status != 'resolved')).sum()), categories=categories, trend=[dict(date=r.date, count=int(r.count), average=round(float(r.average), 2)) for r in daily.itertuples()], distribution=[int((df.rating == i).sum()) for i in range(1, 6)])

def csv_export(reviews):
    columns = ['id', 'created_at', 'rating', 'category', 'comment', 'name', 'status', 'survey_id']
    df = pd.DataFrame(reviews, columns=columns)
    # Prevent spreadsheet formulas from executing when stakeholders open exports.
    for col in ['category', 'comment', 'name', 'status']:
        df[col] = df[col].map(lambda v: "'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else v)
    return '\ufeff' + df.to_csv(index=False)
