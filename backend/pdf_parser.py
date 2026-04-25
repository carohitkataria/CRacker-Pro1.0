"""PDF parsing helper - extracts basic financial fields from a Customer PO PDF."""
import re
from typing import Dict, Any, Optional

try:
    import pdfplumber
except Exception:  # pragma: no cover
    pdfplumber = None  # type: ignore


def _extract_amount(text: str) -> Optional[float]:
    # Match Indian/Western formats e.g. ₹ 12,50,000.00 or $1,234,567.89 or 12500000
    m = re.search(r"(?:₹|Rs\.?|INR|\$|USD)\s*([\d,]+(?:\.\d+)?)", text)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except Exception:
            return None
    return None


def parse_customer_po(file_bytes: bytes) -> Dict[str, Any]:
    """Best-effort extraction of common fields from a Customer PO PDF.
    Returns a dict with extracted fields and the raw text (truncated)."""
    out: Dict[str, Any] = {
        "customer_po_number": None,
        "po_date": None,
        "po_value": None,
        "currency": None,
        "vendor_references": [],
        "milestones": [],
        "raw_text_excerpt": "",
        "warnings": [],
    }
    if pdfplumber is None:
        out["warnings"].append("pdfplumber not installed")
        return out
    try:
        import io as _io
        with pdfplumber.open(_io.BytesIO(file_bytes)) as pdf:
            text = "\n".join((page.extract_text() or "") for page in pdf.pages)
    except Exception as e:
        out["warnings"].append(f"failed to read pdf: {e}")
        return out

    out["raw_text_excerpt"] = text[:4000]

    # PO number: look for "PO Number", "Purchase Order", "PO No"
    m = re.search(r"(?:purchase\s*order(?:\s*no\.?)?|p\.?o\.?\s*(?:number|no\.?)?)\s*[:#-]?\s*([A-Z0-9\-/]{4,30})",
                  text, re.IGNORECASE)
    if m:
        out["customer_po_number"] = m.group(1).strip()

    # PO Date: "Date" followed by typical formats
    m = re.search(r"(?:p\.?o\.?\s*date|date\s*of\s*issue|order\s*date)\s*[:\-]?\s*([0-9]{1,2}[\-/\s.][A-Za-z0-9]{1,9}[\-/\s.][0-9]{2,4})",
                  text, re.IGNORECASE)
    if m:
        out["po_date"] = m.group(1).strip()

    # Total value: search for "Total", "Grand Total", "Net Amount", followed by amount
    val_match = re.search(r"(?:grand\s*total|total\s*(?:amount|value)?|net\s*(?:amount|payable))\s*[:\-]?\s*(?:₹|Rs\.?|INR|\$|USD)?\s*([\d,]+(?:\.\d+)?)",
                          text, re.IGNORECASE)
    if val_match:
        try:
            out["po_value"] = float(val_match.group(1).replace(",", ""))
        except Exception:
            pass

    # Currency
    if re.search(r"₹|INR|Rupees", text, re.IGNORECASE):
        out["currency"] = "INR"
    elif re.search(r"\$|USD|Dollars", text, re.IGNORECASE):
        out["currency"] = "USD"

    # Vendor references (look for "Vendor PO", "Reference")
    for vm in re.finditer(r"(?:vendor\s*ref(?:erence)?|ref(?:erence)?\s*no\.?)\s*[:\-]?\s*([A-Z0-9\-/]{3,30})",
                          text, re.IGNORECASE):
        out["vendor_references"].append(vm.group(1).strip())

    # Milestones: rows like "Milestone 1 ... 25-Mar-2026 ... 10,00,000"
    for mm in re.finditer(r"(milestone\s*\d+|phase\s*\d+|m[ \-]?\d+)[^\n]{0,100}?([0-9]{1,2}[\-/\s.][A-Za-z0-9]{1,9}[\-/\s.][0-9]{2,4})[^\n]{0,40}?([\d,]+(?:\.\d+)?)",
                          text, re.IGNORECASE):
        try:
            value = float(mm.group(3).replace(",", ""))
        except Exception:
            value = 0.0
        out["milestones"].append({
            "milestone_name": mm.group(1).strip(),
            "due_date": mm.group(2).strip(),
            "value": value,
            "is_billed": False,
        })

    if not any([out["customer_po_number"], out["po_date"], out["po_value"]]):
        out["warnings"].append("Could not detect any PO fields — please review manually")
    return out
