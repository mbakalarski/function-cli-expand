# Copyright 2026-present Michal Bakalarski and Netclab Contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""A Crossplane composition function."""

import hashlib
import json

import grpc
from crossplane.function import logging, request, resource, response
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from crossplane.function.proto.v1 import run_function_pb2_grpc as grpcv1
from jsonrpcclient import request_json

JSONRPC_BASE = {"version": 1, "format": "json"}


class FunctionRunner(grpcv1.FunctionRunnerService):
    """A FunctionRunner handles gRPC RunFunctionRequests."""

    def __init__(self):
        """Create a new FunctionRunner."""
        self.log = logging.get_logger()

    async def RunFunction(
        self, req: fnv1.RunFunctionRequest, _: grpc.aio.ServicerContext
    ) -> fnv1.RunFunctionResponse:
        """Run the function."""
        log = self.log.bind(tag=req.meta.tag)
        log.info("Running function")

        rsp = response.to(req)

        observed_xr = resource.struct_to_dict(req.observed.observed_xr.resource)
        name_prefix = observed_xr["metadata"].get("name")
        fqdn = observed_xr["spec"].get("endpoint")
        config_ref = observed_xr["spec"].get("configMapRef")
        config_name = config_ref.get("name")
        namespace = config_ref.get("namespace", "default")

        response.require_resources(
            rsp,
            name="dynamic-config",
            api_version="v1",
            kind="ConfigMap",
            match_name=config_name,
            namespace=namespace,
        )

        config_map = request.get_required_resource(req, "dynamic-config")

        if not config_map:
            return
        
        full_config: str = config_map.get("data", {}).get("cmdlines", " ")

        trees = build_trees(full_config)

        for tree in trees:
            path = path_from_tree(tree)
            name = name_prefix + "-" + name_from_path(path)

            path_log = log.bind(resource=name, path=" | ".join(path))
            path_log.debug("Creating resource")

            source = construct_clicommand_resource(fqdn, tree)
            
            resource.update(
                rsp.desired.resources[name],
                source,
            )

        return rsp


def path_from_tree() -> list[str]:
    pass


def build_trees(config: str):
    pass


def name_from_path(path: list[str]) -> str:
    """name_from_path function."""
    joined = "|".join(path)
    return hashlib.sha1(joined.encode(), usedforsecurity=False).hexdigest()[:10]


def construct_clicommand_resource(fqdn: str, tree: dict) -> dict:
    """Construct the CliCommand resource."""
    return {
        "apiVersion": "netclab.dev/v1alpha1",
        "kind": "CliCommand",
        "spec": {
            "endpoint": fqdn,
            "removeContainer": False,
            "cmds": tree,
        },
    }
