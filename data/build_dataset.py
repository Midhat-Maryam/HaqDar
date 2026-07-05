"""
Builds structured JSON chunks of the Sindh Consumer Protection Act, 2014
and Sindh Consumer Protection Rules, 2017, for embedding into ChromaDB.

Each chunk = one section, with metadata for citation and routing.
Text transcribed from the official Sindh Judicial Academy compiled PDF
(amendments up to Sindh Act No. XXIX of 2023).
"""

import json

# ---------------------------------------------------------------------------
# ACT SECTIONS
# ---------------------------------------------------------------------------
act_sections = [
    {
        "id": "act_s1",
        "part": "PART-I: PRELIMINARY",
        "section_no": "1",
        "title": "Short title, extent and commencement",
        "text": "This Act may be called the Sindh Consumer Protection Act, 2014. It shall extend to the whole of the Province of Sindh. It shall come into force at once."
    },
    {
        "id": "act_s2",
        "part": "PART-I: PRELIMINARY",
        "section_no": "2",
        "title": "Definitions",
        "text": "Defines key terms including: 'Authority' (the Secretary or Director General, Supply and Prices Department, or any officer notified by Government); 'Complainant' (a consumer, a voluntary consumer's association, Government, or the Council/District Protection Council); 'Consumer Court' (the Consumer Protection Court established under section 27); 'Consumer' (a person or entity who buys or leases a product for consideration, including any user, but excluding resale/commercial purchasers; or who hires a service for consideration, including any beneficiary); 'claim' (the case of the consumer set up as a complaint); 'damage' (all damages caused by a product or service, including damage to the product itself and economic loss from deficiency or loss of use); 'Manufacturer' (a person or entity in the business of manufacturing, labeling, controlling design/construction/quality, assembling, or acting as a seller/distributor of a foreign manufacturer's product); 'Product' (same meaning as 'goods' under the Sale of Goods Act 1930, excluding animals, plants, and natural raw products); 'Services' (provision of facilities including communication, advice, or assistance such as medical, legal, or engineering services, excluding contract services or judicial/arbitral judgments); 'False or Misleading Representation' (a detailed list of deceptive statements or conduct by a businessman relating to goods/services, quality, origin, price, warranty, sponsorship, etc.)."
    },
    {
        "id": "act_s3",
        "part": "PART-I: PRELIMINARY",
        "section_no": "3",
        "title": "Act not in derogation of any other law",
        "text": "The provisions of this Act are in addition to, and not in derogation of, any other law currently in force."
    },
    {
        "id": "act_s4",
        "part": "PART-II: LIABILITY ARISING FROM DEFECTIVE PRODUCTS",
        "section_no": "4",
        "title": "Liability for defective products",
        "text": "The manufacturer of a product is liable to a consumer for damages proximately caused by a characteristic of the product that renders it defective, when the damage arose from reasonably anticipated use. A product is defective only if it is defective in construction/composition (s.5), defective in design (s.6), defective due to inadequate warning (s.7), or defective due to nonconformity with an express warranty (s.8). Common trigger scenarios: appliance stopped working, phone or electronics broke shortly after purchase, machine malfunctioned, gadget is faulty, product broke down, item is not working properly, device failed."
    },
    {
        "id": "act_s5",
        "part": "PART-II: LIABILITY ARISING FROM DEFECTIVE PRODUCTS",
        "section_no": "5",
        "title": "Defective in construction or composition",
        "text": "A product is defective in construction or composition if, at the time it was manufactured, a material deviation was made from the manufacturer's own specifications, whether known to the consumer or not."
    },
    {
        "id": "act_s6",
        "part": "PART-II: LIABILITY ARISING FROM DEFECTIVE PRODUCTS",
        "section_no": "6",
        "title": "Defective in design",
        "text": "A product is defective in design if, at the time it left the manufacturer's control, an alternative design existed that was capable of preventing the damage, and the likelihood/gravity of damage outweighed the burden of using that alternative design. Reasonable care in providing adequate warnings is considered when evaluating design defect likelihood."
    },
    {
        "id": "act_s7",
        "part": "PART-II: LIABILITY ARISING FROM DEFECTIVE PRODUCTS",
        "section_no": "7",
        "title": "Defective because of inadequate warning",
        "text": "A product is defective if an adequate warning of a dangerous characteristic was not provided when it left the manufacturer's control, or if the manufacturer failed to use reasonable care to warn users/handlers. Exceptions: no warning is required if the danger is common knowledge, or if the user already knows/should reasonably know of the danger. A manufacturer who later learns of a danger must still warn, or remains liable for subsequent failure to do so."
    },
    {
        "id": "act_s8",
        "part": "PART-II: LIABILITY ARISING FROM DEFECTIVE PRODUCTS",
        "section_no": "8",
        "title": "Defective because of nonconformity to express warranty",
        "text": "A product is defective if it does not conform to an express warranty made by the manufacturer, where that warranty induced the claimant to use the product and the resulting damage was proximately caused by the warranty being untrue."
    },
    {
        "id": "act_s9",
        "part": "PART-II: LIABILITY ARISING FROM DEFECTIVE PRODUCTS",
        "section_no": "9",
        "title": "Proof of manufacturer's knowledge",
        "text": "A manufacturer is not liable for a design defect if they prove they did not know, and could not reasonably have known (given existing scientific/technological knowledge at the time), of the design characteristic, its danger, or a feasible alternative design. Similarly not liable for inadequate-warning claims if they could not have known of the danger at the relevant time."
    },
    {
        "id": "act_s10",
        "part": "PART-II: LIABILITY ARISING FROM DEFECTIVE PRODUCTS",
        "section_no": "10",
        "title": "Restriction on grant of damages",
        "text": "Where a consumer has suffered no damage from a product except loss of utility, the manufacturer is only liable to return the consideration (or part of it) and costs — not full damages."
    },
    {
        "id": "act_s11",
        "part": "PART-II: LIABILITY ARISING FROM DEFECTIVE PRODUCTS",
        "section_no": "11",
        "title": "Duty of disclosures",
        "text": "Where disclosure of a product's components, ingredients, quality, or manufacture/expiry date is material to a consumer's purchase decision, the manufacturer must disclose this. Government may also mandate disclosure by general or special order in particular cases. (Enforceable via complaint to the Authority under s.23(1).)"
    },
    {
        "id": "act_s12",
        "part": "PART-II: LIABILITY ARISING FROM DEFECTIVE PRODUCTS",
        "section_no": "12",
        "title": "Prohibition on exclusions from liability",
        "text": "Liability to a consumer who has suffered damage cannot be limited or excluded by contract terms or notice."
    },
    {
        "id": "act_s13",
        "part": "PART-III: LIABILITY ARISING OUT OF DEFECTIVE AND FAULTY SERVICES",
        "section_no": "13",
        "title": "Liability for faulty or defective services",
        "text": "A provider of services is liable to a consumer for damages proximately caused by the provision of a service that caused damage."
    },
    {
        "id": "act_s14",
        "part": "PART-III: LIABILITY ARISING OUT OF DEFECTIVE AND FAULTY SERVICES",
        "section_no": "14",
        "title": "Standard of provision of services",
        "text": "Where a special (provincial or federal) law regulates the standard of a service, that standard applies. Where no such standard exists, the standard is what a consumer could reasonably expect to obtain in Pakistan at the time."
    },
    {
        "id": "act_s15",
        "part": "PART-III: LIABILITY ARISING OUT OF DEFECTIVE AND FAULTY SERVICES",
        "section_no": "15",
        "title": "Restriction on grant of damages (services)",
        "text": "Where the consumer suffered no damage from a service except lack of benefit, the service provider is only liable to return the consideration (or part of it) and costs."
    },
    {
        "id": "act_s16",
        "part": "PART-III: LIABILITY ARISING OUT OF DEFECTIVE AND FAULTY SERVICES",
        "section_no": "16",
        "title": "Duty of disclosure (services)",
        "text": "Where disclosure of the service provider's capabilities, qualifications, or the quality of products they intend to use is material to a consumer's decision to contract, the provider must disclose this. Government may mandate disclosure by order. (Enforceable via complaint to the Authority under s.23(1).)"
    },
    {
        "id": "act_s17",
        "part": "PART-III: LIABILITY ARISING OUT OF DEFECTIVE AND FAULTY SERVICES",
        "section_no": "17",
        "title": "Prohibition on exclusions from liability (services)",
        "text": "Liability to a person who has suffered damage cannot be limited or excluded by contract terms or notice."
    },
    {
        "id": "act_s18",
        "part": "PART-IV: OBLIGATIONS OF MANUFACTURERS",
        "section_no": "18",
        "title": "Prices to be exhibited at the business place",
        "text": "Unless a price catalogue is available for issue, the manufacturer or trader must prominently display a notice in the shop/display-centre specifying the retail or wholesale price of every good available for sale. (Enforceable via complaint to the Authority under s.23(1), fine up to Rs. 50,000.)"
    },
    {
        "id": "act_s19",
        "part": "PART-IV: OBLIGATIONS OF MANUFACTURERS",
        "section_no": "19",
        "title": "Receipt to be issued to the purchaser",
        "text": "Every manufacturer or trader who sells goods must issue a receipt showing: date of sale; description of goods; batch number, original printed retail price, date of manufacture, and date of expiry; quantity and price; and the name and address of the seller. (Enforceable via complaint to the Authority under s.23(1).)"
    },
    {
        "id": "act_s20",
        "part": "PART-IV: OBLIGATIONS OF MANUFACTURERS",
        "section_no": "20",
        "title": "Return and refund policy",
        "text": "A seller's return and refund policy must be clearly disclosed to the buyer, by means of a sign at the point of purchase, before the transaction is completed."
    },
    {
        "id": "act_s21",
        "part": "PART-V: UNFAIR PRACTICES",
        "section_no": "21",
        "title": "False, deceptive or misleading representation",
        "text": "No person shall make a false, deceptive, or misleading representation regarding: the kind, standard, quality, grade, quantity, composition, style, or model of products; product history or previous use; the kind/standard/quality of services or the skill/qualification of the provider; when products were manufactured/produced/processed/reconditioned; sponsorship, approval, endorsement, or affiliation; whether products are new or reconditioned; necessity of the product/service for wellbeing; existence/exclusion of any condition, guarantee, right, or remedy; or place of origin."
    },
    {
        "id": "act_s22",
        "part": "PART-V: UNFAIR PRACTICES",
        "section_no": "22",
        "title": "Prohibition on bait advertisement",
        "text": "No person shall advertise products/services at a specified price without intending to supply them, or without reasonable grounds to believe they can be supplied at that price for a reasonable period/quantity given market conditions. Anyone who advertises at a specified price must honor that price for a reasonable period and quantity."
    },
    {
        "id": "act_s23",
        "part": "PART-VI: THE POWERS OF THE AUTHORITY",
        "section_no": "23",
        "title": "Powers of Authority",
        "text": "Any person may file a complaint for violation of sections 11, 16, 18, and 19 before the Authority, which may fine the violator up to Rs. 50,000 (recoverable as arrears of land revenue). The Authority may also file a claim before the Consumer Court to declare a product defective (ss.4-8) or a service faulty (s.13), or to declare an act in contravention of Part IV, without proof of actual damage suffered, if damage is likely. The Authority may hold inquiries into defects/practices without prior notice to the manufacturer/service provider, and may direct police or other government officers to gather evidence. Any person aggrieved by an Authority order may appeal to Government within 30 days."
    },
    {
        "id": "act_s24",
        "part": "PART-VI: THE POWERS OF THE AUTHORITY",
        "section_no": "24",
        "title": "Powers of Government",
        "text": "Government may exercise all or any powers of the Authority under the Act (except the power to impose fines under s.23(1)), and may delegate its powers to the Minister In-charge and Secretary, Supply and Prices Department, or to subordinate officers."
    },
    {
        "id": "act_s25",
        "part": "PART-VII: CONSUMER PROTECTION COUNCIL",
        "section_no": "25",
        "title": "Consumer Protection Council",
        "text": "Government shall set up a Consumer Protection Council in the Province, and may set up District Consumer Protection Councils reporting to it. The Provincial Council gathers information to help remove dangerous/defective products and services from trade. At least 50% of Council membership (excluding ex-officio members) must be consumer representatives."
    },
    {
        "id": "act_s26",
        "part": "PART-VIII: DISPOSAL OF CLAIMS AND ESTABLISHMENT OF CONSUMER COURTS",
        "section_no": "26",
        "title": "Filing of Claims",
        "text": "A claim for damages arising from contravention of the Act must be filed before a Consumer Court set up under the Act."
    },
    {
        "id": "act_s27",
        "part": "PART-VIII: DISPOSAL OF CLAIMS AND ESTABLISHMENT OF CONSUMER COURTS",
        "section_no": "27",
        "title": "Establishment of Consumer Courts",
        "text": "Government shall, by notification, establish one or more Consumer Courts in each District, presided over by a Judicial Magistrate."
    },
    {
        "id": "act_s28",
        "part": "PART-VIII: DISPOSAL OF CLAIMS AND ESTABLISHMENT OF CONSUMER COURTS",
        "section_no": "28",
        "title": "Jurisdiction of Consumer Courts",
        "text": "A Consumer Court has jurisdiction where the defendant resides, carries on business, or personally works for gain, or where the cause of action wholly or partly arises."
    },
    {
        "id": "act_s29",
        "part": "PART-VIII: DISPOSAL OF CLAIMS AND ESTABLISHMENT OF CONSUMER COURTS",
        "section_no": "29",
        "title": "Settlement of Claims (mandatory pre-filing notice)",
        "text": "Before filing a claim, a consumer (or the Authority) must send a written notice to the manufacturer/service provider describing the defect/contravention and calling for a remedy. The manufacturer/provider must reply within 15 days. No claim can be entertained by the Consumer Court unless this notice was given and proof of delivery provided, with no adequate response. The claim itself must be filed within 30 days of the cause of action arising (extendable by the Court for sufficient cause, but not beyond 60 days past warranty/guarantee expiry, or one year from purchase/service if no warranty period is specified)."
    },
    {
        "id": "act_s30",
        "part": "PART-VIII: DISPOSAL OF CLAIMS AND ESTABLISHMENT OF CONSUMER COURTS",
        "section_no": "30",
        "title": "Settlement at pretrial stage",
        "text": "Either party may make a firm written settlement offer at any stage of trial. If accepted, the Consumer Court passes an order per the settlement. A party who refuses a settlement offer and later loses must pay actual litigation costs including lawyer's fees. Court approval is required for settlements involving minors, legally incapacitated persons, or collective rights."
    },
    {
        "id": "act_s31",
        "part": "PART-VIII: DISPOSAL OF CLAIMS AND ESTABLISHMENT OF CONSUMER COURTS",
        "section_no": "31",
        "title": "Procedure on receipt of complaint",
        "text": "On receiving a claim about products, the Consumer Court forwards it to the defendant, who must file a written statement within 15 days (extendable by 15 more). If the defendant disputes the claim or fails to respond, the Court settles the dispute; for defective-product claims it may rely on industry standards and expert evidence, or order product samples sent to a laboratory for testing (report due within 30 days, extendable by 15). Similar procedure applies for service claims. The Consumer Court has civil-court powers (summoning witnesses, receiving evidence, etc.) and must decide the claim within six months of summons being served."
    },
    {
        "id": "act_s32",
        "part": "PART-VIII: DISPOSAL OF CLAIMS AND ESTABLISHMENT OF CONSUMER COURTS",
        "section_no": "32",
        "title": "Order of Consumer Court",
        "text": "If satisfied that the product/service complained of is defective/faulty, the Consumer Court may order the defendant to: remove the defect; replace with a non-defective product; return the price/charges paid; take other steps necessary for compliance; pay reasonable compensation for loss due to negligence; award damages; award actual litigation costs including lawyer's fees; recall the product from trade; confiscate or destroy the defective product; remedy the defect within a set period; or cease providing the defective/faulty service until it meets the required standard."
    },
    {
        "id": "act_s33",
        "part": "PART-VIII: DISPOSAL OF CLAIMS AND ESTABLISHMENT OF CONSUMER COURTS",
        "section_no": "33",
        "title": "Penalties",
        "text": "A manufacturer who fails to perform or infringes liabilities under sections 4-8, 11, 13, 14, 16, or 18-22 is punishable with imprisonment up to two years, or a fine up to Rs. 100,000, or both, in addition to damages/compensation determined by the Court. A defendant or claimant who fails to comply with a Consumer Court order is punishable with imprisonment of one month to three years, or a fine of Rs. 50,000 to Rs. 200,000, or both."
    },
    {
        "id": "act_s34",
        "part": "PART-VIII: DISPOSAL OF CLAIMS AND ESTABLISHMENT OF CONSUMER COURTS",
        "section_no": "34",
        "title": "Appeal",
        "text": "Any person aggrieved by a final order of the Consumer Court may appeal to the District and Sessions Court within 30 days of the order."
    },
    {
        "id": "act_s35",
        "part": "PART-VIII: DISPOSAL OF CLAIMS AND ESTABLISHMENT OF CONSUMER COURTS",
        "section_no": "35",
        "title": "Finality of order",
        "text": "Every Consumer Court order becomes final if no appeal is filed under the Act's provisions."
    },
    {
        "id": "act_s36",
        "part": "PART-VIII: DISPOSAL OF CLAIMS AND ESTABLISHMENT OF CONSUMER COURTS",
        "section_no": "36",
        "title": "Dismissal of frivolous or vexatious claims",
        "text": "A frivolous or vexatious claim is dismissed, and the claimant fined up to Rs. 10,000 for willfully instituting a false claim; the defendant receives appropriate compensation from the fine collected."
    },
    {
        "id": "act_s37",
        "part": "PART-IX: MISCELLANEOUS",
        "section_no": "37",
        "title": "Aid to the Consumer Court",
        "text": "All government agencies must act in aid of the Consumer Court in performing its functions."
    },
    {
        "id": "act_s38",
        "part": "PART-IX: MISCELLANEOUS",
        "section_no": "38",
        "title": "Immunity",
        "text": "No suit, prosecution, or legal proceeding lies against any functionary acting in good faith under the direction of the Consumer Court or Government under this Act."
    },
    {
        "id": "act_s39",
        "part": "PART-IX: MISCELLANEOUS",
        "section_no": "39",
        "title": "Power to make rules",
        "text": "Government may make rules, by notification in the official Gazette, to carry out the purposes of the Act. (This is the basis for the Sindh Consumer Protection Rules, 2017.)"
    },
    {
        "id": "act_s40",
        "part": "PART-IX: MISCELLANEOUS",
        "section_no": "40",
        "title": "Power to remove difficulties",
        "text": "If any difficulty arises in giving effect to the Act, Government may make orders, not inconsistent with the Act, to remove such difficulty."
    },
]

