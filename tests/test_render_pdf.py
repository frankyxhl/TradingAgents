"""Tests for render_pdf in render_report.py."""

import sys
from unittest.mock import MagicMock, patch

from tradingagents.render_report import render_pdf


def _minimal_data(decision: str = "FINAL TRANSACTION PROPOSAL: BUY") -> dict:
    return {
        "trade_date": "2025-01-01",
        "company_of_interest": "AAPL",
        "final_trade_decision": decision,
    }


def _mock_weasyprint():
    """Create a mock weasyprint module and return (module_mock, html_instance_mock)."""
    mock_module = MagicMock()
    mock_instance = MagicMock()
    mock_module.HTML.return_value = mock_instance
    return mock_module, mock_instance


def test_render_pdf_generates_file_at_specified_path(tmp_path):
    """render_pdf writes a PDF at the given output_path."""
    out = str(tmp_path / "report.pdf")
    mock_module, mock_instance = _mock_weasyprint()

    with patch.dict(sys.modules, {"weasyprint": mock_module}):
        result = render_pdf(_minimal_data(), output_path=out)

    assert result == out
    mock_module.HTML.assert_called_once()
    mock_instance.write_pdf.assert_called_once_with(out)


def test_render_pdf_auto_generates_filename():
    """When output_path is None, filename is derived from ticker and date."""
    mock_module, mock_instance = _mock_weasyprint()

    with patch.dict(sys.modules, {"weasyprint": mock_module}):
        result = render_pdf(_minimal_data())

    assert result == "AAPL_2025-01-01_report.pdf"
    mock_instance.write_pdf.assert_called_once_with("AAPL_2025-01-01_report.pdf")


def test_render_pdf_auto_generates_filename_from_data():
    """Filename uses company_of_interest and trade_date from data."""
    mock_module, mock_instance = _mock_weasyprint()
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: SELL")
    data["company_of_interest"] = "TSLA"
    data["trade_date"] = "2026-03-15"

    with patch.dict(sys.modules, {"weasyprint": mock_module}):
        result = render_pdf(data)

    assert result == "TSLA_2026-03-15_report.pdf"
    mock_instance.write_pdf.assert_called_once_with("TSLA_2026-03-15_report.pdf")


def test_render_pdf_passes_html_string():
    """render_pdf passes the rendered HTML string to weasyprint.HTML."""
    mock_module, mock_instance = _mock_weasyprint()

    with patch.dict(sys.modules, {"weasyprint": mock_module}):
        render_pdf(_minimal_data(), output_path="/tmp/test.pdf")

    call_kwargs = mock_module.HTML.call_args
    html_string = call_kwargs.kwargs.get("string") or call_kwargs[1].get("string")
    assert "<!DOCTYPE html>" in html_string
    assert "AAPL" in html_string


def test_render_pdf_returns_string(tmp_path):
    """render_pdf return value is a string path."""
    mock_module, mock_instance = _mock_weasyprint()
    out = str(tmp_path / "out.pdf")

    with patch.dict(sys.modules, {"weasyprint": mock_module}):
        result = render_pdf(_minimal_data(), output_path=out)

    assert isinstance(result, str)
