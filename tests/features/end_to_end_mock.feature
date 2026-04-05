Feature: End-to-end mock pipeline
  Signal processing must extract a valid trading decision from LLM output.

  Scenario: Pipeline produces a valid trading decision
    Given a complete trading pipeline with mocked LLM
    When the pipeline processes ticker "AAPL"
    Then a trading decision should be produced
    And the decision should contain BUY, SELL, or HOLD
