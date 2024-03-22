""" Copyright start
MIT License
Copyright (c) 2024 Fortinet Inc
Copyright end """

import requests, json
from connectors.core.connector import get_logger, ConnectorError
from connectors.core.utils import update_connnector_config

logger = get_logger('microfocus_smax')

URGENCY = {
    "Total Loss Of Service": "TotalLossOfService",
    "No Disruption": "NoDisruption",
    "Slight Disruption": "SlightDisruption",
    "Severe Disruption": "SevereDisruption",
}
IMPACT_SCOP = {
    "Single User": "SingleUser",
    "Multiple Users": "MultipleUsers",
    "Site Or Department": "SiteOrDepartment",
    "Enterprise": "Enterprise"
}

REQUEST_STATUS = {
    "Request Status Ready": "RequestStatusReady",
    "Request Status In Progress": "RequestStatusInProgress",
    "Request Status Pending": "RequestStatusPending",
    "Request Status Suspended": "RequestStatusSuspended",
    "Request Status Complete": "RequestStatusComplete",
    "Request Status Pending Parent": "RequestStatusPendingParent",
    "Request Status Rejected": "RequestStatusRejected",
    "Request Status PendingVendor": "RequestStatusPendingVendor",
    "Request Status Pending External Service Desk": "RequestStatusPendingExternalServiceDesk",
    "Request Status Pending Special Operation": "RequestStatusPendingSpecialOperation"
}


class MicroFocusSmax(object):
    def __init__(self, config):
        self.server_url = config.get("server_url", "").strip("/")
        self.verify_ssl = config.get('verify_ssl')
        self.username = config.get("username")
        self.password = config.get("password")
        self.tenant_id = config.get("tenant_id")
        self.token = self.get_token()

        self.connector_info = config.get("connector_info")
        if self.connector_info:
            update_connnector_config(connector_name=self.connector_info.get("connector_name"),
                                     version=self.connector_info.get("connector_version"),
                                     updated_config=config,
                                     configId=config.get("config_id"))

    def get_token(self):
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            data = {
                "login": self.username,
                "password": self.password
            }
            params = {
                "TENANTID": self.tenant_id
            }
            login_api = "/auth/authentication-endpoint/authenticate/login"
            url = self.server_url + login_api

            try:
                from connectors.debug_utils.curl_script import make_curl
                make_curl("POST", url, headers=headers, params=params, data=json.dumps(data), verify_ssl=self.verify_ssl)
            except Exception as err:
                pass

            response = requests.request(method="POST", url=url,
                                        headers=headers, json=data, params=params, verify=self.verify_ssl)
            if response.ok:
                return response.text
            else:
                raise ConnectorError(json.loads(response.text).get("message"))
        except Exception as e:
            if 'Max retries exceeded' in str(e):
                raise ConnectorError(
                    'Max retries exceeded. Please check the URL provided for configuration of connector')
            raise ConnectorError(e)

    def make_api_call(self, method="GET", params=None, data=None, headers=None, url=None, json_data=None):
        try:
            url = self.server_url + url
            if json_data is None:
                json_data = {}

            if headers:
                headers.update({"Cookie" : "SMAX_AUTH_TOKEN="+self.token})
            else:
                headers = {"Cookie": "SMAX_AUTH_TOKEN=" + self.token}

            try:
                from connectors.debug_utils.curl_script import make_curl
                make_curl("POST", url, headers=headers, params=params, data=json.dumps(data),
                          verify_ssl=self.verify_ssl)
            except Exception as err:
                pass

            response = requests.request(method=method, url=url, headers=headers, data=data, json=json_data, params=params, verify=self.verify_ssl)
            if response.ok:
                if response.content:
                    response = response.json()
                else:
                    response = {"Success": "No Data Returned"}
                return response
            else:
                raise ConnectorError(json.loads(response.text).get("message"))
        except Exception as e:
            # logger.error(e)
            if 'Max retries exceeded' in str(e):
                raise ConnectorError(
                    'Max retries exceeded. Please check the URL provided for configuration of connector')
            raise ConnectorError(e)


def get_entity_details(config, params):
    endpoint = "/rest/{tenant_id}/ems/{entity_type}/{entity_id}".format(tenant_id=config.get("tenant_id"), entity_type=params.get("entity_type"), entity_id=params.get("entity_id"))
    layout = "Id"
    if params.get("entity_fields"):
        layout = layout + "," + params.get("entity_fields")
    params = {
        "layout": layout
    }
    smax = MicroFocusSmax(config)
    resp = smax.make_api_call(params=params, url=endpoint)
    return resp


