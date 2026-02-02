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


import unittest
from pathlib import Path

from crossplane.function import logging, resource
from crossplane.function.proto.v1 import run_function_pb2 as fnv1

from function import fn


class TestFunctionRunner(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        logging.configure(level=logging.Level.DISABLED)

    async def test_run_function_generates_resources(self) -> None:
        """Generates a valid Resources."""

        # ----------------------------
        # Inputs
        # ----------------------------

        composite = {
            "apiVersion": "netclab.dev/v1alpha1",
            "kind": "CliConfigSource",
            "metadata": {"name": "ceos01-config"},
            "spec": {
                "endpoint": "ceos01.default.svc.cluster.local",
                "version": 1,
                "configMapRef": {"name": "ceos01-cm", "namespace": "default"},
            },
        }

        cfg_path = Path(__file__).parent / "dc1-spine1.cfg"
        cfg_text = cfg_path.read_text()

        configmap = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "ceos01-cm",
            },
            "data": {
                "cmdlines": cfg_text,
            },
        }

        req = fnv1.RunFunctionRequest(
            input=resource.dict_to_struct({"version": "v1beta2"}),
            observed=fnv1.State(
                composite=fnv1.Resource(resource=resource.dict_to_struct(composite))
            ),
            required_resources={
                "dynamic-config": fnv1.Resources(
                    items=[fnv1.Resource(resource=resource.dict_to_struct(configmap))]
                ),
            },
        )

        # ----------------------------
        # Run function
        # ----------------------------

        runner = fn.FunctionRunner()
        resp = await runner.RunFunction(req, None)

        # ----------------------------
        # Assert
        # ----------------------------

        # Resource existence
        self.assertIsNotNone(resp)
        self.assertIsNotNone(resp.desired)

        self.assertGreater(
            len(resp.desired.resources), 0, "No desired resources generated"
        )

        # Top-level lines (commands without indentation)
        top_level_commands = [
            line
            for line in cfg_text.splitlines()
            if line.strip()
            and not line.startswith(" ")
            and not line.startswith("!")
            and not line.startswith("end")
        ]
        namespace = (
            composite["spec"].get("configMapRef", {}).get("namespace", "default")
        )

        # Number of generated resources matches
        self.assertEqual(
            len(resp.desired.resources),
            len(top_level_commands),
            (
                f"Expected {len(top_level_commands)} resources, "
                f"got {len(resp.desired.resources)}"
            ),
        )

        for cmd in top_level_commands:
            name = fn.hashed_name(f"{composite['metadata']['name']}-{namespace}", cmd)

            # Top-level command has a corresponding resource
            self.assertIn(
                name,
                resp.desired.resources,
                f"Resource for top-level command '{cmd}' not found",
            )

            resource_dict = resource.struct_to_dict(resp.desired.resources[name])
            resource_obj = resource_dict.get("resource", {})

            self.assertEqual(resource_obj["apiVersion"], "netclab.dev/v1alpha1")
            self.assertEqual(resource_obj["kind"], "CliConfig")
            self.assertEqual(resource_obj["metadata"]["name"], name)
            self.assertEqual(
                resource_obj["spec"]["endpoint"], composite["spec"]["endpoint"]
            )
            self.assertIn(cmd, resource_obj["spec"]["cmds"])
            self.assertIsInstance(resource_obj["spec"]["cmds"][cmd], dict)
            self.assertFalse(resource_obj["spec"]["removeContainer"])
