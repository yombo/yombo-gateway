# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

Core FFMPEG tools.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
import shlex

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.utils import getProcessOutput

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

logger = get_logger("utils.ffmpeg.ffmpeg")


class YBOFFmpeg(object):
    """
    Core FFMPEG handler.
    """

    def __init__(self, parent, stdout_callback=None, errout_callback=None, connected_callback=None,
                 closed_callback=None, stdout_callback_arguments=None, errout_callback_arguments=None, **kwargs):
        self._Parent = parent
        self.connected_callback = connected_callback
        self.closed_callback = closed_callback
        self.stdout_callback = stdout_callback
        self.errout_callback = errout_callback

        if isinstance(stdout_callback_arguments, dict):
            self.stdout_callback_arguments = stdout_callback_arguments
        else:
            self.stdout_callback_arguments = {}

        if isinstance(errout_callback_arguments, dict):
            self.errout_callback_arguments = errout_callback_arguments
        else:
            self.errout_callback_arguments = {}

        self._argv = None
        self._protocol = None

        self.input_source = None
        self.commands = None
        self.output = None
        self.extra_cmd = None
        self.is_starting = False

        # Reconnection items.
        self.continue_trying = True
        self.max_delay = kwargs.get("max_delay") or 60
        self.initial_delay = 0.4
        self.backoff_factor = 1.4
        self.delay = self.initial_delay
        self.retries = 0
        self.max_retries = None
        self.retry_calllater = None
        self.connector = None
        self.clock = None

        try:
            self.ffmpeg_bin = self._Parent._Atoms.get("ffmpeg_bin")
        except KeyError:
            self.ffmpeg_bin = None
            raise YomboWarning(
                "ffmpeg was not found, check that ffmpeg is installed and accessible from your path environment variable.")

    def _generate_ffmpeg_cmd(self, input_source, commands, extra_cmd, output):
        """
        Create the FFMPEG command.
        Generate ffmpeg command line.
        """
        if self.ffmpeg_bin is None:
            raise YomboWarning(
                "ffmpeg was not found, check that ffmpeg is installed and accessible from your path environment variable.")
        self._argv = [self.ffmpeg_bin]

        # add -i input_source
        self._add_input(input_source)
        self._argv.extend(commands)

        # extra commands might be tagged on after initial call
        if extra_cmd is not None:
            self._argv.extend(shlex.split(extra_cmd))

        self._merge_filters()
        self._add_output(output)

    def _add_input(self, input_source):
        """
        Set the input for ffmpeg command. Appends -i if there's only one input value.
        """
        input_cmd = shlex.split(str(input_source))
        if len(input_cmd) > 1:
            self._argv.extend(input_cmd)
        else:
            self._argv.extend(['-i', input_source])

    def _add_output(self, output):
        """
        Set the output. By default, sets no file and tells ffmpeg to stream it's output.
        """
        if output is None:
            self._argv.extend(['-f', 'null', '-'])
            return

        output_cmd = shlex.split(str(output))
        if len(output_cmd) > 1:
            self._argv.extend(output_cmd)
        else:
            self._argv.append(output)

    def _merge_filters(self):
        """
        Merge various filters config in command line.
        """
        for opts in (['-filter:a', '-af'], ['-filter:v', '-vf']):
            filter_list = []
            new_argv = []
            cmd_iter = iter(self._argv)
            for element in cmd_iter:
                if element in opts:
                    filter_list.insert(0, next(cmd_iter))
                else:
                    new_argv.append(element)

            # update argv if changes
            if filter_list:
                new_argv.extend([opts[0], ",".join(filter_list)])
                self._argv = new_argv.copy()

    @inlineCallbacks
    def open(self, input_source, commands, output=None, extra_cmd=None, auto_reconnect=None):
        """
        Starts the ffmpeg process and setups various callbacks.

        :param input_source:
        :param commands:
        :param output:
        :param extra_cmd:
        :param auto_reconnect: Set to True to automatically reconnect. Used for sensors and various streaming videos.
        :return:
        """
        if auto_reconnect is None:
            auto_reconnect = True
        self.continue_trying = auto_reconnect
        self.delay = self.initial_delay
        self.input_source = input_source
        self.commands = commands
        self.output = output
        self.extra_cmd = extra_cmd

        results = yield self.start()
        return results

    @inlineCallbacks
    def start(self):
        """
        An internal function. Start the actual ffmpeg process. Called by open() and restart().
        :return:
        """
        if self.is_starting:
            logger.info("ffmpeg can't start, already trying..")
            return
        self.is_starting = True
        if self.is_running:
            self.close()

        self._generate_ffmpeg_cmd(self.input_source, self.commands, self.extra_cmd, self.output)
        self._protocol = FFMPEGSubprocessProtocol(self)

        # port_open = True  # Incase we aren't actually using network devices.
        # try:
        #     port_open = test_url_listening(self.input_source)
        # except SyntaxError:  # We don't always deal with network devices, it's ok.
        #     pass
        # if port_open is False:
        #     raise YomboWarning("Appears the port")

        logger.debug("FFMPEG:starting ffmpeg process: {args}", args=" ".join(self._argv))

        try:
            yield reactor.spawnProcess(self._protocol, self._argv[0], self._argv)
        # pylint: disable=broad-except
        except Exception as err:
            self.continue_trying = False
            logger.warn(f"ERROR: YBOFFmpeg failed to start: {err}")
            self.close()
            return False

        self.is_starting = False
        return True

    @inlineCallbacks
    def restart(self):
        """
        Restart the ffmpeg process.
        :return:
        """
        self.close()
        yield self.start()

    def close(self):
        """
        Stop the ffmpeg app...
        """
        self.continue_trying = False
        if self.retry_calllater:
            self.retry_calllater.cancel()
            self.retry_calllater = None

        if self.is_running:
            self._protocol.close()

        self._argv = None
        self._protocol = None

    def process_ended(self):
        """
        Monitors the process. If it ends, and it's not been requested to end, then reconnect.
        :return:
        """
        if self.closed_callback is not None:
            self.closed_callback(continue_trying=self.continue_trying)
        if self.continue_trying:
            self.retry()

    def retry(self):
        """
        When the connection drops, come here and try to reconnect.
        """
        if not self.continue_trying:
            return
        if self.retry_calllater is not None and self.retry_calllater.active():
            return

        self.retries += 1
        if self.max_retries is not None and (self.retries > self.max_retries):
            return

        self.delay = min(self.delay * self.backoff_factor, self.max_delay)

        self.retry_calllater = reactor.callLater(self.delay, self.start)

    def reset_delay(self):
        """
        This method should be called after a successful connection to reset the delay and retry counter.
        """
        # print(f"FFMPEG: reset delay")
        self.delay = self.initial_delay
        self.retries = 0
        self.retry_calllater = None

    @property
    def is_running(self):
        """Return True if ffmpeg is running."""
        if self._protocol is None or self._protocol.running is not True:
            return False
        return True

    @inlineCallbacks
    def _detect_video_type(self):
        """
        Attempt to detect the video type.

        :return:
        """
        self.detected_type = None
        args = [
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "default=nw=1",
            self.video_url,
        ]
        results = yield getProcessOutput(self.ffprobe_bin, args)
        results = results.decode("utf-8")
        parts = results.split("=")
        if parts[0] == "codec_name":
            self.detected_type = parts[1].strip()
        else:
            raise YomboWarning("Unable to detect video type.")