# ---------------------------------------------------------------------------
# RULES SECTIONS (Sindh Consumer Protection Rules, 2017)
# ---------------------------------------------------------------------------
rules_sections = [
    {
        "id": "rules_r3",
        "part": "RULES: Complaints Procedure",
        "section_no": "Rule 3",
        "title": "Complaints — Private Person to the Authority",
        "text": "A person may file a complaint for violation of sections 11, 16, 18, and 19 of the Act to the Authority, which shall inquire into the complaint and collect evidence. Police/government officers must assist. If the Authority is satisfied there is sufficient material, it issues notice to the defendant and gives an opportunity to be heard before passing an order. If the defendant fails to appear after being served notice, the Authority may proceed ex-parte and impose a fine."
    },
    {
        "id": "rules_r4_6",
        "part": "RULES: Complaints Procedure",
        "section_no": "Rules 4-6",
        "title": "Cases inquired into; procedure for defective products/services",
        "text": "The Authority may inquire into defects on complaint, reference, or its own motion, without needing prior notice to the manufacturer/provider. For defective products, the Authority examines whether the manufacturer set standards, whether the product meets any express warranty, and other causes of defect (relying on expert analysis). For defective services, it examines whether statutory/professional standards apply, whether there's an express warranty, equipment quality, and the provider's capacity/qualifications."
    },
    {
        "id": "rules_r7_8",
        "part": "RULES: Evidence Collection",
        "section_no": "Rules 7-8",
        "title": "Proof of manufacture and evidence collection",
        "text": "If a manufacturer disowns a product, the Authority may direct an Inspector to obtain three samples from the market (sealed, witnessed, signed) and send them to a laboratory. The manufacturer/distributor/retailer must provide samples; police may assist if refused. All government authorities must support the Authority's evidence-gathering, including via court-issued search warrants where needed."
    },
    {
        "id": "rules_r9_10",
        "part": "RULES: Orders and Appeals",
        "section_no": "Rules 9-10",
        "title": "Order of the Authority and appeal",
        "text": "The Authority signs and dates its order and may direct free communication to any person. Any person aggrieved by an Authority order under section 23(1) may appeal within 30 days to the Secretary, Agriculture, Supply and Prices Department (or seek review if the Secretary is the Authority)."
    },
    {
        "id": "rules_r11_14",
        "part": "RULES: Court Proceedings",
        "section_no": "Rules 11-14",
        "title": "Claims on behalf of public; place of sitting; form of claim; defence",
        "text": "If the Authority finds a contravention affecting public interest and the manufacturer/provider is unwilling to remedy it, the Authority may file a claim on behalf of the public. Consumer Courts sit at District headquarters. A claim is filed via a signed, verified application with particulars of claimant/defendant, facts, and relief sought, plus documentary evidence including the mandatory pre-filing notice and proof of delivery. Anonymous/pseudonymous claims are not entertained. The Court follows section 31 procedure; if the defendant admits the claim, it is decided on merits; only one adjournment is ordinarily given; claims should be decided within 180 days of notice to the defendant."
    },
    {
        "id": "rules_r15_16",
        "part": "RULES: Product Testing",
        "section_no": "Rules 15-16",
        "title": "Analysis of product; proof of manufacture by the Court",
        "text": "The Court may direct the claimant to provide product samples for laboratory analysis; the laboratory reports findings and methodology to the Court, claimant, and defendant. Objections to lab findings must be raised in writing within 15 days. If the defendant disowns the product, the Court may direct an Inspector to obtain samples (similar process to Authority-level sampling); the claimant bears sampling/lab costs in this scenario."
    },
    {
        "id": "rules_r17_18",
        "part": "RULES: Court Orders and Appeal",
        "section_no": "Rules 17-18",
        "title": "Order of the Court and appeal against Court order",
        "text": "The Presiding Officer signs and dates orders, communicated free of charge. Any person aggrieved by a final Consumer Court order may appeal to the Sindh High Court within 30 days, following Sindh High Court procedural rules."
    },
    {
        "id": "rules_r19_25",
        "part": "RULES: Councils and Public Disclosure",
        "section_no": "Rules 19-25",
        "title": "Provincial and District Councils; laboratory registration; public disclosure",
        "text": "The Provincial Council (chaired by the DG, Bureau of Supply & Prices) and District Councils (chaired by the Deputy Commissioner) include official and non-official members, with functions including reform recommendations, public awareness campaigns, laboratory registration/categorization, and issuing information booklets on product/service standards. After a final Consumer Court order, the Council must ensure easy public access to that order's information."
    },
]

