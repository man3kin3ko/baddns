import re

from baddns.base import BadDNS_base
from baddns.lib.dnsmanager import DNSManager
from baddns.lib.httpmanager import HttpManager
from baddns.modules.cname import BadDNS_cname
from baddns.lib.findings import Finding

import logging
from urllib.parse import urlparse

log = logging.getLogger(__name__)


class BadDNS_txt(BadDNS_base):
    name = "TXT"
    description = "Check TXT contents for hijackable domains"

    def __init__(self, target, **kwargs):
        super().__init__(target, **kwargs)
        self.target = target
        self.target_dnsmanager = DNSManager(target, dns_client=self.dns_client)
        self.target_httpmanager = HttpManager(
            self.target, http_client_class=self.http_client_class, skip_redirects=True
        )
        self.cname_findings = None
        self.cname_findings_direct = None
        self.reference_data = {}

    def parse_txt_record(self, txt):
        return results

    async def dispatch(self):
        self.cname_findings_direct = []
        self.cname_findings = []

        await self.target_dnsmanager.dispatchDNS(omit_types=["A", "AAAA", "CNAME", "NS", "SOA", "MX"])
        if self.target_dnsmanager.answers["TXT"] == None:
            log.debug("No TXT records found, aborting")
            return False

        for txt_record in self.target_dnsmanager.answers["TXT"]:
            log.debug(f"Got TXT record [{txt_record}]")

            for match in DNSManager.dns_name_regex.finditer(txt_record):
                start, end = match.span()
                host = txt_record[start:end]
                log.info(f"Found host [{host}] in TXT record [{txt_record}] and analyzing with CNAME module")

                cname_instance_direct = BadDNS_cname(
                    host,
                    custom_nameservers=self.custom_nameservers,
                    signatures_dir=self.signatures_dir,
                    direct_mode=True,
                    parent_class="txt",
                    http_client_class=self.http_client_class,
                    dns_client=self.dns_client,
                )
                if await cname_instance_direct.dispatch():
                    self.cname_findings_direct.append(
                        {
                            "finding": cname_instance_direct.analyze(),
                            "description": "Vulnerable Host in TXT Record",
                            "trigger": self.target_dnsmanager.target,
                        }
                    )

                cname_instance = BadDNS_cname(
                    host,
                    custom_nameservers=self.custom_nameservers,
                    signatures_dir=self.signatures_dir,
                    direct_mode=False,
                    parent_class="txt",
                    http_client_class=self.http_client_class,
                    dns_client=self.dns_client,
                )
                if await cname_instance.dispatch():
                    self.cname_findings.append(
                        {
                            "finding": cname_instance.analyze(),
                            "description": "Vulnerable Host in TXT Record",
                            "trigger": self.target_dnsmanager.target,
                        }
                    )

        return True

        # self.cname_findings_direct = []
        # self.cname_findings = []

        # for r in live_results:
        #     parsed_results = self.parse_body(r.text)
        #     if parsed_results:
        #         for pr in parsed_results:
        #             if pr["domain"] == self.target:
        #                 log.debug(f"Found domain matches target ({self.target}), ignoring")
        #                 continue
        #             log.debug(f"Initializing cname instance for target {pr['domain']}")

        #             cname_instance_direct = BadDNS_cname(
        #                 pr["domain"],
        #                 custom_nameservers=self.custom_nameservers,
        #                 signatures_dir=self.signatures_dir,
        #                 direct_mode=True,
        #                 parent_class="references",
        #                 http_client_class=self.http_client_class,
        #                 dns_client=self.dns_client,
        #             )
        #             if await cname_instance_direct.dispatch():
        #                 self.cname_findings_direct.append(
        #                     {
        #                         "finding": cname_instance_direct.analyze(),
        #                         "description": pr["description"],
        #                         "trigger": pr["trigger"],
        #                     }
        #                 )

        #             cname_instance = BadDNS_cname(
        #                 pr["domain"],
        #                 custom_nameservers=self.custom_nameservers,
        #                 signatures_dir=self.signatures_dir,
        #                 direct_mode=False,
        #                 parent_class="references",
        #                 http_client_class=self.http_client_class,
        #                 dns_client=self.dns_client,
        #             )
        #             if await cname_instance.dispatch():
        #                 self.cname_findings.append(
        #                     {
        #                         "finding": cname_instance.analyze(),
        #                         "description": pr["description"],
        #                         "trigger": pr["trigger"],
        #                     }
        #                 )
        # return True

    def _convert_findings(self, finding_sets):
        converted_findings = []
        for finding_set in finding_sets:
            for finding in finding_set["finding"]:
                finding_dict = finding.to_dict()
                log.debug(f"Found finding during cname check for target: {finding_dict['target']}")
                converted_findings.append(
                    Finding(
                        {
                            "target": self.target,
                            "description": f"{finding_set['description']}. Original Event: [{finding_dict['description']}]",
                            "confidence": finding_dict["confidence"],
                            "signature": finding_dict["signature"],
                            "indicator": finding_dict["indicator"],
                            "trigger": finding_set["trigger"],
                            "module": type(self),
                        }
                    )
                )
        return converted_findings

    def analyze(self):
        findings = []
        log.debug("in txt analyze")
        if self.cname_findings_direct:
            findings.extend(self._convert_findings(self.cname_findings_direct))
        if self.cname_findings:
            findings.extend(self._convert_findings(self.cname_findings))
        return findings
