import unittest
from esurvey import create_app

class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'DATABASE_URL':'sqlite:///:memory:','SECRET_KEY':'test-secret','HOSTED':False})
        self.client=self.app.test_client()
        self.csrf=self.client.get('/api/session').json['csrf']

    def write(self,path,data=None,method='POST',client=None,csrf=None):
        return (client or self.client).open('/api'+path,method=method,json=data or {},headers={'X-CSRF-Token':csrf or self.csrf})

    def register(self,email='owner@example.com'):
        result=self.write('/auth/register',{'name':'Test Owner','business':'Test Restaurant','email':email,'password':'a-long-test-password'})
        self.assertEqual(result.status_code,201,result.json)
        self.csrf=result.json['csrf']
        biz=self.client.get('/api/businesses').json[0]
        data=self.client.get(f'/api/businesses/{biz["id"]}/dashboard').json
        return biz,data['surveys'][0]

    def submit(self,slug,**extra):
        return self.client.post('/api/public/surveys/'+slug+'/responses',json={'rating':2,'category':'Service','comment':'We waited too long for our order.','consent':True,'submission_key':'unique-response-key-0001',**extra})

    def test_complete_feedback_to_report_and_action(self):
        biz,survey=self.register();bid=biz['id']
        result=self.submit(survey['slug']);self.assertEqual(result.status_code,201,result.json)
        data=self.client.get(f'/api/businesses/{bid}/dashboard').json
        self.assertEqual(data['summary']['average'],2)
        self.assertEqual(data['summary']['attention'],1)
        rid=result.json['id']
        self.assertEqual(self.write(f'/businesses/{bid}/reviews/{rid}',{'status':'resolved'},'PATCH').status_code,200)
        self.assertEqual(self.client.get(f'/api/businesses/{bid}/dashboard').json['summary']['attention'],0)
        action=self.write(f'/businesses/{bid}/actions',{'title':'Improve service times','category':'Service','priority':'high'})
        self.assertEqual(action.status_code,201)
        aid=action.json['id']
        self.assertEqual(self.write(f'/businesses/{bid}/actions/{aid}',{'status':'done'},'PATCH').json['status'],'done')
        self.assertEqual(self.write(f'/businesses/{bid}/actions/{aid}',method='DELETE').status_code,200)
        export=self.client.get(f'/api/businesses/{bid}/export')
        self.assertEqual(export.status_code,200)
        self.assertIn('We waited too long',export.text)

    def test_tenant_isolation(self):
        biz,survey=self.register()
        stranger=self.app.test_client();token=stranger.get('/api/session').json['csrf']
        result=self.write('/auth/register',{'name':'Other Owner','business':'Other Restaurant','email':'other@example.com','password':'another-long-password'},client=stranger,csrf=token)
        self.assertEqual(result.status_code,201)
        self.assertEqual(stranger.get(f'/api/businesses/{biz["id"]}/dashboard').status_code,404)
        response=self.write(f'/businesses/{biz["id"]}/surveys/{survey["id"]}',{'title':'Hijacked'},'PATCH',client=stranger,csrf=result.json['csrf'])
        self.assertEqual(response.status_code,404)
        self.assertEqual(stranger.get(f'/api/businesses/{biz["id"]}/export').status_code,404)

    def test_duplicate_and_validation(self):
        _,survey=self.register();slug=survey['slug']
        for invalid in [0,6,True,'5']:
            self.assertEqual(self.submit(slug,rating=invalid).status_code,400)
        self.assertEqual(self.submit(slug,consent=False).status_code,400)
        self.assertEqual(self.submit(slug,category='Invalid').status_code,400)
        self.assertEqual(self.submit(slug,comment='  ').status_code,400)
        self.assertEqual(self.submit(slug,website='spam').status_code,400)
        first=self.submit(slug);second=self.submit(slug)
        self.assertEqual(first.status_code,201)
        self.assertEqual(second.status_code,200)
        self.assertEqual(first.json['id'],second.json['id'])

    def test_paused_survey_and_delete_protection(self):
        biz,survey=self.register();bid=biz['id'];sid=survey['id'];slug=survey['slug']
        self.submit(slug)
        self.assertEqual(self.write(f'/businesses/{bid}/surveys/{sid}',method='DELETE').status_code,409)
        self.write(f'/businesses/{bid}/surveys/{sid}',{'status':'paused'},'PATCH')
        self.assertEqual(self.client.get('/api/public/surveys/'+slug).status_code,410)
        self.assertEqual(self.submit(slug,submission_key='another-unique-key').status_code,410)

    def test_auth_csrf_logout_and_headers(self):
        self.assertEqual(self.client.post('/api/auth/login',json={}).status_code,403)
        self.assertEqual(self.client.get('/api/businesses').status_code,401)
        self.register()
        self.write('/auth/logout')
        self.assertEqual(self.client.get('/api/businesses').status_code,401)
        self.csrf=self.client.get('/api/session').json['csrf']
        self.assertEqual(self.write('/auth/login',{'email':'owner@example.com','password':'wrong-password'}).status_code,401)
        self.assertEqual(self.write('/auth/login',{'email':'owner@example.com','password':'a-long-test-password'}).status_code,200)
        self.assertEqual(self.client.get('/api/session').headers['Cache-Control'],'no-store')
        self.assertIn("frame-ancestors 'none'",self.client.get('/').headers['Content-Security-Policy'])

    def test_filters_and_formula_safe_csv(self):
        biz,survey=self.register();bid=biz['id']
        self.submit(survey['slug'],comment='=HYPERLINK("bad")')
        self.assertEqual(self.client.get(f'/api/businesses/{bid}/dashboard?rating=positive').json['summary']['total'],0)
        self.assertEqual(self.client.get(f'/api/businesses/{bid}/dashboard?category=Service').json['summary']['total'],1)
        self.assertEqual(self.client.get(f'/api/businesses/{bid}/dashboard?q=absent').json['summary']['total'],0)
        self.assertIn("'=HYPERLINK",self.client.get(f'/api/businesses/{bid}/export').text)
        self.assertEqual(self.client.get(f'/api/businesses/{bid}/dashboard?days=invalid').status_code,400)

    def test_survey_crud_and_business_update(self):
        biz,_=self.register();bid=biz['id']
        created=self.write(f'/businesses/{bid}/surveys',{'title':'New survey','description':'Tell us more','categories':['Service']})
        self.assertEqual(created.status_code,201)
        sid=created.json['id']
        self.assertEqual(self.write(f'/businesses/{bid}/surveys/{sid}',{'title':'Updated survey'},'PATCH').json['title'],'Updated survey')
        self.assertEqual(self.write(f'/businesses/{bid}/surveys/{sid}',method='DELETE').status_code,200)
        self.assertEqual(self.write(f'/businesses/{bid}',{'name':'Updated business','industry':'Retail'},'PATCH').json['name'],'Updated business')

    def test_demo_cannot_collect_real_feedback(self):
        data=self.client.get('/api/demo').json
        self.assertGreater(data['summary']['total'],0)
        self.assertEqual(self.submit('demo-dining').status_code,400)

if __name__=='__main__': unittest.main()
