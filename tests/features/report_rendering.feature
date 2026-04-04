Feature: Report rendering
  HTML reports must render Chinese action labels correctly.

  Scenario: Chinese buy action renders in HTML
    Given a trading report with action "买入"
    When rendered to HTML
    Then the HTML should contain the Chinese action label "买入"
    And should not contain untranslated English label "BUY" in the badge
