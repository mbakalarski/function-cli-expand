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

import grpc
from crossplane.function import logging, request, resource, response
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from crossplane.function.proto.v1 import run_function_pb2_grpc as grpcv1

from ._buildtree import build_tree

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

        observed_xr = resource.struct_to_dict(req.observed.composite.resource)
        observed_xr_name = observed_xr["metadata"].get("name")
        fqdn = observed_xr["spec"].get("endpoint")
        config_ref = observed_xr["spec"].get("configMapRef")
        configmap_name = config_ref.get("name")
        configmap_namespace = config_ref.get("namespace", "default")

        response.require_resources(
            rsp,
            name="dynamic-config",
            api_version="v1",
            kind="ConfigMap",
            match_name=configmap_name,
            namespace=configmap_namespace,
        )

        configmap = request.get_required_resource(req, "dynamic-config")

        if not configmap:
            response.warning(
                rsp,
                f"Required ConfigMap {configmap_name} not found",
            )
            return rsp

        device_config: str = configmap.get("data", {}).get("cmdlines", "")

        tree = build_tree(device_config)

        for toplevel_cmd, nested_cmd in tree.items():
            name = hashed_name(observed_xr_name, toplevel_cmd)

            path_log = log.bind(resource=name)
            path_log.debug("Creating resource")

            source = construct_cliconfig_resource(
                name, fqdn, {toplevel_cmd: nested_cmd}
            )

            resource.update(
                rsp.desired.resources[name],
                source,
            )

        return rsp


def hashed_name(observed_xr_name: str, toplevel_cmd: str) -> str:
    """hashed_name function."""
    prefix = f"{observed_xr_name[:15]}".rstrip("-")
    suffix = hashlib.sha256(
        toplevel_cmd.encode("utf-8"), usedforsecurity=False
    ).hexdigest()
    return f"{prefix}-{suffix}".strip()[:63]


def construct_cliconfig_resource(name: str, fqdn: str, tree: dict) -> dict:
    """Construct the CliConfig resource."""
    return {
        "apiVersion": "netclab.dev/v1alpha1",
        "kind": "CliConfig",
        "metadata": {
            "name": name,
        },
        "spec": {
            "endpoint": fqdn,
            "removeContainer": False,
            "cmds": tree,
        },
    }
