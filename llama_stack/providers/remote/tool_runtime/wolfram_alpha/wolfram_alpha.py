# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import json
from typing import Any, Dict, List, Optional

import requests

from llama_stack.apis.common.content_types import URL
from llama_stack.apis.tools import (
    Tool,
    ToolDef,
    ToolInvocationResult,
    ToolParameter,
    ToolRuntime,
)
from llama_stack.distribution.request_headers import NeedsRequestProviderData
from llama_stack.providers.datatypes import ToolsProtocolPrivate

from .config import WolframAlphaToolConfig


class WolframAlphaToolRuntimeImpl(
    ToolsProtocolPrivate, ToolRuntime, NeedsRequestProviderData
):
    def __init__(self, config: WolframAlphaToolConfig):
        self.config = config
        self.url = "https://api.wolframalpha.com/v2/query"

    async def initialize(self):
        pass

    async def register_tool(self, tool: Tool):
        pass

    async def unregister_tool(self, tool_id: str) -> None:
        return

    def _get_api_key(self) -> str:
        if self.config.api_key:
            return self.config.api_key

        provider_data = self.get_request_provider_data()
        if provider_data is None or not provider_data.wolfram_alpha_api_key:
            raise ValueError(
                'Pass WolframAlpha API Key in the header X-LlamaStack-Provider-Data as { "wolfram_alpha_api_key": <your api key>}'
            )
        return provider_data.wolfram_alpha_api_key

    async def list_runtime_tools(
        self, tool_group_id: Optional[str] = None, mcp_endpoint: Optional[URL] = None
    ) -> List[ToolDef]:
        return [
            ToolDef(
                name="wolfram_alpha",
                description="Query WolframAlpha for computational knowledge",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="The query to compute",
                        parameter_type="string",
                    )
                ],
            )
        ]

    async def invoke_tool(
        self, tool_name: str, args: Dict[str, Any]
    ) -> ToolInvocationResult:
        api_key = self._get_api_key()
        params = {
            "input": args["query"],
            "appid": api_key,
            "format": "plaintext",
            "output": "json",
        }
        response = requests.get(
            self.url,
            params=params,
        )

        return ToolInvocationResult(
            content=json.dumps(self._clean_wolfram_alpha_response(response.json()))
        )

    def _clean_wolfram_alpha_response(self, wa_response):
        remove = {
            "queryresult": [
                "datatypes",
                "error",
                "timedout",
                "timedoutpods",
                "numpods",
                "timing",
                "parsetiming",
                "parsetimedout",
                "recalculate",
                "id",
                "host",
                "server",
                "related",
                "version",
                {
                    "pods": [
                        "scanner",
                        "id",
                        "error",
                        "expressiontypes",
                        "states",
                        "infos",
                        "position",
                        "numsubpods",
                    ]
                },
                "assumptions",
            ],
        }
        for main_key in remove:
            for key_to_remove in remove[main_key]:
                try:
                    if key_to_remove == "assumptions":
                        if "assumptions" in wa_response[main_key]:
                            del wa_response[main_key][key_to_remove]
                    if isinstance(key_to_remove, dict):
                        for sub_key in key_to_remove:
                            if sub_key == "pods":
                                for i in range(len(wa_response[main_key][sub_key])):
                                    if (
                                        wa_response[main_key][sub_key][i]["title"]
                                        == "Result"
                                    ):
                                        del wa_response[main_key][sub_key][i + 1 :]
                                        break
                            sub_items = wa_response[main_key][sub_key]
                            for i in range(len(sub_items)):
                                for sub_key_to_remove in key_to_remove[sub_key]:
                                    if sub_key_to_remove in sub_items[i]:
                                        del sub_items[i][sub_key_to_remove]
                    elif key_to_remove in wa_response[main_key]:
                        del wa_response[main_key][key_to_remove]
                except KeyError:
                    pass
        return wa_response
