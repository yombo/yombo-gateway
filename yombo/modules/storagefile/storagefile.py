"""
Adds support for storing files on the local file system through the storage library.

All files are stored within the "working_dir/storage_files" path.

.. code-block:: python

   yield self._Storage.save_data(
                   image.content,
                   f"file://kitchen_webcam_motion/{self._Storage.expand(500)}/{int(round(time(), 3)*1000)}.jpg",
                   expires=1,
                   public=True)


:copyright: 2018 Yombo
"""
import ntpath
import os
import urllib.parse

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.web.static import File

from yombo.core.exceptions import YomboWarning
from yombo.core.module import YomboModule
from yombo.core.log import get_logger
from yombo.lib.webinterface.auth import run_first
from yombo.utils import save_file, delete_file
from yombo.utils.imagehelper import ImageHelper

logger = get_logger("modules.storagefile")


class StorageFile(YomboModule):
    """
    Stores files locally.
    """
    def _init_(self, **kwargs):
        storage_path = f"{self._Atoms.get('working_dir')}/storage_files"
        self.app_dir = self._Atoms.get('app_dir')
        self.storage_path = self._Configs.get("storagefile", "path", storage_path)

        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    def _storage_backends_(self, **kwargs):
        return {
            "file": {
                "save_file_callback": self.save_file,
                "save_data_callback": self.save_data,
                "delete": self.delete,
            }
        }

    def generate_url(self, parts, file_id, mangle_id, thumb=None):
        folder, filename = ntpath.split(parts.netloc + parts.path)
        file, extension = os.path.splitext(filename)

        if thumb is True:
            thumb2 = "_thumb"
        else:
            thumb2 = ""
        return f"/storage_files/{file_id}_{mangle_id}{thumb2}{extension}"

    @inlineCallbacks
    def save_file(self, source_file, dest_parts, dest_parts_thumb,
                  delete_source, file_id, mangle_id, expires, public, extra, **kwargs):
        """
        Saves an existing file. Basically, either moves or copies an existing file into
        the new location.

        Item in stored within the yombo working directory, which is typically within the user's folder under the
        '.yombo' folder. If an absolute (full) path is supplied, set extra as a dictionary with 'abolsute' as True.

        :param source_file:
        :param dest_parts:
        :param delete_source:
        :param file_id:
        :param expires:
        :param public:
        :return:
        """
        helper = ImageHelper()
        yield helper.set(source_file)
        results = yield self._save_common(helper, dest_parts, dest_parts_thumb,
                                          delete_source, file_id, mangle_id,
                                          expires, public, extra, **kwargs)
        if delete_source is True:
            yield delete_file(source_file)
        return results

    @inlineCallbacks
    def save_data(self, source_data, dest_parts, dest_parts_thumb,
                  file_id, mangle_id, expires, public, extra, **kwargs):
        """
        Saves data into a file.

        Item in stored within the yombo working directory, which is typically within the user's folder under the
        '.yombo' folder. If an absolute (full) path is supplied, set extra as a dictionary with 'abolsute' as True.

        :param source_data:
        :param dest_parts:
        :param file_id:
        :param expires:
        :param public:
        :return:
        """
        helper = ImageHelper()
        yield helper.set(source_data)
        results = yield self._save_common(helper, dest_parts, dest_parts_thumb,
                                          file_id, mangle_id,
                                          expires, public, extra, **kwargs)
        return results

    @inlineCallbacks
    def _save_common(self, helper, dest_parts, dest_parts_thumb,
                    file_id, mangle_id, expires, public, extra, **kwargs):
        """
        An internal function that saves the data.

        :param helper:
        :param dest_parts:
        :param dest_parts_thumb:
        :param file_id:
        :param mangle_id:
        :param expires:
        :param public:
        :param extra:
        :param kwargs:
        :return:
        """

        destination = urllib.parse.urlunparse(dest_parts)
        file_path = destination.split("://")[1].split("?")[0].split("#")[0]
        final_path = f"{self.storage_path}/{file_path}"
        if isinstance(extra, dict) and "absolute" in extra and extra["absolute"] is True:
            final_path = file_path

        image = yield helper.get()
        yield save_file(final_path, image.content)

        url = self.generate_url(dest_parts, file_id, mangle_id)
        results = {
            "internal_url": self._WebInterface.internal_url + url,
            "external_url": self._WebInterface.external_url + url,
            "file_path": final_path,
        }

        try:
            thumbnail = yield helper.thumbnail()
            destination = urllib.parse.urlunparse(dest_parts_thumb)
            file_path = destination.split("://")[1].split("?")[0].split("#")[0]
            final_path = f"{self.storage_path}/{file_path}"
            if isinstance(extra, dict) and "absolute" in extra and extra["absolute"] is True:
                final_path = file_path
            yield save_file(final_path, thumbnail.content)
            url = self.generate_url(dest_parts_thumb, file_id, mangle_id, thumb=True)
            results.update({
                "internal_thumb_url": self._WebInterface.internal_url + url,
                "external_thumb_url": self._WebInterface.external_url + url,
                "file_path_thumb": final_path,
            })
        except YomboWarning:
            pass

        return results

    @inlineCallbacks
    def delete(self, file):
        """
        Delete's a file.

        :param file:
        :return:
        """
        try:
            yield delete_file(file["file_path"], remove_empty=True)
        except Exception as e:
            logger.warn("Error deleting file: {e}", e=e)
            pass
        try:
            yield delete_file(file["file_path_thumb"], remove_empty=True)
        except Exception as e:
            logger.warn("Error deleting file thumb: {e}", e=e)
        return True

    def _webinterface_add_routes_(self, **kwargs):
        """
        Display storage files via HTTP.

        :param kwargs:
        :return:
        """
        if hasattr(self, "_States") and self._States["loader.operating_mode"] == "run":
            return {
                "routes": [
                    self.web_interface_routes,
                ],
            }

    def web_interface_routes(self, webapp):
        """
        Display the actual content of the requested locally stored file.

        :param webapp: A pointer to the webapp, it"s used to setup routes.
        :return:
        """
        with webapp.subroute("/") as webapp:
            @webapp.route("/storage_files/<string:in_file_id>")
            @run_first()
            @inlineCallbacks
            def page_file_storage_show_file(webinterface, request, session, in_file_id):
                # print("looking up file_id: %s" % in_file_id)
                folder, filename = ntpath.split(in_file_id)
                filename, extension = os.path.splitext(filename)

                file_parts = filename.split("_", 3)
                file_id = file_parts[0]
                mangle_id = file_parts[1]

                Storage = webinterface._Storage
                # print(f"storageFile_web: getting file_id: {file_id}")
                file = yield Storage.get(file_id)
                # print(f"got file: {file}")
                if (file.public is not True and (session is None or session.auth_id is None)) or \
                        mangle_id != file.mangle_id:
                    f = File(f"{self.app_dir}/yombo/lib/webinterface/static/source/img/no-access.svg")
                    f.isLeaf = True
                    f.type = "image/svg+xml"
                    f.encoding = None
                    return f

                if "_thumb" in in_file_id:
                    f = File(file.file_path_thumb)
                else:
                    f = File(file.file_path)
                f.isLeaf = True
                f.type = file.content_type
                f.encoding = file.charset
                return f
