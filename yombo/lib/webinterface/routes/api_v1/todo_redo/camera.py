# Import python libraries
from twisted.internet.defer import inlineCallbacks

from yombo.constants.permissions import AUTH_PLATFORM_DEVICE
from yombo.lib.webinterface.auth import get_session
from yombo.lib.webinterface.routes.api_v1.__init__ import return_not_found, request_args
from yombo.utils import sleep


def route_api_v1_camera(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route("/camera/<string:device_id>/mjpeg", methods=["GET"])
        @get_session(auth_required=True, api=True)
        @inlineCallbacks
        def apiv1_camera_mjpeg_get(webinterface, request, session, device_id):
            webinterface._Validate.id_string(device_id)
            session.is_allowed(AUTH_PLATFORM_DEVICE, "view", device_id)
            # print(f"auth_type: {session.auth_type}, auth_id: {session.auth.auth_id}")

            if device_id in webinterface._Devices:
                device = webinterface._Devices[device_id]
            else:
                return return_not_found(request, "Device not found")

            arguments = request_args(webinterface, request)
            # print(f"arguments: {arguments}")

            try:
                framerate = int(arguments["framerate"])
            except:
                framerate = 5

            try:
                quality = int(arguments["quality"])
            except:
                quality = 4

            def write_to_http_mjpeg_stream(image, *args, **kwargs):
                """
                Takes an image instance and writes it to the HTTP request instance.
                """
                # print("write_to_mpeg_stream: request: %s" % request)
                # print("write_to_mpeg_stream: image: %s" % image)
                request.write(bytes(
                    '--frameboundary\r\n'
                    f'Content-Type: {image.content_type}\r\n'
                    f'Content-Length: {len(image.content)}\r\n\r\n',
                    'utf-8') + image.content + b'\r\n')

            request.setHeader("Content-Type", "multipart/x-mixed-replace; boundary=--frameboundary")

            # print("final framerate: %s - %s" % (framerate, type(framerate)))
            # print("about to stream from: %s" % device.PLATFORM)
            yield device.stream_http_mjpeg_video(image_callback=write_to_http_mjpeg_stream,
                                                 framerate=framerate,
                                                 quality=quality)

        @webapp.route("/camera/<string:device_id>/h264", methods=["GET"])
        @get_session(auth_required=True, api=True)
        @inlineCallbacks
        def apiv1_camera_h264_get(webinterface, request, session, device_id):
            webinterface._Validate.id_string(device_id)
            session.is_allowed(AUTH_PLATFORM_DEVICE, "view", device_id)
            # print(f"auth_type: {session.auth_type}, auth_id: {session.auth.auth_id}")

            if device_id in webinterface._Devices:
                device = webinterface._Devices[device_id]
            else:
                return return_not_found(request, "Device not found")

            arguments = request_args(webinterface, request)
            # print(f"arguments: {arguments}")

            try:
                framerate = int(arguments["framerate"])
            except:
                framerate = 5

            try:
                video_bitrate = int(arguments["video_bitrate"])
            except:
                video_bitrate = 768

            try:
                video_profile = int(arguments["video_profile"])
            except:
                video_profile = "baseline"

            def write_to_http_h264_stream(stream_data, *args, **kwargs):
                """
                Takes a video stream from FFMPEG and spits it out to the client.
                """
                nonlocal request
                print("write_to_http_h264_stream: data size:: %s" % len(stream_data))
                # print("write_to_mpeg_stream: image: %s" % image)
                request.write(bytes(stream_data))

            request.setHeader("Content-Type", "video/mp4")

            print("final framerate: %s - %s" % (framerate, type(framerate)))
            print("about to stream from: %s" % device.PLATFORM)
            yield device.stream_http_264_video(stream_callback=write_to_http_h264_stream,
                                               video_bitrate=video_bitrate,
                                               video_profile=video_profile)
            print("I'm finished streaming......")


