# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Files @ Library Documentation <https://yombo.net/docs/libraries/files>`_

Various helpers for working with files.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/files/__init__.html>`_
"""
import sys

import errno
from functools import reduce
import glob
from pathlib import Path
import os
import os.path
from pyclbr import readmodule
import shutil
from time import time
import traceback
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
import yombo.ext.magic as magicfile

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.lib.files.read_stream import ReadStream
from yombo.lib.files.save_stream import SaveStream
from yombo.utils import bytes_to_unicode

logger = get_logger("library.files")


class Files(YomboLibrary):
    """
    Various tools to work with files, this includes streaming to/from files.
    """
    @inlineCallbacks
    def _init_(self, **kwargs):
        self.magicparse = magicfile.Magic(mime_encoding=True, mime=True)

        self.start_tracking = yield self._SQLDicts.get(self, "files_tracking")

        for key in self.start_tracking.keys():  # Delete trackers older than 90 days.
            if self.start_tracking[key]["last_accessed"] < int(time) - 7776000:
                logger.debug("deleting tracking: {key}", key=self.start_tracking[key])
                del self.start_tracking[key]

    ##################################
    # Various reading/writing files. #
    ##################################

    @inlineCallbacks
    def read(self, filename: str, convert_to_unicode: Optional[bool] = None, unpickle: Optional[str] = None):
        """
        Reads a file in a non-blocking method and returns a deferred.

        :param filename:
        :param convert_to_unicode: If True, converts the read file from bytes to unicode (string).
        :param unpickle: If string is set, run through self._Tools.data_unpickle(unpickle)
        :return:
        """
        def _read(read_filename):
            f = open(read_filename, "r")
            data = f.read()
            f.close()
            return data

        contents = yield threads.deferToThread(_read, filename)
        if convert_to_unicode is True:
            contents = bytes_to_unicode(contents)
        if unpickle is not None:
            contents = self._Tools.data_unpickle(contents, "json")

        return contents

    @inlineCallbacks
    def read_stream(self, filename: str, callback: Callable, file_id: Optional[str] = None,
                    encoding: Optional[str] = None, create_if_missing: Optional[bool] = None,
                    frequency: Optional[int] = None):
        """
        Reads a file in a non-blocking method and returns a deferred.

        :param filename: The full path to the file to stream from.
        :param callback: Callback to call when new data is available.
        :param file_id: A persistent tracking ID if reloads should skip to previous read position.
        :param encoding: If using text, specify the encoding - default: utf-8
        :param create_if_missing: If true, will create an empty file if file doesn't
            already exist.  Default: True
        :param frequency: How often, in seconds, to check for new content. Default: 1
        :return:
        """
        if filename is None or filename == "":
            raise YomboWarning("read_stream requires a file name to read from,", 652321, "read_stream", "Files")
        if filename.startswith("/") is False:
            filename = f"./{filename}"
        encoding = encoding or "utf-8"
        create_if_missing = create_if_missing or True
        frequency = frequency or 1

        exists = yield self.exists(filename, encoding)
        if exists is False:
            raise YomboWarning(f"read_stream cannot find the requested file to open for monitoring: {filename}",
                               423215, "read_stream", "Files")

        file_id_hash = None
        if file_id is not None:
            file_id_hash = self._Hash.sha224_compact(file_id)
            if file_id in self.start_tracking:
                file_info = self.start_tracking[file_id_hash]
                file_info["last_accessed"] = int(time())
                file_size = yield self.size(filename)
                if file_size < file_info["start"]:
                    file_info["start"] = 0
            else:
                file_info = {
                    "start": 0,
                    "last_accessed": int(time())
                }
        start_location = file_info["start"]
        monitored_file = ReadStream(self, filename, callback, file_id_hash, start_location, encoding, frequency)
        return monitored_file

    def read_stream_location(self, file_id_hash: Optional[str], start_location: int):
        """
        Set's the start location for the provided file_id_hash, this is called by the ReadStream class.

        :param file_id_hash:
        :param start_location:
        :return:
        """
        if file_id_hash is not None and self.start_tracking[file_id_hash]["start"] != start_location:
            self.start_tracking[file_id_hash]["start"] = start_location

    @inlineCallbacks
    def save(self, filename: str, content, mode: Optional[str] = None):
        """
        Saves contents to a file in a non-blocking method and returns a deferred. The default mode is "w" to
        overwrite the contents, set mode to "a" to append.

        This shouldn't be used to save really large files, instead, use save_stream to save a file in chunks.

        :param filename: Full path to save to.
        :param content: Content to save.
        :param mode: File open mode, default to "w".
        :return:
        """
        def _save(file, data, file_mode):
            if not os.path.exists(os.path.dirname(file)):
                try:
                    os.makedirs(os.path.dirname(file))
                except OSError as exc:  # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise IOError(f"Unable to save file: {exc}")
            if file_mode is None:
                if isinstance(data, bytes):
                    file_mode = "wb"
                else:
                    file_mode = "w"
            file = open(file, file_mode)
            file.write(data)
            file.close()

        yield threads.deferToThread(_save, filename, content, mode)

    @inlineCallbacks
    def save_stream(self, filename: str, mode: Optional[str] = None, create_if_missing: Optional[bool] = None,
                    frequency: Optional[int] = None):
        """
        Saves a file in a non-blocking method and returns a deferred.

        .. code-block:: python

           class MyModule(YomboModule):
               @inlineCallbacks
               def _start_(self):
                   self.file = yield self._Files.save_stream(filename="myfile.txt")
                   self.file.write("some more text....")

               @inlineCallbacks  # <----  This is required as it saves contents in a different thread.
               def _stop_(self):
                   yield self.file.close()  # Tell save_stream to close the file. Very important!

        :param filename: The full path to the file to stream from.
        :param mode: The mode use to for writing, default is "a". Use "w" to overwrite.
        :param create_if_missing: If true, will create an empty file if file doesn't
            already exist.  Default: True
        :param frequency: How often, in seconds, to check for new content. Default: 1
        :return:
        """
        if filename is None or filename == "":
            raise YomboWarning("save_stream requires a file name to read from,", 652321, "save_stream", "Files")
        if filename.startswith("/") is False:
            filename = f"./{filename}"

        create_if_missing = create_if_missing or True
        frequency = frequency or 1

        exists = yield self.exists(filename, create_if_missing)
        if exists is False:
            raise YomboWarning(f"save_stream cannot find the requested file to open for saving: {filename}",
                               423215, "save_stream", "Files")

        save_file = SaveStream(self, filename, mode, frequency)
        return save_file

    #########################
    # Basic file operations #
    #########################

    @inlineCallbacks
    def chmod(self, filename: str, mode: int) -> None:
        """
        Uses os.chmod to set the mode of a file in a non-blocking manor.  Examples:

        chmode("/tmp/a_file", 0o600) - set read and write bits for the user.

        :param filename:
        :param mode: What mode to set.
        :return:
        """
        def _chmod(do_filename, do_mode):
            os.chmod(do_filename, do_mode)
        yield threads.deferToThread(_chmod, filename, mode)

    @inlineCallbacks
    def copy_file(self, source_path: str, dest_path: str):
        """
        Copy a file in a non-blocking method and returns a deferred.

        :param source_path: Complete path for source file.
        :param dest_path: Complete path to destination file.
        :return:
        """
        def _copy_file(src, dst):
            shutil.copy2(src, dst)

        yield threads.deferToThread(_copy_file, source_path, dest_path)

    @inlineCallbacks
    def delete(self, filename, remove_empty: Optional[bool] = None, ignore_warnings: Optional[bool] = None):
        """
        Delete a file, returns a deferred.

        :param filename: Full path of file to delete
        :param remove_empty: If the directory is empty after the file is deleted, remove the directory.
        :param ignore_warnings: If True, no errors will be raised.
        :return:
        """
        if ignore_warnings is None:
            ignore_warnings = True

        def _delete(delete_filename, delete_empty):
            try:
                os.remove(delete_filename)
            except OSError as e:
                if ignore_warnings is True:
                    return
                raise IOError(f"delete: Could not delete: {e}")
            if delete_empty is True:
                folder = os.path.dirname(delete_filename)
                if os.path.exists(folder) and os.path.isdir(folder):
                    all_items = os.listdir(os.path.dirname(delete_filename))
                    if len(all_items) == 0:
                        os.rmdir(folder)

        if remove_empty is None:
            remove_empty = False

        yield threads.deferToThread(_delete, filename, remove_empty)

    @inlineCallbacks
    def exists(self, filename: str, create_if_missing: Optional[bool] = None):
        """
        Checks if a file exists. If create_if_missing is True, will create the file if it's
        missing.

        :param filename:
        :param create_if_missing:
        :return:
        """
        create_if_missing = create_if_missing or False

        def _exists(filepath):
            return os.path.exists(filepath)
        results = yield threads.deferToThread(_exists, filename)

        if results is False and create_if_missing is True:
            self.touch(filename)
            return True
        return results

    @inlineCallbacks
    def file_last_modified(self, path_to_file: str):
        """
        Gets the timestamp a file was last modified. This returns a deferred that returns an int.

        :param path_to_file:
        :return:
        """
        def _file_last_modified(path):
            return os.path.getmtime(path)

        yield threads.deferToThread(_file_last_modified, path_to_file)

    @inlineCallbacks
    def listdir(self, pathname):
        """
        Return the results of os.listdir, but in a non-blocking method.

        :param pathname: Full path of directory to list.
        :return:
        """
        def _listdir(thepath):
            try:
                os.listdir(thepath)
            except OSError as e:
                raise IOError(f"listdir: Could not list directory: {e}")

        yield threads.deferToThread(_listdir, pathname)

    @inlineCallbacks
    def move_file(self, source_path: str, dest_path: str):
        """
        Move a file in a non-blocking method and returns a deferred.

        :param source_path: Complete path for source file.
        :param dest_path: Complete path to destination file.
        :return:
        """
        def _move_file(src, dst):
            shutil.move(src, dst)

        yield threads.deferToThread(_move_file, source_path, dest_path)

    @inlineCallbacks
    def rename(self, filename: str):
        """
        Rean

        :param filename: Path to the file.
        :return:
        """
        def _size(file):
            os.path.getsize(file)

        yield threads.deferToThread(_size, filename)

    @inlineCallbacks
    def size(self, filename: str):
        """
        Get the size of a file, returns a deferred that returns an int.

        :param filename: Path to the file.
        :return:
        """
        def _size(file):
            os.path.getsize(file)

        yield threads.deferToThread(_size, filename)

    @inlineCallbacks
    def touch(self, filename: str) -> None:
        """
        Checks if a file exists. If create_if_missing is True, will create the file if it's
        missing.

        :param filename:
        :param create_if_missing:
        :return:
        """
        def _touch(do_filename):
            Path(filename).touch()

        yield threads.deferToThread(_touch, filename)

    ################################
    # Search files in directories. #
    ################################

    @inlineCallbacks
    def search_path_for_files(self, filename: str, recursive: Optional[bool] = None,
                              merge_dict: Optional[dict] = None, hasher: Optional[Callable] = None):
        """
        Used to search a path for a given filename. For example, the following will search
        all modules for a given file:
        files = self._Files.search_path_for_files("yombo/modules/*/somefile.txt")

        This returns a dictionary of dictionaries. The key is the fully qualified path.

        :param filename: A path and filename to search.
        :param recursive: If true, will do a recursive search. Default: True
        :param merge_dict: If set, merge results from a previous call into the output.
        :param hasher: If set, file will be read and it's contents passed to the the hasher function.
        :return:
        """

        def get_the_files_list(_final_filter, _recursive):
            return [f for f in glob.glob(_final_filter, recursive=_recursive)]

        merge_dict = merge_dict or {}

        recursive = recursive or True
        if filename.startswith("/"):
            final_filter = filename
        else:
            final_filter = f"{self._app_dir}/{filename}"

        files = yield threads.deferToThread(get_the_files_list, final_filter, recursive)

        remove_length_full = len(f"{self._app_dir}/")
        for file in files:
            relative_full_file = file[remove_length_full:]  # yombo/modules/zwave/xyz/somethingelse.txt
            relative_full_parts = relative_full_file.split("/")
            full_parts = file.split("/")
            merge_dict[file] = {
                "module_name": relative_full_parts[2],  # zwave
                "module_name_full": ".".join(relative_full_parts[0:2]),  # yombo.modules.zwave
                "filename": relative_full_parts[-1],  # somethingelse.txt
                "folder": "/".join(full_parts[:-1]),  # /opt/yombo-gateway/yombo/modules/zwave
                "file": file,  # /opt/yombo-gateway/yombo/modules/zwave/xyz/somethingelse.txt
            }
        return merge_dict

    @inlineCallbacks
    def extract_classes_from_files(self, files: Union[str, List[str], Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extracts all classes from a file (or files). This accepts a string (file path), list of filepaths, or
        even a dictionary where the keys are file path names. This can even accept self._Files.search_path_for_files, imagine that!

        Returns a dictionary where the classname is the key with the class object as the value.

        This function is typically used to get magic classes from modules. See device types, input types, or nodes modules
        for examples.

        :param files: A full pathname of the file. Can be a string, list of strings, or dictionary.
        :return:
        """
        if isinstance(files, str):
            files = [files]
        elif isinstance(files, dict):
            files = list(files.keys())

        app_dir = self._app_dir

        def get_classes():
            results = {}
            for fullfile in files:
                # Check to make sure it's relative pathname and not absolute.
                if fullfile.startswith(app_dir):
                    fullfile = fullfile[len(f"{app_dir}/"):]

                fullfile_parts = fullfile.split("/")
                filename = fullfile_parts[-1]
                if filename.endswith(".py") is False:  # Only process python files.
                    continue

                # Convert fullfile to python module:
                file_parts = fullfile.split(".", 2)
                file_root = file_parts[0]
                python_module = file_parts[0].replace("/", ".")

                # Now look at each file, get the available classes, import them, and create the returning dictionary.
                try:
                    possible_file = __import__(python_module, globals(), locals(), [], 0)
                    module_tail = reduce(lambda p1, p2: getattr(p1, p2),
                                         [possible_file, ] + python_module.split(".")[1:])
                    classes = readmodule(python_module)
                    for class_name_full, reference in classes.items():
                        class_name = class_name_full.rstrip('_')
                        klass = getattr(module_tail, class_name_full)
                        if not isinstance(klass, Callable):
                            logger.info(f"Warning: Unable to load class: '{class_name_full}'  It's not callable.")
                            continue
                        results[class_name] = klass
                except Exception as e:
                    logger.error("------------------( Magic class error)-----------------")
                    logger.error("File processing: Full path: {fullfile}", fullfile=fullfile)
                    logger.error("File processing: Python Module: {python_module}", python_module=python_module)
                    logger.error("Reason: {e}", e=e)
                    logger.error("-----------------==(Traceback)==-----------------------")
                    logger.error("{trace}", trace=traceback.format_exc())
                    logger.error("-------------------------------------------------------")
                    pass
            return results

        classes = yield threads.deferToThread(get_classes)
        return classes

    ############################
    # Determine file contents. #
    ############################

    @classmethod
    @inlineCallbacks
    def mime_type_from_file(cls, filename):
        """
        Gets the mime type by inspecting the file.

        :param filename:
        :return:
        """
        def get_mime(file):
            my_results = cls.magicparse.from_file(file)
            mime, charset = my_results.split("; charset=")
            return {"content_type": mime, "charset": charset}

        results = yield threads.deferToThread(get_mime, filename)
        return results

    @classmethod
    @inlineCallbacks
    def mime_type_from_buffer(cls, data):
        """
        Gets the mime type by inspecting the variable contents.

        :param filename:
        :return:
        """

        def get_mime(buffer):
            my_results = cls.magicparse.from_buffer(buffer)
            mime, charset = my_results.split("; charset=")
            return {"content_type": mime, "charset": charset}

        results = yield threads.deferToThread(get_mime, data)
        return results
