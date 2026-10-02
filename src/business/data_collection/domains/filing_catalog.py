from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable


@dataclass(frozen=True)
class FilingFamily:
    key: str
    name: str
    capability_group: str
    xbrl_available: bool = True


# Inventory of filing families published by NSE on its XBRL Filing Information
# page as of 2026-09-03. This is a capability registry, not a claim that every
# family has a dedicated JSON endpoint; many are exposed through the broad
# corporate-announcements feed and/or attached XBRL assets.
NSE_XBRL_FILING_FAMILIES: tuple[FilingFamily, ...] = (
    FilingFamily("investor_complaints", "Regulation 13(3) - Statement of Investor complaints", "investor_protection"),
    FilingFamily("investor_complaints_reits_invits", "Statement of Investor complaints-REITS/InvITs", "investor_protection"),
    FilingFamily("corporate_governance", "Regulation 27(2) - Corporate Governance", "governance"),
    FilingFamily("shareholding_pattern", "Regulation 31 - Shareholding Pattern", "ownership"),
    FilingFamily("share_capital_reconciliation", "Reconciliation of Share Capital Audit", "ownership"),
    FilingFamily("financial_results_indas", "Regulation 33 - Financial Results - Ind AS Integrated Filing - Financial - Ind AS", "financial"),
    FilingFamily("financial_results_other_than_banks", "Regulation 33 - Financial Results - Other than Banks Integrated Filing - Financial", "financial"),
    FilingFamily("financial_results_reits_invits", "Regulation 33 - Financial Results - REITS/InvITs", "financial"),
    FilingFamily("financial_results_general_insurance", "Regulation 33 - Financial Results - General Insurance", "financial"),
    FilingFamily("financial_results_life_insurance", "Regulation 33 - Financial Results - Life Insurance", "financial"),
    FilingFamily("financial_results_banking", "Regulation 33 - Financial Results - Banking", "financial"),
    FilingFamily("financial_results_nbfc", "Regulation 33 - Financial Results - NBFC", "financial"),
    FilingFamily("voting_results", "Regulation 44 - Voting Result", "shareholder_actions"),
    FilingFamily("insider_trading_reg_7", "Regulation 7(2) and 7(3) - Insider Trading", "ownership"),
    FilingFamily("deviation_variation", "Regulation 32(1) - Statement of deviation/variation", "capital_allocation"),
    FilingFamily("secretarial_compliance", "Regulation 24A - Secretarial Compliance Report", "governance"),
    FilingFamily("record_date", "Regulation 60 - Record Date/closure of transfer book", "corporate_actions"),
    FilingFamily("unit_holding_pattern", "Unit Holding Pattern", "ownership"),
    FilingFamily("related_party_transactions", "Regulation 23(9) - Related Party Transactions", "related_parties"),
    FilingFamily("brsr", "Business Responsibility and Sustainability Reporting", "esg"),
    FilingFamily("credit_rating", "Credit Rating", "credit"),
    FilingFamily("default_history", "Default History Information", "credit"),
    FilingFamily("interest_payment", "Interest Payment", "debt_service"),
    FilingFamily("redemption_payment", "Redemption Payment", "debt_service"),
    FilingFamily("board_meeting_prior_intimation_reg50", "Regulation 50 - Prior Intimation of Board Meeting", "governance"),
    FilingFamily("board_meeting_prior_intimation_reg29", "Regulation 29 - Prior Intimation of Board Meeting", "governance"),
    FilingFamily("management_auditor_changes", "Regulation 30 - Change in directors, KMP, SMP, Auditor and Compliance Officer", "governance"),
    FilingFamily("acquisition_restructuring", "Regulation 30 - Acquisitions / Scheme of Arrangement / restructuring", "strategy_transactions"),
    FilingFamily("board_outcome_dividend_bonus_delisting_buyback", "Regulation 30 - Board outcome for Dividend, Bonus, Voluntary Delisting and Buyback", "corporate_actions"),
    FilingFamily("securities_issuance_structure", "Regulation 30 - Issuance/forfeiture/split/consolidation/buyback/restrictions/allotment", "capital_structure"),
    FilingFamily("material_agreements", "Regulation 30 - Material agreements", "strategy_transactions"),
    FilingFamily("fraud_default_arrest", "Regulation 30 - Fraud/defaults/arrest", "regulatory_risk"),
    FilingFamily("one_time_settlement", "Regulation 30 - One time settlement with a bank", "credit"),
    FilingFamily("debt_restructuring", "Regulation 30 - Resolution plan / loan restructuring", "credit"),
    FilingFamily("shareholder_meeting_notice", "Regulation 30 - Notice of Shareholders Meeting", "shareholder_actions"),
    FilingFamily("trading_window_closure", "Regulation 30 - Closure of Trading Window", "insider_trading"),
    FilingFamily("lost_share_certificate", "Regulation 39 - Loss of Share Certificate / duplicate", "investor_services"),
    FilingFamily("corporate_insolvency", "Regulation 30 - Corporate Insolvency Resolution Process", "regulatory_risk"),
    FilingFamily("audit_qualifications", "Regulation 33 - Impact of Audit Qualifications / Unmodified Opinion", "audit"),
    FilingFamily("insider_trading_plan", "Insider - Trading Plan", "insider_trading"),
    FilingFamily("integrated_governance", "Integrated Filing - Governance", "governance"),
    FilingFamily("orders_contracts", "Regulation 30 - Awarding / bagging / receiving orders/contracts", "business_operations"),
    FilingFamily("buyback_open_market", "ISD for buy-back from Open Market Route", "corporate_actions"),
    FilingFamily("buyback_tender_offer", "ISD for buy-back through Tender Offer Route", "corporate_actions"),
    FilingFamily("ipo_in_principle", "Initial Public Offer - In-principle", "capital_raising"),
    FilingFamily("adr_gdr", "ADR/GDR In-principle and Post Allotment", "capital_raising"),
    FilingFamily("fccb", "FCCB In-principle and Post Allotment", "capital_raising"),
    FilingFamily("preferential_issue", "Preferential Issue - In-principle and Post Allotment", "capital_raising"),
    FilingFamily("qip", "QIP - In-principle and Post Allotment", "capital_raising"),
    FilingFamily("rights_issue", "Right Issue - In-principle and Post Allotment", "capital_raising"),
    FilingFamily("ipo_final_listing", "Initial Public Offer - Final Listing", "capital_raising"),
    FilingFamily("resignation_management", "Resignation of Director/KMP/SMP/Compliance Officer", "governance"),
    FilingFamily("resignation_statutory_auditor", "Regulation 30 - Resignation of Statutory Auditor", "audit"),
    FilingFamily("forensic_audit", "Regulation 30 - Forensic Audit - Para A", "audit"),
    FilingFamily("actions_orders", "Actions initiated/taken or orders passed", "regulatory_risk"),
    FilingFamily("analyst_investor_meet", "Analyst/Investor Meet - Para A", "investor_relations"),
    FilingFamily("code_of_conduct_violation", "Violation of Code of Conduct under PIT Regulations", "insider_trading"),
    FilingFamily("regulation_30_para_b", "Regulation 30 - Para B of Part A of Schedule III", "material_disclosures"),
)


def list_nse_xbrl_filing_families(*, capability_group: str | None = None) -> list[dict[str, object]]:
    families: Iterable[FilingFamily] = NSE_XBRL_FILING_FAMILIES
    if capability_group:
        families = (f for f in families if f.capability_group == capability_group)
    return [asdict(f) for f in families]
