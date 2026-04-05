Feature: Provider routing
  LLM client factory must route each provider to the correct API endpoint.

  Scenario: ZAI provider uses Z.AI Coding API endpoint
    Given provider "zai"
    When creating an LLM client
    Then the client should use the endpoint "https://api.z.ai/api/coding/paas/v4"

  Scenario: XAI provider uses xAI endpoint
    Given provider "xai"
    When creating an LLM client
    Then the client should use the endpoint "https://api.x.ai/v1"
