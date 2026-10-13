from bs4 import BeautifulSoup

from pipeline import storage

KEY_PHRASES = {
    "has_online_payment": [
        "pay online",
        "pay now",
        "make a payment",
        "pay your bill",
        "payment portal",
        "online payment",
        "pay invoice",
    ],
    "has_processor_fees": [
        "convenience fee",
        "processing fee",
        "surcharge",
        "credit card fee",
    ],
}
PAYMENT_DOMAINS = {
    "stripe": ["stripe.com"],
    "paypal": ["paypal.com", "paypal.me"],
    "square": ["squareup.com", "square.link"],
    "venmo": ["venmo.com"],
    "authorize.net": ["authorize.net"],
    "clover": ["clover.com"],
    "payload": ["payload.com"],
    "hyfin": ["hyfin.app"],
    "slim cd": ["slimcd.com"],
}
ACCOUNTING_DOMAINS = {
    "quickbooks": ["quickbooks", "intuit.com"],
    "freshbooks": ["freshbooks.com"],
    "xero": ["xero.com"],
    "bill.com": ["bill.com"],
    "melio": ["meliopayments.com"],
    "invoice2go": ["invoice2go.com"],
    "jobber": ["getjobber.com"],
    "housecall pro": ["housecallpro.com"],
    "servicetitan": ["servicetitan.com"],
}


def find_tools(html, tool_domains):
    """
    Finds domains in the html that are often signs of tool integration
    """
    found = []
    for tool, domains in tool_domains.items():
        for domain in domains:
            if domain in html:
                found.append(tool)
                break
    return found


def find_phrases(html, keyphrases_dict):
    """
    Finds key phrases in the html
    """
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text().lower()
    signals = {}
    for signal, phrases in keyphrases_dict.items():
        signals[signal] = any(phrase in page_text for phrase in phrases)
    return signals


def find_pay_links(html):
    """
    Finds links whose text mentions "pay"
    """
    soup = BeautifulSoup(html, "html.parser")
    pay_links = []
    for a in soup.select("a[href]"):
        if "pay" in a.get_text().lower():
            pay_links.append(a["href"])
    return pay_links


def extract_signals(html):
    """
    Extract the signals from phrases and tools integrations
    """
    html_lowered = html.lower()
    signals = find_phrases(html_lowered, KEY_PHRASES)
    signals["payment_tools"] = find_tools(html_lowered, PAYMENT_DOMAINS)
    signals["accounting_tools"] = find_tools(html_lowered, ACCOUNTING_DOMAINS)
    signals["pay_links"] = find_pay_links(html_lowered)
    return signals


def run():
    """
    Extract signals from all websites and upload to GCP
    """
    _, rows = storage.read_all_files("websites")

    # Initialize results and error logging
    results = []
    errors = {}

    # Extract signals and join with the domain
    for row in rows:
        if row["html"] is None or row["error"] is not None:
            continue
        try:
            signals = extract_signals(row["html"])
            signals["domain"] = row["domain"]
            results.append(signals)
        except Exception as e:
            errors[row["domain"]] = type(e).__name__

    # Upload the signals
    blob_name = storage.write_data("website_signals", results, stage="intermediate")

    # Return a summary
    return {
        "domains": len(results),
        "errors": errors,
        "uploaded": blob_name,
    }


if __name__ == "__main__":
    print(run())