# ---------------------------------------------------------------------------
# AUTHORITY / FORUM ROUTING TABLE (for the Authority Router agent node)
# ---------------------------------------------------------------------------
authority_routing = {
    "pricing_receipt_disclosure": {
        "issue_examples": ["no price displayed", "no receipt given", "missing batch/expiry on receipt", "seller didn't disclose return policy"],
        "relevant_sections": ["act_s18", "act_s19", "act_s20", "act_s11", "act_s16"],
        "forum": "Authority (Secretary/DG, Supply & Prices Department, Sindh)",
        "process": "File complaint directly to the Authority under s.23(1) — no mandatory pre-notice required for this route. Authority can fine violator up to Rs. 50,000.",
        "pre_requisite": "None — direct complaint to Authority."
    },
    "defective_product": {
        "issue_examples": ["broken appliance", "product doesn't match warranty", "unsafe/dangerous product", "product not as described"],
        "relevant_sections": ["act_s4", "act_s5", "act_s6", "act_s7", "act_s8", "act_s9", "act_s10"],
        "forum": "Consumer Court (District level, presided by Judicial Magistrate)",
        "process": "Send written notice to manufacturer/seller (s.29) giving 15 days to respond. If unresolved, file claim before District Consumer Court within 30 days of cause of action.",
        "pre_requisite": "Mandatory written notice under s.29 with proof of delivery."
    },
    "defective_service": {
        "issue_examples": ["poor quality repair service", "unqualified service provider", "service not as promised", "medical/legal/engineering service failure"],
        "relevant_sections": ["act_s13", "act_s14", "act_s15", "act_s16", "act_s17"],
        "forum": "Consumer Court (District level, presided by Judicial Magistrate)",
        "process": "Send written notice to service provider (s.29) giving 15 days to respond. If unresolved, file claim before District Consumer Court within 30 days.",
        "pre_requisite": "Mandatory written notice under s.29 with proof of delivery."
    },
    "unfair_deceptive_practice": {
        "issue_examples": ["false advertising", "bait and switch", "fake discount/sale claims", "misleading endorsement claims", "fake free offers"],
        "relevant_sections": ["act_s21", "act_s22"],
        "forum": "Authority initially (inquiry, s.23(3)); Consumer Court if Authority files claim for Part IV/V contravention",
        "process": "Complaint to Authority, which may inquire and file a claim before the Consumer Court without needing to prove actual damage if damage is 'likely'.",
        "pre_requisite": "None for initiating an Authority inquiry."
    },
}

data = {
    "act_sections": act_sections,
    "rules_sections": rules_sections,
    "authority_routing": authority_routing,
}

with open("/home/claude/haqdar/data/scpa_dataset.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Act sections: {len(act_sections)}")
print(f"Rules sections: {len(rules_sections)}")
print(f"Routing categories: {len(authority_routing)}")
print("Saved to data/scpa_dataset.json")
