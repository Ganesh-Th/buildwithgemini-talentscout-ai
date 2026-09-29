# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configure Memory Bank instance with custom topic for user allergies."""

import agentplatform

PROJECT_ID = "qwiklabs-gcp-03-70611c3d6bad"
LOCATION = "us-east1"
MEMORY_BANK_ID = "6850201532625846272"
RESOURCE_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{MEMORY_BANK_ID}"


def configure_memory_bank():
    client = agentplatform.Client(project=PROJECT_ID, location=LOCATION)

    config = agentplatform.types.AgentEngineConfig(
        context_spec=agentplatform.types.ReasoningEngineContextSpec(
            memory_bank_config=agentplatform.types.ReasoningEngineContextSpecMemoryBankConfig(
                customization_configs=[
                    agentplatform.types.MemoryBankCustomizationConfig(
                        memory_topics=[
                            agentplatform.types.MemoryBankCustomizationConfigMemoryTopic(
                                managed_memory_topic=agentplatform.types.MemoryBankCustomizationConfigMemoryTopicManagedMemoryTopic(
                                    managed_topic_enum="USER_PERSONAL_INFO"
                                )
                            ),
                            agentplatform.types.MemoryBankCustomizationConfigMemoryTopic(
                                managed_memory_topic=agentplatform.types.MemoryBankCustomizationConfigMemoryTopicManagedMemoryTopic(
                                    managed_topic_enum="USER_PREFERENCES"
                                )
                            ),
                            agentplatform.types.MemoryBankCustomizationConfigMemoryTopic(
                                managed_memory_topic=agentplatform.types.MemoryBankCustomizationConfigMemoryTopicManagedMemoryTopic(
                                    managed_topic_enum="KEY_CONVERSATION_DETAILS"
                                )
                            ),
                            agentplatform.types.MemoryBankCustomizationConfigMemoryTopic(
                                managed_memory_topic=agentplatform.types.MemoryBankCustomizationConfigMemoryTopicManagedMemoryTopic(
                                    managed_topic_enum="EXPLICIT_INSTRUCTIONS"
                                )
                            ),
                            agentplatform.types.MemoryBankCustomizationConfigMemoryTopic(
                                custom_memory_topic=agentplatform.types.MemoryBankCustomizationConfigMemoryTopicCustomMemoryTopic(
                                    label="user_allergies",
                                    description="Allergies, food sensitivities, medical allergies, dietary restrictions, and environmental allergies of the user.",
                                )
                            ),
                        ]
                    )
                ]
            )
        )
    )

    print(f"Updating Memory Bank instance {RESOURCE_NAME}...")
    res = client.agent_engines.update(
        name=RESOURCE_NAME,
        config=config,
    )
    print("Memory Bank updated successfully with user_allergies topic.")
    return res


if __name__ == "__main__":
    configure_memory_bank()
