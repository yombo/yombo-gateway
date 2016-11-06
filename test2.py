import inspect

class mytest(object):

    callers = {}
    called_count = [0]

    def make_decorators():
        # Mutable shared storage...
        callers = {}
        called_count = [0]

        def callee_decorator(callee):
    #        callee_L.append(callee)
            def counting_callee(*args, **kwargs):
                current_frame = inspect.currentframe()
                caller_name = inspect.getouterframes(current_frame)[1][3]
                if caller_name in callers:
                    callers[caller_name] = callers[caller_name] + 1
                else:
                    callers[caller_name]  = 1
                called_count[0] += 1
                print "function name: %s " % callee.func_name
                print "count: %s" % callers[caller_name]
                return callee(*args, **kwargs)
            return counting_callee

        def print_information():
            print "called_count: %s" % callers

        return callee_decorator, print_information

    callee_decorator, print_information = make_decorators()

    @callee_decorator
    def bar(self):
        print "in bar..."
        foobar = 'some result other than the call count that you might use'
        return foobar


testit = mytest()

testit.bar()
testit.bar()
testit.print_information()

