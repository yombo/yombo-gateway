# Import python libraries

# Import 3rd-party libs

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import data_pickle, data_unpickle
from yombo.utils.datatypes import coerce_value

from yombo.lib.localdb import Sessions
logger = get_logger("library.localdb.websessions")


class DB_Websessions(object):
    @inlineCallbacks
    def get_web_session(self, session_id=None):
        def parse_record(data):
            auth_data = data_unpickle(data.auth_data)

            return {
                "id": data.id,
                "enabled": coerce_value(data.enabled, "bool"),
                "gateway_id": data.gateway_id,
                "user_id": data.user_id,
                "auth_data": auth_data,
                "refresh_token": data.refresh_token,
                "access_token": data.access_token,
                "refresh_token_expires_at": data.refresh_token_expires_at,
                "access_token_expires_at": data.access_token_expires_at,
                "created_at": data.created_at,
                "last_access_at": data.last_access_at,
                "updated_at": data.updated_at,
            }
        if session_id is None:
            records = yield Sessions.all()
            output = []
            for record in records:
                output.append(parse_record(record))
            return output
        else:
            record = yield Sessions.find(session_id)
            if record is None:
                raise YomboWarning(f"Session not found in deep storage: {session_id}", errorno=23231)
            return parse_record(record)

    @inlineCallbacks
    def save_web_session(self, session):
        logger.info("save_web_session: session.auth_id: {auth_id}", auth_id=session._auth_id)
        logger.info("save_web_session: session.auth_data: {auth_data}", auth_data=session.auth_data)
        auth_data = data_pickle({
            "auth_data": session.auth_data,
            "auth_type": session.auth_type,
            "auth_at": session.auth_at,
        })

        args = {
            "id": session._auth_id,
            "enabled": coerce_value(session.enabled, "int"),
            "gateway_id": session.gateway_id,
            "auth_data": auth_data,
            "refresh_token": session._refresh_token,
            "access_token": session._access_token,
            "refresh_token_expires_at": session.refresh_token_expires_at,
            "access_token_expires_at": session.access_token_expires_at,
            "user_id": session.user_id,
            "created_at": session.created_at,
            "last_access_at": session.last_access_at,
            "updated_at": session.updated_at,
        }
        yield self.dbconfig.insert("webinterface_sessions", args, None, "OR IGNORE")

    @inlineCallbacks
    def update_web_session(self, session):
        logger.debug("update_web_session: session.auth_id: {auth_id}", auth_id=session._auth_id)
        save_data = data_pickle({
            "auth_data": session.auth_data,
            "auth_type": session.auth_type,
            "auth_at": session.auth_at,
        })
        args = {
            "enabled": coerce_value(session.enabled, "int"),
            "auth_data": save_data,
            "refresh_token": session._refresh_token,
            "access_token": session._access_token,
            "refresh_token_expires_at": session.refresh_token_expires_at,
            "access_token_expires_at": session.access_token_expires_at,
            "user_id": session.user_id,
            "last_access_at": session.last_access_at,
            "updated_at": session.updated_at,
            }
        yield self.dbconfig.update("webinterface_sessions", args, where=["id = ?", session._auth_id])

    @inlineCallbacks
    def delete_web_session(self, session_id):
        yield self.dbconfig.delete("webinterface_sessions", where=["id = ?", session_id])
