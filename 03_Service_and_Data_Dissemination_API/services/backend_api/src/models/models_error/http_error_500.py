########################################################################################################################
#
# InternalServerError error model
#
# Date created: 01.06.2020
# Date last modified: 10.02.2021
#
# __author__  = Michel Schwandner (schwandner@geoville.com)
# __version__ = 21.02
#
########################################################################################################################

from flask_restx import fields
from init.namespace_constructor import general_error_namespace as api
from models.models_error.error_base_model import error_definition
from werkzeug.exceptions import InternalServerError

########################################################################################################################
# Nested response model for the InternalServerError errors
########################################################################################################################

error_description = api.model('error_description_500_model', {
    'code': fields.String(
        description='HTTP error status code',
        example=InternalServerError.code,
        default=InternalServerError.code
    ),
    'status': fields.String(
        description='HTTP error status',
        example='INTERNAL_SERVER_ERROR',
        default='INTERNAL_SERVER_ERROR'
    ),
    'description': fields.String(
        description='Detailed HTTP error description',
        example=InternalServerError.description,
        default=InternalServerError.description
    )
})

error_dicts = api.model('error_dict_500_model', {
    'error_description': fields.Nested(error_description),
    'error_definition': fields.Nested(error_definition),
})

error_500_model = api.model('error_500_model', {
    'message': fields.Nested(error_dicts),
})
