"""Map a Utiliko ticket + client/ISP data into the app's OutageRequestCreate.

This is the bridge between the ticket world and the existing call pipeline.
Anything the source did not provide is left BLANK — never invented. Missing
verification data (account #, PIN) flows through as empty so the agent reports
"couldn't verify" instead of fabricating, reusing the POC's never-fabricate rule.
"""

from app.models import OutageRequestCreate
from app.ticketing.base import Company, IspInfo, TicketDetail


def map_ticket_to_request(
    ticket: TicketDetail,
    company: Company,
    isp: IspInfo,
    caller_name: str = "",
) -> OutageRequestCreate:
    """Build the call pipeline's input from the ticket + client + ISP records."""
    return OutageRequestCreate(
        # Required by the pipeline: the number to dial + the account to match.
        isp_phone=isp.support_phone or "",
        account_number=isp.account_or_circuit_id or "",
        # Verification details — passed through as-is; blank stays blank.
        pin=isp.pin or "",
        circuit_id=isp.account_or_circuit_id if isp.circuit_type else "",
        isp_name=isp.isp_name or "",
        # Identity the agent gives / the location it is calling about.
        business_name=company.name or "",
        business_address=isp.service_address or company.address or "",
        caller_name=caller_name or "",
        callback_number=isp.callback_number or company.phone or "",
        location_phone=company.phone or "",
        # Context from the ticket the customer/monitoring system reported.
        symptoms=ticket.description or "",
    )