class FFMPEGSubprocessProtocol(ProcessProtocol):

    def __init__(self, parent):
        self._Parent = parent
        self.connected_callback = self._Parent.connected_callback
        self.stdout_callback = self._Parent.stdout_callback
        self.errout_callback = self._Parent.errout_callback
        self.stdout_callback_arguments = self._Parent.stdout_callback_arguments
        self.errout_callback_arguments = self._Parent.errout_callback_arguments

        self.called_stopped_callback = False
        self.running = False
        self.startup_deferred = Deferred()
        self.pid = None

        self.connection_good_delay_calllater = 10
        self.connection_good_delay_calllater_calllater = None

    def close(self):
        """
        Stop the process.

        :return:
        """
        # print("FFMPEG:SubprocessProtocol::close: pid: {self.pid}")
        self.transport.loseConnection()
        self.transport.signalProcess('INT')

    def outReceived(self, output):
        # print(f"FFMPEG:SubprocessProtocol::outReceived: pid: {self.pid}")
        # print(f"out: {output}")
        if callable(self.stdout_callback):
            return self.stdout_callback(output, **self.stdout_callback_arguments)

    def errReceived(self, output):
        # print(f"FFMPEG:SubprocessProtocol::errReceived: pid: {self.pid}")
        # print(f"err: {output}")
        if callable(self.errout_callback):
            # print(f"FFMPEG:SubprocessProtocol::output: {output}")
            return self.errout_callback(output, **self.errout_callback_arguments)

    def connectionMade(self):
        self.pid = self.transport.pid
        # print(f"FFMPEG:SubprocessProtocol::connectionMade: pid: {self.pid}")
        self.running = True

        if self.startup_deferred is not None and self.startup_deferred.called is False:
            self.startup_deferred.callback(self.pid)

        if self.connected_callback is not None:
            self.connected_callback()

        self.connection_good_delay_calllater_calllater = reactor.callLater(
            self.connection_good_delay_calllater, self._Parent.reset_delay)

    def stopped(self):
        """
        The process has stopped.

        :return:
        """
        # print(f"FFMPEG:SubprocessProtocol::stopped")
        if self.called_stopped_callback is False:
            self.called_stopped_callback = True
            self.running = False
            if self.connection_good_delay_calllater_calllater is not None and \
                    self.connection_good_delay_calllater_calllater.active():
                self.connection_good_delay_calllater_calllater.cancel()
            reactor.callLater(0.00001, self._Parent.process_ended)

    def processEnded(self, reason):
        # print(f"FFMPEG:SubprocessProtocol::processEnded: pid: {self.pid}")
        self.stopped()

    def processExited(self, status):
        # print(f"FFMPEG:SubprocessProtocol::processExited: pid: {self.pid}")
        self.stopped()