def query_entities(config, params):
    endpoint = "/rest/{tenant_id}/ems/{entity_type}".format(tenant_id=config.get("tenant_id"), entity_type=params.get("entity_type"))
    layout = "Id"
    if params.get("entity_fields"):
        layout = layout + "," + params.get("entity_fields")
    params = {
        "layout": layout,
        "filter": params.get("query_filter"),
        "order": params.get("order_by"),
        "size": params.get("size"),
        "skip": params.get("skip")
    }
    smax = MicroFocusSmax(config)
    resp = smax.make_api_call(params=params, url=endpoint)
    return resp


def bulk_operations_entities(config, params, operation):
    endpoint = "/rest/{tenant_id}/ems/bulk".format(tenant_id=config.get("tenant_id"))
    data = {
        "entities": params.get("entities"),
        "operation": operation
    }
    headers = {
        'Content-Type': 'application/json'
    }
    smax = MicroFocusSmax(config)
    resp = smax.make_api_call("POST", headers=headers, url=endpoint, json_data=data)
    return resp


def update_entities(config, params):
    return bulk_operations_entities(config, params, "UPDATE")


def create_entities(config, params):
    return bulk_operations_entities(config, params, "CREATE")


def create_incident(config, params):
    incident_properties = {
        "DisplayLabel": params.get("incident_name"),
        "Description": params.get("incident_description"),
        "RegisteredForActualService": params.get("impacted_service_id"),
        "RequestedByPerson": params.get("requested_by_user_id"),
        "Urgency": URGENCY.get(params.get("incident_urgency")),
        "ImpactScope": IMPACT_SCOP.get(params.get("impact_scope")),
        "ServiceDeskGroup": params.get("service_desk_group_id")
    }
    if params.get("other_properities"):
        incident_properties.update(params.get("other_properities"))
    params.update({"entities": [{"entity_type":"Incident", "properties": incident_properties}]})
    return bulk_operations_entities(config, params, "CREATE")


def update_incident(config, params):
    incident_properties = {
        "Id": params.get("incident_id"),
        "Description": params.get("incident_description"),
        "Urgency": URGENCY.get(params.get("incident_urgency")),
        "ImpactScope": IMPACT_SCOP.get(params.get("impact_scope")),
        "Status": params.get("incident_status"),
        "ClosureCategory": params.get("incident_closure_category_id"),
        "CompletionCode": params.get("incident_completion_code"),
        "Solution": params.get("incident_solution"),
    }
    if params.get("other_properties"):
        incident_properties.update(params.get("other_properties"))
    params.update({"entities": [{"entity_type":"Incident", "properties": incident_properties}]})
    return bulk_operations_entities(config, params, "UPDATE")


def create_request(config, params):
    incident_properties = {
        "DisplayLabel": params.get("request_name"),
        "Description": params.get("request_description"),
        "RequestedByPerson": params.get("requested_by_user_id"),
        "RequestedForPerson": params.get("requested_for_user_id"),
        "Urgency": URGENCY.get(params.get("request_urgency")),
        "ImpactScope": IMPACT_SCOP.get(params.get("impact_scope")),
    }
    if params.get("other_properties"):
        incident_properties.update(params.get("other_properties"))
    params.update({"entities": [{"entity_type":"Request", "properties": incident_properties}]})
    return bulk_operations_entities(config, params, "CREATE")


def update_request(config, params):
    incident_properties = {
        "Id": params.get("request_id"),
        "Description": params.get("request_description"),
        "Urgency": URGENCY.get(params.get("request_urgency")),
        "ImpactScope": IMPACT_SCOP.get(params.get("impact_scope")),
        "Status": REQUEST_STATUS.get(params.get("request_status"))
    }
    if params.get("other_properties"):
        incident_properties.update(params.get("other_properties"))
    params.update({"entities": [{"entity_type":"Request", "properties": incident_properties}]})
    return bulk_operations_entities(config, params, "UPDATE")


def check_health(config):
    smax = MicroFocusSmax(config)
    return True


operations = {
    "create_entities": create_entities,
    "get_entity_details": get_entity_details,
    "query_entities": query_entities,
    "update_entities": update_entities,
    "create_incident": create_incident,
    "update_incident": update_incident,
    "create_request": create_request,
    "update_request": update_request,
    "check_health": check_health
}