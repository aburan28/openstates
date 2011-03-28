import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import xlrd


class MELegislatorScraper(LegislatorScraper):
    state = 'me'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod(term)

        session = ((int(term[0:4]) - 2009) / 2) + 124

        if chamber == 'upper':
            self.scrape_senators(chamber, session, term)
        elif chamber == 'lower':
            self.scrape_reps(chamber, session, term)

    def scrape_reps(self, chamber, session, term_name):
        url = 'http://www.maine.gov/legis/house/dist_mem.htm'
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            # There are 151 districts
            for district in xrange(1, 152):
                if (district % 10) == 0:
                    path = 'string(/html/body/p[%s]/a[3])' % (district + 4)
                else:
                    path = 'string(/html/body/p[%s]/a[2])' % (district + 4)
                name = page.xpath(path)

                if len(name) > 0:
                    if name.split()[0] != 'District':
                        mark = name.find('(')
                        party = name[mark + 1]
                        district_name = name[mark + 3:-1]
                        name = name[15:mark]

                        firstname = ""
                        lastname = ""
                        middlename = ""

                        if party == "V":
                            # vacant
                            continue

                        leg = Legislator(term_name, chamber, str(district),
                                         name, firstname, lastname,
                                         middlename, party,
                                         district_name=district_name)
                        leg.add_source(url)

                        self.save_legislator(leg)

    def scrape_senators(self, chamber, session, term):
        url = ('http://www.maine.gov/legis/senate/senators/email/'
               '%sSenatorsList.xls' % session)

        DISTRICT = 1
        FIRST_NAME = 3
        MIDDLE_NAME = 4
        LAST_NAME = 6
        PARTY = 7

        mapping = {
            'district': 1,
            'first_name': 3,
            'middle_name': 4,
            'last_name': 5,
            'suffix': 6,
            'party': 7,
            'resident_county': 9,
            'street_addr': 10,
            'city': 11,
            'zip_code': 13,
            'phone': 14,
            'email': 15,
        }

        with self.urlopen(url) as senator_xls:
            with open('me_senate.xls', 'w') as f:
                f.write(senator_xls)

        wb = xlrd.open_workbook('me_senate.xls')
        sh = wb.sheet_by_index(0)

        for rownum in xrange(1, sh.nrows):
            # get fields out of mapping
            d = {}
            for field, col_num in mapping.iteritems():
                d[field] = str(sh.cell(rownum, col_num).value)

            full_name = " ".join((d['first_name'], d['middle_name'],
                                  d['last_name'], d['suffix']))
            full_name = re.sub(r'\s+', ' ', full_name).strip()

            address = "{street_addr}\n{city}, ME {zip_code}".format(**d)

            # For matching up legs with votes
            district_name = d['city']

            phone = d['phone']
            if phone.find("-") == -1:
                phone = phone[0: len(phone) - 2]
            else:
                phone = phone[1:4] + phone[6:9] + phone[10:14]

            leg = Legislator(term, chamber, d['district'], full_name,
                             d['first_name'], d['last_name'], d['middle_name'],
                             d['party'], suffix=d['suffix'],
                             resident_county=d['resident_county'],
                             office_address=address,
                             office_phone=phone,
                             email=d['email'],
                             disctict_name=district_name)
            leg.add_source(url)

            self.save_legislator(leg)
