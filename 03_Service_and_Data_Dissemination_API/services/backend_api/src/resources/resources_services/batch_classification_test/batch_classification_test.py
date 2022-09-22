########################################################################################################################
#
# Redistribution and use in source and binary forms, with or without modification, is prohibited for all commercial
# applications without licensing by GeoVille GmbH.
#
# Batch classification test API call
#
# Date created: 01.06.2020
# Date last modified: 10.02.2021
#
# __author__  = Michel Schwandner (schwandner@geoville.com)
# __version__ = 21.02
#
########################################################################################################################

from error_classes.http_error_400.http_error_400 import BadRequestError
from error_classes.http_error_404.http_error_404 import NotFoundError
from error_classes.http_error_500.http_error_500 import InternalServerErrorAPI
from error_classes.http_error_503.http_error_503 import ServiceUnavailableError
from flask_restx import Resource
from geoville_ms_database.geoville_ms_database import execute_database
from geoville_ms_logging.geoville_ms_logging import gemslog, LogLevel
from geoville_ms_orderid_generator.generator import generate_orderid
from init.init_env_variables import database_config_file, database_config_section_api, database_config_section_oauth
from init.namespace_constructor import service_namespace as api
from lib.auth_header import auth_header_parser
from lib.database_helper import check_service_name_existence, get_service_id, query_user_id
from lib.general_helper_methods import publish_to_queue
from models.general_models.general_models import service_success_response_model
from models.models_error.http_error_400 import error_400_model
from models.models_error.http_error_401 import error_401_model
from models.models_error.http_error_403 import error_403_model
from models.models_error.http_error_404 import error_404_model
from models.models_error.http_error_500 import error_500_model
from models.models_error.http_error_503 import error_503_model
from models.models_services.batch_classification.batch_classification_model import batch_classification_model
from oauth.oauth2 import require_oauth
import flask
import json
import traceback


########################################################################################################################
# Resource definition for the batch classification test API call
########################################################################################################################

@api.expect(batch_classification_model)
@api.header('Content-Type', 'application/json')
class BatchClassificationTest(Resource):
    """ Class for handling the POST request

    This class defines the API call for starting the batch classification test workflow. The class consists of one
    methods which accepts a POST request. For the POST request a JSON with several parameters is required, defined in
    the corresponding model.

    """

    ####################################################################################################################
    # Method for handling the POST request
    ####################################################################################################################

    @require_oauth(['admin', 'batch_classification', 'gaf'])
    @api.expect(auth_header_parser)
    @api.response(202, 'Order Received', service_success_response_model)
    @api.response(400, 'Validation Error', error_400_model)
    @api.response(401, 'Unauthorized', error_401_model)
    @api.response(403, 'Forbidden', error_403_model)
    @api.response(404, 'Not Found', error_404_model)
    @api.response(500, 'Internal Server Error', error_500_model)
    @api.response(503, 'Service Unavailable', error_503_model)
    def post(self):
        """ POST definition for triggering the batch classification test workflow

        <p style="text-align: justify">This method defines the handler of the POST request for starting off the batch
        classification processing chain within the GEMS service architecture. It is an asynchronous call and thus, it
        does not return the requested data immediately but generates an order ID. After the request has been submitted
        successfully, a message to a RabbitMQ queue will be send. A listener in the backend triggers the further
        procedure, starting with the job scheduling of the order. The final result will be stored in a database in form
        of a link and can be retrieved via the browser. To access the service it is necessary to generate a valid Bearer
        token with sufficient access rights, otherwise the request will return a HTTP status code 401 or 403. In case of
        those errors, please contact the GeoVille service team for any support.</p>

        <br><b>Description:</b>
        <p style="text-align: justify"></p>

        <br><b>Request headers:</b>
        <ul>
        <li><p><i>Authorization: Bearer token in the format "Bearer XXXX"</i></p></li>
        </ul>

        <br><b>Request payload:</b>
        <ul>
        <li><p><i>params (dict): Dictionary with a set of parameters</i></p></li>
        <li><p><i>user_id (str): User specific client ID</i></p></li>
        <li><p><i>service_name (str): Unique name of the service to be called. Name should not be changed</i></p></li>
        </ul>

        <br><b>Result:</b>
        <p style="text-align: justify">After the request was successfully received by the GEMS API, an order ID will be
        created for the submitted job in the GEMS backend and stored in a database with all necessary information for
        the consumer and the system itself. The initial status of the order in the database will be set to 'received'.
        After that the order ID will be returned in form of a Hypermedia link which enables the possibilities to
        programmatically check the status the order by a piece of code of a GEMS API consumer. In the following the
        status of the order can be queried by using the GEMS service route listed below:</p>

        <ul><li><p><i>/services/order_status/{order_id}</i></p></li></ul>

        <p style="text-align: justify">The status of the order will be updated whenever the processing chain reaches the
        next step in its internal calculation. In case of success, the user will receive a link, which provides the
        ordered file. Additionally an e-mail notification is enabled, which sends out an e-mail in case of success, with
        the resulting link or in case of failure, with a possible error explanation.
        </p>

        """

        order_id = None

        try:
            req_args = api.payload
            access_token = flask.request.headers.get('Authorization').split(" ")[1].strip()

            user_id = query_user_id(access_token, database_config_file, database_config_section_oauth)

            if not check_service_name_existence(req_args['service_name'], database_config_file,
                                                database_config_section_api):
                error = NotFoundError('Service name does not exist', '', '')
                gemslog(LogLevel.WARNING, f"'message': {error.to_dict()}", 'API-batch_classification_test')
                return {'message': error.to_dict()}, 404

            service_id = get_service_id(req_args['service_name'], database_config_file, database_config_section_api)
            order_id = generate_orderid(user_id, service_id, json.dumps(req_args))

            publish_to_queue(req_args['service_name'], order_id, req_args)

            update_query = """UPDATE customer.service_orders 
                                  set status = 'RECEIVED' 
                              WHERE
                                  order_id = %s;
                           """
            execute_database(update_query, (order_id,), database_config_file, database_config_section_api, True)

        except KeyError as err:
            error = BadRequestError(f'Key error resulted in a BadRequest: {err}', api.payload, traceback.format_exc())
            gemslog(LogLevel.WARNING, f"'message': {error.to_dict()}", 'API-batch_classification_test', order_id)
            return {'message': error.to_dict()}, 400

        except AttributeError:
            error = ServiceUnavailableError('Could not connect to the database server', '', '')
            gemslog(LogLevel.ERROR, f"'message': {error.to_dict()}", 'API-batch_classification_test', order_id)
            return {'message': error.to_dict()}, 503

        except Exception:
            error = InternalServerErrorAPI('Unexpected error occurred', api.payload, traceback.format_exc())
            gemslog(LogLevel.ERROR, f"'message': {error.to_dict()}", 'API-batch_classification_test', order_id)
            return {'message': error.to_dict()}, 500

        else:
            gemslog(LogLevel.INFO, f'Request successful with order ID {order_id}', 'API-batch_classification_test', order_id)
            return {
                       'message': 'Your order has been successfully submitted',
                       'links': {
                           'href': f'/services/order_status/{order_id}',
                           'rel': 'services',
                           'type': 'GET'
                       }
                   }, 202
