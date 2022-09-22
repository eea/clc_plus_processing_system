########################################################################################################################
#
# Redistribution and use in source and binary forms, with or without modification, is prohibited for all commercial
# applications without licensing by GeoVille GmbH.
#
# RabbitMQ list virtual hosts GEMS API call
#
# Date created: 01.06.2020
# Date last modified: 10.02.2021
#
# __author__  = Michel Schwandner (schwandner@geoville.com)
# __version__ = 21.02
#
########################################################################################################################

from error_classes.http_error_401.http_error_401 import UnauthorizedError
from error_classes.http_error_500.http_error_500 import InternalServerErrorAPI
from error_classes.http_error_503.http_error_503 import ServiceUnavailableError
from flask_restx import Resource
from geoville_ms_logging.geoville_ms_logging import gemslog, LogLevel
from init.init_env_variables import rabbitmq_host, rabbitmq_management_port, rabbitmq_password, rabbitmq_user
from init.namespace_constructor import rabbitmq_namespace as api
from lib.auth_header import auth_header_parser
from models.models_rabbitmq.list_vhosts.list_vhosts_model import virtual_host_response_model
from models.models_error.http_error_401 import error_401_model
from models.models_error.http_error_403 import error_403_model
from models.models_error.http_error_500 import error_500_model
from models.models_error.http_error_503 import error_503_model
from oauth.oauth2 import require_oauth
from pyrabbit.api import Client
from pyrabbit.http import HTTPError, NetworkError
import traceback


########################################################################################################################
# Resource definition for the list virtual hosts API call
########################################################################################################################

@api.header('Content-Type', 'application/json')
class RabbitMQVHosts(Resource):
    """ Class for handling the GET requests

    This class defines the API call for the RabbitMQ list virtual hosts script. The class consists of one method which
    accepts a GET request. For the GET request no additional parameters are required.

    """

    ####################################################################################################################
    # Method for handling the GET request
    ####################################################################################################################

    @require_oauth(['admin'])
    @api.expect(auth_header_parser)
    @api.response(200, 'Operation successful', virtual_host_response_model)
    @api.response(401, 'Unauthorized', error_401_model)
    @api.response(403, 'Forbidden', error_403_model)
    @api.response(500, 'Internal Server Error', error_500_model)
    @api.response(503, 'Service Unavailable', error_503_model)
    def get(self):
        """ GET definition for requesting the list of all available virtual hosts of the RabbitMQ instance

        <p style="text-align: justify">This method defines the handler for the GET request of the RabbitMQ list virtual
        hosts script. It returns a list of all available virtual hosts in GEMS with the connection parameters stored in
        the environment variables.</p>

        <br><b>Description:</b>
        <p style="text-align: justify"></p>

        <br><b>Request headers:</b>
        <ul>
        <li><p><i>Authorization: Bearer token in the format "Bearer XXXX"</i></p></li>
        </ul>

        <br><b>Result:</b>
        <p style="text-align: justify">The result of the </p>

        """

        try:
            cl = Client(f'{rabbitmq_host}:{rabbitmq_management_port}', rabbitmq_user, rabbitmq_password)

        except HTTPError:
            error = UnauthorizedError('Login credentials derived from the environment variable are incorrect', '', '')
            gemslog(LogLevel.ERROR, f"'message': {error.to_dict()}", 'API-rabbitmq_vhosts')
            return {'message': error.to_dict()}, 401

        except NetworkError:
            error = ServiceUnavailableError('Could not connect to the specified RabbitMQ service', '', '')
            gemslog(LogLevel.ERROR, f"'message': {error.to_dict()}", 'API-rabbitmq_vhosts')
            return {'message': error.to_dict()}, 503

        except Exception:
            error = InternalServerErrorAPI('Unexpected error occurred', api.payload, traceback.format_exc())
            gemslog(LogLevel.ERROR, f"'message': {error.to_dict()}", 'API-rabbitmq_vhosts')
            return {'message': error.to_dict()}, 500

        else:
            gemslog(LogLevel.INFO, 'Successfully retrieved the virtual hosts', 'API-rabbitmq_vhosts')
            return {'virtual_hosts': cl.get_vhost_names()}, 200
