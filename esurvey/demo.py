from datetime import timedelta
import random
from .models import now

def demo_data():
    rng = random.Random(28)
    examples = [
        (5, 'Food quality', 'The seasonal menu was incredible. The roasted tomato pasta is worth coming back for.', 'Olivia M.'),
        (2, 'Service', 'We waited 35 minutes before anyone took our order. Lovely food, but the service needs attention.', 'James R.'),
        (4, 'Atmosphere', 'Such a warm, welcoming space. A little noisy near the kitchen, but a lovely evening overall.', 'Sophia K.'),
        (1, 'Value for money', 'Portions have become smaller while prices keep going up. I expected more for the price.', 'Anonymous'),
        (5, 'Service', 'Our server made a birthday dinner feel really special. Thoughtful details throughout.', 'Daniel L.'),
        (3, 'Food quality', 'The mains were great but the fries arrived cold. Please check the food before it leaves the kitchen.', 'Emma W.'),
        (4, 'Value for money', 'The lunch special is excellent value. Would love a vegetarian option in the set menu.', 'Noah T.'),
        (2, 'Service', 'It was difficult to get someone’s attention to pay the bill. More staff at peak hours would help.', 'Ava S.'),
        (5, 'Atmosphere', 'Beautiful lighting and a relaxing atmosphere. Our new favorite neighborhood spot.', 'Isabella P.'),
        (5, 'Food quality', 'Fresh ingredients, thoughtful presentation, and really good coffee.', 'Liam B.'),
    ]
    reviews = []
    for i in range(148):
        rating, category, comment, name = rng.choice(examples)
        reviews.append(dict(id=i+1, business_id=0, survey_id=1 if i % 4 else 2, rating=rating, category=category, comment=comment, name=name, status='resolved' if i % 5 == 0 else 'new', created_at=(now()-timedelta(days=rng.randrange(30), hours=rng.randrange(24))).isoformat()))
    reviews.sort(key=lambda x:x['created_at'], reverse=True)
    return dict(business=dict(id=0, name='The Greenhouse', industry='Restaurant'), surveys=[dict(id=1,title='Your dining experience',slug='demo-dining',description='A few honest words can make a real difference.',categories=['Food quality','Service','Atmosphere','Value for money'],status='active',created_at=now().isoformat()),dict(id=2,title='The weekend brunch',slug='demo-brunch',description='Help us make your next brunch even better.',categories=['Food quality','Service','Atmosphere','Value for money'],status='active',created_at=now().isoformat())], reviews=reviews, actions=[dict(id=1,title='Review weekend staffing levels',category='Service',priority='high',status='in_progress'),dict(id=2,title='Revisit portion sizes and menu pricing',category='Value for money',priority='medium',status='planned'),dict(id=3,title='Add a food temperature check',category='Food quality',priority='medium',status='done')])
