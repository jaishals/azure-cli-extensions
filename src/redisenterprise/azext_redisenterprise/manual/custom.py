# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
# pylint: disable=too-many-lines
# pylint: disable=too-many-locals

from azure.cli.core.util import sdk_no_wait
from azure.cli.core.azclierror import MutuallyExclusiveArgumentError
from msrest.serialization import last_restapi_key_transformer


def _get_database_client(cli_ctx):
    from ..generated._client_factory import cf_database
    return cf_database(cli_ctx)


def _get_cluster_with_databases(cluster,
                                databases):
    result = cluster.as_dict(key_transformer=last_restapi_key_transformer)
    # Restore select null cluster attributes that were removed by cluster.as_dict()
    if cluster.zones is None:
        result['zones'] = None

    result['databases'] = []
    for database in databases:
        result['databases'].append(database)
    return result


def redisenterprise_update(client,
                           resource_group_name,
                           cluster_name,
                           sku=None,
                           capacity=None,
                           tags=None,
                           minimum_tls_version=None,
                           no_wait=False):
    parameters = {}
    parameters['sku'] = {}
    parameters['sku']['name'] = sku
    if capacity is not None:
        parameters['sku']['capacity'] = capacity
    if len(parameters['sku']) == 0:
        del parameters['sku']
    if tags is not None:
        parameters['tags'] = tags
    if minimum_tls_version is not None:
        parameters['minimum_tls_version'] = minimum_tls_version
    return sdk_no_wait(no_wait,
                       client.begin_update,
                       resource_group_name=resource_group_name,
                       cluster_name=cluster_name,
                       parameters=parameters)


def redisenterprise_list(cmd,
                         client,
                         resource_group_name=None):
    if resource_group_name:
        clusters = client.list_by_resource_group(resource_group_name=resource_group_name)
    else:
        clusters = client.list()

    result = []
    database_client = _get_database_client(cmd.cli_ctx)
    for cluster in clusters:
        cluster_resource_group = cluster.id.split('/')[4]
        databases = database_client.list_by_cluster(resource_group_name=cluster_resource_group,
                                                    cluster_name=cluster.name)
        result.append(_get_cluster_with_databases(cluster, databases))
    return result


def redisenterprise_show(cmd,
                         client,
                         resource_group_name,
                         cluster_name):
    cluster = client.get(resource_group_name=resource_group_name,
                         cluster_name=cluster_name)

    database_client = _get_database_client(cmd.cli_ctx)
    databases = database_client.list_by_cluster(resource_group_name=resource_group_name,
                                                cluster_name=cluster_name)
    return _get_cluster_with_databases(cluster, databases)


def redisenterprise_create(cmd,
                           client,
                           resource_group_name,
                           cluster_name,
                           location,
                           sku,
                           tags=None,
                           capacity=None,
                           zones=None,
                           minimum_tls_version=None,
                           client_protocol=None,
                           port=None,
                           clustering_policy=None,
                           eviction_policy=None,
                           persistence=None,
                           modules=None,
                           no_database=False,
                           no_wait=False,
                           group_nickname=None,
                           linked_databases=None):
    if (no_database and any(x is not None for x in [client_protocol,
                                                    port,
                                                    clustering_policy,
                                                    eviction_policy,
                                                    persistence,
                                                    modules,
                                                    group_nickname,
                                                    linked_databases])):
        database_param_list_str = []
        if client_protocol is not None:
            database_param_list_str.append('--client-protocol')
        if port is not None:
            database_param_list_str.append('--port')
        if clustering_policy is not None:
            database_param_list_str.append('--clustering-policy')
        if eviction_policy is not None:
            database_param_list_str.append('--eviction-policy')
        if persistence is not None:
            database_param_list_str.append('--persistence')
        if modules is not None:
            database_param_list_str.append('--modules')
        if group_nickname is not None:
            database_param_list_str.append('--group-nickname')
        if linked_databases is not None:
            database_param_list_str.append('--linked-databases')
        error_msg = ('--no-database conflicts with the specified database parameter(s): '
                     '{}'.format(', '.join(database_param_list_str)))
        recommendation = ('Try to use --no-database without specifying database parameters, '
                          'or else try removing --no-database')
        raise MutuallyExclusiveArgumentError(error_msg, recommendation)

    # Create cluster
    cluster_parameters = {}
    cluster_parameters['tags'] = tags
    cluster_parameters['location'] = location
    cluster_parameters['sku'] = {}
    cluster_parameters['sku']['name'] = sku
    cluster_parameters['sku']['capacity'] = capacity
    cluster_parameters['zones'] = zones
    cluster_parameters['minimum_tls_version'] = minimum_tls_version
    if (no_database and all(x is None for x in [client_protocol,
                                                port,
                                                clustering_policy,
                                                eviction_policy,
                                                persistence,
                                                modules,
                                                group_nickname,
                                                linked_databases])):
        return sdk_no_wait(no_wait,
                           client.begin_create,
                           resource_group_name=resource_group_name,
                           cluster_name=cluster_name,
                           parameters=cluster_parameters)

    sdk_no_wait(no_wait,
                client.begin_create,
                resource_group_name=resource_group_name,
                cluster_name=cluster_name,
                parameters=cluster_parameters)

    # Create database
    database_parameters = {}
    database_parameters['client_protocol'] = client_protocol
    database_parameters['port'] = port
    database_parameters['clustering_policy'] = clustering_policy
    database_parameters['eviction_policy'] = eviction_policy
    database_parameters['persistence'] = persistence
    database_parameters['modules'] = modules
    database_parameters['geo_replication'] = {}
    if group_nickname is not None:
        database_parameters['geo_replication']['group_nickname'] = group_nickname
    if linked_databases is not None:
        database_parameters['geo_replication']['linked_databases'] = linked_databases
    if len(database_parameters['geo_replication']) == 0:
        del database_parameters['geo_replication']
    database_name = "default"

    database_client = _get_database_client(cmd.cli_ctx)
    database = sdk_no_wait(no_wait,
                           database_client.begin_create,
                           resource_group_name=resource_group_name,
                           cluster_name=cluster_name,
                           database_name=database_name,
                           parameters=database_parameters)

    return database
