""" Copyright start
  Copyright (C) 2024 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """

from connectors.core.connector import Connector, get_logger, ConnectorError
from .operations import operations, check_health

logger = get_logger('microfocus_smax')


class MicroFocusSmax(Connector):
    def execute(self, config, operation, params, **kwargs):
        try:
            config['connector_info'] = {"connector_name": self._info_json.get('name'),
                                        "connector_version": self._info_json.get('version')}
            operation = operations.get(operation)
            result = operation(config, params)
            return result
        except Exception as e:
            logger.error("An exception occurred: {}".format(e))
            raise ConnectorError("An exception occurred: {}".format(e))

    def check_health(self, config):
        try:
            config['connector_info'] = {"connector_name": self._info_json.get('name'),
                                        "connector_version": self._info_json.get('version')}
            check_health(config)
        except Exception as e:
            logger.error("An exception occurred: {}".format(e))
            raise ConnectorError("An exception occurred: {}".format(e))
