Feature: Chinese localization
  When output_language is set to Chinese, agent labels must be in Chinese.

  Scenario: Bull analyst label is Chinese when language is Chinese
    Given output_language is "Chinese"
    When an agent generates a bull analyst label
    Then the label should be in Chinese as "看多分析师"
