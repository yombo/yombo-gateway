# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found, return_error, return_unauthorized
from yombo.constants import CONTENT_TYPE_JSON
from yombo.utils.converters import epoch_to_string

def route_api_v1_statistics(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route('/statistics/names', methods=['GET'])
        @require_auth(api=True)
        @inlineCallbacks
        def apiv1_statistics_names(webinterface, request, session):
            session.has_access('statistic', '*', 'view', raise_error=True)
            records = yield webinterface._Libraries['localdb'].get_distinct_stat_names()
            request.setHeader('Content-Type', CONTENT_TYPE_JSON)
            return json.dumps(records)

        @webapp.route('/statistics/echarts/buckets', methods=['GET', 'POST'])
        @require_auth(api=True)
        @inlineCallbacks
        def apiv1_statistics_echarts_buckets(webinterface, request, session):

            session.has_access('statistic', '*', 'view', raise_error=True)
            requested_stats = []

            chart_label = request.args.get('chart_label', ['Unlabeled', ])[0]
            time_last = request.args.get('last', [1209600, ])[0]
            time_start = request.args.get('start', [None, ])[0]
            time_end = request.args.get('end', [None, ])[0]
            stat_chart_type = request.args.get('stat_chart_type', [None, ])
            stat_chart_label = request.args.get('stat_chart_label', [None, ])
            stat_type = request.args.get('stat_type', [None, ])
            stat_name = request.args.get('stat_name', [None, ])
            bucket_size = request.args.get('bucket_size', [3600, ])

            try:
                if time_start is not None:
                    try:
                        time_start = int(time_start)
                    except Exception as e:
                        return return_error(request, "'time_start' must be an int and must be greater than 0")
                    if time_start < 0:
                        return return_error(request, "'time_start' must be an int and must be greater than 0")
                    my_time_start = time_start
                else:
                    my_time_start = 0
            except Exception as e:
                my_time_start = None

            try:
                if time_last is not None:
                    time_last = int(time_last)
                    if time_last < 0:
                        return return_error(request, "'time_last' must be an int and must be greater than 0.")
                    my_time_start = int(time()) - time_last
            except Exception as e:
                pass

            if my_time_start is None:
                return return_error(request, "'time_start' not included for stat: %s" % stat_name[idx])

            try:
                if time_end is not None:
                    if not isinstance(time_end, int) or time_end < 0:
                        return return_error(request, "'time_end' must be an int and must be greater than 0")
                    my_time_end = time_end
                else:
                    my_time_end = time()
            except Exception as e:
                return return_error(request, "'time_end' not included for stat: %s" % stat_name[idx])

            for idx, item in enumerate(stat_name):
                # print(" checking: %s - %s" % (idx, item))
                if item is None:
                    break

                if stat_name[idx] is None:
                    return return_error(request, "'stat_name' is required.")
                if not isinstance(stat_name[idx], str):
                    return return_error(request, "'stat_name' Must be a string. Got: %s" % stat_name)
                my_stat_name = stat_name[idx]

                try:
                    if stat_type[idx] is not None:
                        if isinstance(stat_type[idx], str) is False:
                            return return_error(request, "'stat_type' Must be a string")
                        if stat_type[idx] not in ('counter', 'datapoint', 'average'):
                            return return_error(request, "'stat_type' must be either: 'counter', 'datapoint', or 'average'")
                        my_stat_type = stat_type[idx]
                    else:
                        my_stat_type = None
                        # return return_error(request, "'stat_type' is None, must be either: 'counter', 'datapoint', or 'average'")
                except Exception as e:
                    my_stat_type = None
                    # return return_error(request, "'stat_type' not included for stat: %s" % stat_name[idx])

                try:
                    if stat_chart_type[idx] is not None:
                        if isinstance(stat_chart_type[idx], str) is False:
                            return return_error(request, "'stat_chart_type' Must be a string, got: %s" % type(stat_chart_type[idx]))
                        if stat_chart_type[idx] not in ('bar', 'line'):
                            return return_error(request, "'stat_chart_type' must be either: 'bar' or 'line'")
                        my_stat_chart_type = stat_chart_type[idx]
                    else:
                        my_stat_chart_type = 'bar'
                except Exception as e:
                    my_stat_chart_type = 'bar'

                try:
                    if stat_chart_label[idx] is not None:
                        if isinstance(stat_chart_label[idx], str) is False:
                            return return_error(request, "'stat_chart_label' Must be a string")
                        my_stat_chart_label = stat_chart_type[idx]
                    else:
                        my_stat_chart_label = my_stat_name
                except Exception as e:
                    my_stat_chart_label = my_stat_name

                try:
                    if bucket_size[idx] is not None:
                        try:
                            bucket_size[idx] = int(bucket_size[idx])
                        except Exception as e:
                            return return_error(request, "'bucket_size' must be an int and must be greater than 0")

                        if bucket_size[idx] < 0:
                            return return_error(request, "'bucket_size' must be an int and must be greater than 0")
                        if bucket_size[idx] < 0:
                            return return_error(request, "'bucket_size' must be an int and must be greater than 0.")
                        my_bucket_size = int(bucket_size[idx])
                    else:
                        my_bucket_size = 900
                except Exception as e:
                    my_bucket_size = 900

                records = yield webinterface._Libraries['localdb'].get_stats_sums(my_stat_name,
                                                                                  bucket_size=my_bucket_size,
                                                                                  bucket_type=my_stat_type,
                                                                                  time_start=my_time_start,
                                                                                  time_end=my_time_end,
                                                                                  )

                labels = []
                data = []
                live_stats = webinterface._Statistics.get_stat(my_stat_name, my_stat_type)

                for record in records:
                    labels.append(epoch_to_string(record['bucket'], '%Y/%-m/%-d %H:%M'))
                    data.append(record['value'])

                for record in live_stats:
                    labels.append(epoch_to_string(record['bucket'], '%Y/%-m/%-d %H:%M'))
                    data.append(record['value'])

                requested_stats.append({
                    'name': my_stat_chart_label,
                    'type': my_stat_chart_type,
                    'data': data,
                })

            if len(requested_stats) == 0:
                return return_error(request, "Not enough valid requested stats.")

            results = {
                'title': {'text': chart_label},
                'toolbox': {
                    'show': 'true',
                    'feature': {
                        'dataZoom': {
                            'show': 'true',
                            'title': {
                                'zoom': 'Select Zoom',
                                'back': 'Reset Zoom'
                            },
                        },
                        'dataView': {
                            'show': 'true',
                            'title': 'View',
                            'lang': ['View', 'Cancel', 'Save']
                        },
                        'restore': {
                            'show': 'true',
                            'title': 'Restore'
                        },
                        'saveAsImage': {
                            'show': 'true',
                            'title': 'Save as image',
                            'type': 'png',
                            'lang': ['Save as image']
                        },
                    },
                },
                'dataZoom': {
                    'show': 'true',
                },

                'tooltip': {'show': 'true'},
                'legend': {'data': ['Legend here']},
                'xAxis': [{'type': 'category', 'data': labels}],
                'yAxis': [{'type': 'value'}], 'series': requested_stats,

            }

            request.setHeader('Content-Type', CONTENT_TYPE_JSON)
            return json.dumps(results)