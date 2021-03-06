# Copyright (c) 2013 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import uuid

from zaqar.i18n import _
import zaqar.openstack.common.log as logging
from zaqar.queues.transport import utils
from zaqar.queues.transport.wsgi import errors


JSONObject = dict
"""Represents a JSON object in Python."""

JSONArray = list
"""Represents a JSON array in Python."""

LOG = logging.getLogger(__name__)


#
# TODO(kgriffs): Create Falcon "before" hooks adapters for these functions
#


def deserialize(stream, len):
    """Deserializes JSON from a file-like stream.

    This function deserializes JSON from a stream, including
    translating read and parsing errors to HTTP error types.

    :param stream: file-like object from which to read an object or
        array of objects.
    :param len: number of bytes to read from stream
    :raises: HTTPBadRequest, HTTPServiceUnavailable
    """

    if len is None:
        description = _(u'Request body can not be empty')
        raise errors.HTTPBadRequestBody(description)

    try:
        # TODO(kgriffs): read_json should stream the resulting list
        # of messages, returning a generator rather than buffering
        # everything in memory (bp/streaming-serialization).
        return utils.read_json(stream, len)

    except utils.MalformedJSON as ex:
        LOG.debug(ex)
        description = _(u'Request body could not be parsed.')
        raise errors.HTTPBadRequestBody(description)

    except utils.OverflowedJSONInteger as ex:
        LOG.debug(ex)
        description = _(u'JSON contains integer that is too large.')
        raise errors.HTTPBadRequestBody(description)

    except Exception as ex:
        # Error while reading from the network/server
        LOG.exception(ex)
        description = _(u'Request body could not be read.')
        raise errors.HTTPServiceUnavailable(description)


def sanitize(document, spec=None, doctype=JSONObject):
    """Validates a document and drops undesired fields.

    :param document: A dict to verify according to `spec`.
    :param spec: (Default None) Iterable describing expected fields,
        yielding tuples with the form of:

            (field_name, value_type, default_value)

        Note that value_type may either be a Python type, or the
        special string '*' to accept any type. default_value is the
        default to give the field if it is missing, or None to require
        that the field be present.

        If spec is None, the incoming documents will not be validated.
    :param doctype: type of document to expect; must be either
        JSONObject or JSONArray.
    :raises: HTTPBadRequestBody
    :returns: A sanitized, filtered version of the document. If the
        document is a list of objects, each object will be filtered
        and returned in a new list. If, on the other hand, the document
        is expected to contain a single object, that object's fields will
        be filtered and the resulting object will be returned.
    """

    if doctype is JSONObject:
        if not isinstance(document, JSONObject):
            raise errors.HTTPDocumentTypeNotSupported()

        return document if spec is None else filter(document, spec)

    if doctype is JSONArray:
        if not isinstance(document, JSONArray):
            raise errors.HTTPDocumentTypeNotSupported()

        if spec is None:
            return document

        return [filter(obj, spec) for obj in document]

    raise TypeError('doctype must be either a JSONObject or JSONArray')


def filter(document, spec):
    """Validates and retrieves typed fields from a single document.

    Sanitizes a dict-like document by checking it against a
    list of field spec, and returning only those fields
    specified.

    :param document: dict-like object
    :param spec: iterable describing expected fields, yielding
        tuples with the form of: (field_name, value_type). Note that
        value_type may either be a Python type, or the special
        string '*' to accept any type.
    :raises: HTTPBadRequest if any field is missing or not an
        instance of the specified type
    :returns: A filtered dict containing only the fields
        listed in the spec
    """

    filtered = {}
    for name, value_type, default_value in spec:
        filtered[name] = get_checked_field(document, name,
                                           value_type, default_value)

    return filtered


def get_checked_field(document, name, value_type, default_value):
    """Validates and retrieves a typed field from a document.

    This function attempts to look up doc[name], and raises
    appropriate HTTP errors if the field is missing or not an
    instance of the given type.

    :param document: dict-like object
    :param name: field name
    :param value_type: expected value type, or '*' to accept any type
    :param default_value: Default value to use if the value is missing,
        or None to make the value required.
    :raises: HTTPBadRequest if the field is missing or not an
        instance of value_type
    :returns: value obtained from doc[name]
    """

    try:
        value = document[name]
    except KeyError:
        if default_value is not None:
            value = default_value
        else:
            description = _(u'Missing "{name}" field.').format(name=name)
            raise errors.HTTPBadRequestBody(description)

    # PERF(kgriffs): We do our own little spec thing because it is way
    # faster than jsonschema.
    if value_type == '*' or isinstance(value, value_type):
        return value

    description = _(u'The value of the "{name}" field must be a {vtype}.')
    description = description.format(name=name, vtype=value_type.__name__)
    raise errors.HTTPBadRequestBody(description)


def get_client_uuid(req):
    """Read a required Client-ID from a request.

    :param req: A falcon.Request object
    :raises: HTTPBadRequest if the Client-ID header is missing or
        does not represent a valid UUID
    :returns: A UUID object
    """

    try:
        return uuid.UUID(req.get_header('Client-ID', required=True))

    except ValueError:
        description = _(u'Malformed hexadecimal UUID.')
        raise errors.HTTPBadRequestAPI(description)
