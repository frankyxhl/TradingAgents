Feature: Graph routing
  Debate routing must handle Chinese-prefixed responses correctly.

  Scenario: Chinese bull response routes to Bear Researcher
    Given a Chinese debate response from "看多分析师"
    When routing to the next node
    Then the next node should be "Bear Researcher"

  Scenario: English bull response routes to Bear Researcher
    Given a debate response from "Bull Analyst"
    When routing to the next node
    Then the next node should be "Bear Researcher"
