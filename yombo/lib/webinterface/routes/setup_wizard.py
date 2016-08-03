from klein import Klein

# webapp_local = Klein()
#
# def test_get_routes(WI, webapp):
#     @webapp.route('/setup_wizard', branch=True)
#     def branch_to_setup_wizard(WI, request):
#         print "self: %s" % WI
#         print "request: %s" % request
#         return webapp_local.resource()
#
# @webapp_local.route('/1', **{'test':'zxcv'})
# def page_setup_wizard_1(suppp, request):
#     print "supp: %s" % suppp
#     print "page_setup_wizard_1"
#     self.WI.sessions.set(request, 'login_redirect', '/setup_wizard/2')
#     auth = self.require_auth_pin(request)
#     if auth is not None:
#         return auth
#
#     page = self.get_template(request, self._dir + 'pages/setup_wizard/1.html')
#     return page.render(alerts={},
#                        data=self.data,
#                        )

webapp_local = Klein()

class setup_wizard():


    simulate_gw = {
                  'xyz1':{
                      'label': 'Home',
                      'description': 'Main house gateway',
                      'variables': {
                          'elevation': 800,
                          'latitude': -121,
                          'longitude': 30
                          }
                      },
                  'abc2':{
                      'label': 'Garage',
                      'description': 'The garage',
                      'variables': {
                          'elevation': 805,
                          'latitude': -121,
                          'longitude': 30
                          }
                      },
                  'mno3':{
                      'label': 'Shed',
                      'description': 'In the shed!',
                      'variables': {
                          'elevation': 800,
                          'latitude': -121,
                          'longitude': 30
                          }
                      },
                  }

    def __init__(self, WebInterface):
        self.WI = WebInterface
        pass

    def get_routes(self, webapp):
        @webapp.route('/setup_wizard', branch=True)
        def branch_to_setup_wizard(WI, request):
            print "self: %s" % self
            print "request: %s" % request
            return webapp_local.resource()

